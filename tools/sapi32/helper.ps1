# 32-bit SAPI helper for voices registered only under WOW6432Node (e.g. VW Julie).
# Protocol: one JSON object per stdin line; one JSON response per stdout line.
# Started by SoundRTS via SysWOW64\WindowsPowerShell so COM is 32-bit.

$ErrorActionPreference = 'Stop'
[Console]::InputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$sp = $null
try {
    $sp = New-Object -ComObject SAPI.SpVoice
} catch {
    $err = @{ ok = $false; cmd = 'init'; error = $_.Exception.Message } | ConvertTo-Json -Compress
    [Console]::Out.WriteLine($err)
    exit 1
}

function Write-Reply($obj) {
    $json = $obj | ConvertTo-Json -Compress -Depth 6
    [Console]::Out.WriteLine($json)
    [Console]::Out.Flush()
}

function Find-VoiceToken([string]$name) {
    if (-not $name) { return $null }
    $voices = $sp.GetVoices()
    $low = $name.ToLowerInvariant()
    for ($i = 0; $i -lt $voices.Count; $i++) {
        $tok = $voices.Item($i)
        $desc = [string]$tok.GetDescription()
        if ($desc -eq $name -or $desc.ToLowerInvariant() -eq $low -or $desc.ToLowerInvariant().Contains($low) -or $low.Contains($desc.ToLowerInvariant())) {
            return $tok
        }
        try {
            $attr = [string]$tok.GetAttribute('Name')
            if ($attr -and ($attr -eq $name -or $attr.ToLowerInvariant() -eq $low)) {
                return $tok
            }
        } catch {}
    }
    return $null
}

while ($true) {
    $line = [Console]::In.ReadLine()
    if ($null -eq $line) { break }
    $line = $line.Trim()
    if (-not $line) { continue }
    try {
        $msg = $line | ConvertFrom-Json
    } catch {
        Write-Reply @{ ok = $false; error = 'bad json' }
        continue
    }
    $cmd = [string]$msg.cmd
    switch ($cmd) {
        'init' {
            Write-Reply @{ ok = $true; cmd = 'init' }
        }
        'list' {
            $names = @()
            $voices = $sp.GetVoices()
            for ($i = 0; $i -lt $voices.Count; $i++) {
                $names += [string]$voices.Item($i).GetDescription()
            }
            Write-Reply @{ ok = $true; cmd = 'list'; voices = $names }
        }
        'speak' {
            $text = [string]$msg.text
            $voiceName = [string]$msg.voice
            $rate = 0
            $volume = 100
            try { $rate = [int]$msg.rate } catch {}
            try { $volume = [int]$msg.volume } catch {}
            if ($volume -lt 0) { $volume = 0 }
            if ($volume -gt 100) { $volume = 100 }
            if ($rate -lt -10) { $rate = -10 }
            if ($rate -gt 10) { $rate = 10 }
            $interrupt = $true
            try { if ($null -ne $msg.interrupt) { $interrupt = [bool]$msg.interrupt } } catch {}
            if ($voiceName) {
                $tok = Find-VoiceToken $voiceName
                if ($null -eq $tok) {
                    Write-Reply @{ ok = $false; cmd = 'speak'; error = "voice not found: $voiceName" }
                    break
                }
                $sp.Voice = $tok
            }
            $sp.Rate = $rate
            $sp.Volume = $volume
            # SVSFPurgeBeforeSpeak | SVSFlagsAsync
            $flags = 1
            if ($interrupt) { $flags = 1 -bor 2 }
            try {
                $sp.Speak($text, $flags) | Out-Null
                Write-Reply @{ ok = $true; cmd = 'speak' }
            } catch {
                Write-Reply @{ ok = $false; cmd = 'speak'; error = $_.Exception.Message }
            }
        }
        'stop' {
            try {
                $sp.Speak('', 3) | Out-Null  # purge + async empty
            } catch {}
            Write-Reply @{ ok = $true; cmd = 'stop' }
        }
        'busy' {
            $busy = $false
            try {
                # SPRS_IS_SPEAKING = 2
                $busy = ([int]$sp.Status.RunningState -eq 2)
            } catch {}
            Write-Reply @{ ok = $true; cmd = 'busy'; busy = $busy }
        }
        'quit' {
            try { $sp.Speak('', 3) | Out-Null } catch {}
            Write-Reply @{ ok = $true; cmd = 'quit' }
            exit 0
        }
        default {
            Write-Reply @{ ok = $false; error = "unknown cmd: $cmd" }
        }
    }
}
