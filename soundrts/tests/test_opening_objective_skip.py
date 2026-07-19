"""Opening objective must be skippable before the world thread starts."""

from pathlib import Path


def test_world_loop_starts_after_opening_objective():
    text = Path("soundrts/clientgame/game_interface_base.py").read_text(encoding="utf-8")
    body = text.split("def _run_game_body(self, game, new=True):", 1)[1]
    body = body.split("\n    def ", 1)[0]
    obj_at = body.find("voice.confirmation(mp.OBJECTIVE")
    world_at = body.find("threading.Thread(target=game.world.loop)")
    assert obj_at != -1
    assert world_at != -1
    assert obj_at < world_at


def test_in_match_enabled_when_world_starts():
    text = Path("soundrts/clientgame/game_interface_base.py").read_text(encoding="utf-8")
    body = text.split("def _run_game_body(self, game, new=True):", 1)[1]
    body = body.split("\n    def ", 1)[0]
    assert body.find("set_in_match(True)") > body.find("voice.confirmation(mp.OBJECTIVE")


def test_say_now_stops_on_any_key_out_of_match():
    text = Path("soundrts/lib/voice.py").read_text(encoding="utf-8")
    block = text.split("def _say_now(", 1)[1].split("\n    def ", 1)[0]
    assert "elif self._key_hit(keep_key=keep_key):" in block
    assert "self.channel.stop()" in block
    assert "time.sleep(0.02)" in block


def test_game_tts_primary_stop_clears_busy():
    text = Path("soundrts/lib/game_tts.py").read_text(encoding="utf-8")
    block = text.split("if channel == PRIMARY:", 1)[1].split(
        "# secondary: stop Nuance", 1
    )[0]
    assert "_end_time = None" in block
    assert "nuance_tts.stop()" in block
