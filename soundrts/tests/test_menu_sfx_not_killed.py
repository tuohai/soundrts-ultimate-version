"""Menu browse SFX must not be killed by VoiceChannel.stop() on channel 1."""

from pathlib import Path


def test_voicechannel_full_stop_does_not_stop_ops_channel():
    text = Path("soundrts/lib/voicechannel.py").read_text(encoding="utf-8")
    block = text.split("def stop(self", 1)[1].split("\n    def ", 1)[0]
    # Full stop (tts_channel is None) must not stop _ops_channel — that channel
    # lives in the SFX pool and stopping it silenced menu select sounds.
    assert "Do **not** stop ``_ops_channel``" in block or "Do not stop" in block.lower() or "_ops_channel" in block
    # The None branch should not call _ops_channel.stop
    none_branch = block.split("if tts_channel is None:", 1)[1].split("return", 1)[0]
    assert "_ops_channel.stop" not in none_branch


def test_ops_channel_prefers_last_mixer_channel():
    text = Path("soundrts/lib/voicechannel.py").read_text(encoding="utf-8")
    assert "n - 1" in text or "get_num_channels() - 1" in text.replace(" ", "")
