"""user/voices/*/voice.ini pack scanning."""

from pathlib import Path

from soundrts.lib import voice_packs


def test_scan_packs_reads_title_and_sapi(tmp_path, monkeypatch):
    root = tmp_path / "voices"
    pack = root / "juli"
    pack.mkdir(parents=True)
    (pack / "voice.ini").write_text(
        "[voice]\ntitle = 朱莉\nsapi = VW Julie\nrate = 0\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(voice_packs, "_voices_root", lambda: str(root))
    packs = voice_packs.scan_packs()
    assert len(packs) == 1
    assert packs[0]["id"] == "pack:juli"
    assert packs[0]["title"] == "朱莉"
    assert packs[0]["sapi"] == "VW Julie"


def test_list_selectable_filters_uninstalled(tmp_path, monkeypatch):
    root = tmp_path / "voices"
    pack = root / "juli"
    pack.mkdir(parents=True)
    (pack / "voice.ini").write_text(
        "[voice]\ntitle = 朱莉\nsapi = VW Julie\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(voice_packs, "_voices_root", lambda: str(root))
    assert voice_packs.list_selectable_ids(installed_sapi=["Microsoft Huihui"]) == []
    assert voice_packs.list_selectable_ids(
        installed_sapi=["VW Julie - English"]
    ) == ["pack:juli"]


def test_display_name_uses_title(tmp_path, monkeypatch):
    root = tmp_path / "voices"
    pack = root / "juli"
    pack.mkdir(parents=True)
    (pack / "voice.ini").write_text(
        "[voice]\ntitle = 朱莉\nsapi = VW Julie\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(voice_packs, "_voices_root", lambda: str(root))
    assert voice_packs.display_name("pack:juli") == "朱莉"
    assert voice_packs.display_name("VW Julie") == "朱莉"
