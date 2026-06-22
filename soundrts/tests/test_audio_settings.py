import configparser
import os
import tempfile

from soundrts import config
from soundrts.lib import sound


def test_audio_settings_persist_in_ini():
    with tempfile.TemporaryDirectory() as tmp:
        ini_path = os.path.join(tmp, "SoundRTS.ini")

        config.load(ini_path)
        config.apply_audio_settings()

        sound.main_volume = 0.3
        sound.music_volume = 0.7
        sound.music_enabled = False
        config.save_audio_settings(ini_path)

        config.init()
        config.load(ini_path)
        config.apply_audio_settings()

        assert sound.main_volume == 0.3
        assert sound.music_volume == 0.7
        assert sound.music_enabled is False

        c = configparser.ConfigParser()
        with open(ini_path, encoding="utf-8") as f:
            c.read_file(f)
        assert c.get("audio", "main_volume") == "0.3"
        assert c.get("audio", "music_volume") == "0.7"
        assert c.get("audio", "music_enabled") == "0"


def test_volume_type_clamps_out_of_range_values():
    assert config.volume_type("1.5") == 1.0
    assert config.volume_type("-0.2") == 0.0
