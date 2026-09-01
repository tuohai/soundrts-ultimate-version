"""Lobby room list + optional password for join and spectate."""
from __future__ import annotations

from pathlib import Path
from urllib.parse import unquote

from soundrts.room_password import sanitize_room_password
from soundrts.serverclient import ConnectionToClient
from soundrts.serverroom import Game, _Computer


def _source(*path_parts):
    return (
        Path(__file__).resolve().parents[2]
        .joinpath(*path_parts)
        .read_text(encoding="utf-8")
    )


class _FakeMap:
    name = "jl1"
    title = ["jl1"]
    nb_players_min = 1
    nb_players_max = 2


class _FakeAdmin:
    login = "host"
    version = "1.4.9.3"
    alliance = 1
    faction = "random_faction"
    game = None

    def notify(self, *args):
        pass

    def is_compatible(self, other):
        return self.version == getattr(other, "version", None)


class _FakeServer:
    def get_next_id(self, increment=True):
        return 7

    def available_players(self, client=None):
        return []


class _FakeClient:
    def __init__(self, login, version="1.4.9.3"):
        self.login = login
        self.version = version
        self.game = None
        self.alliance = 0
        self.faction = "random_faction"

    def notify(self, *args):
        pass

    def is_compatible(self, other):
        return self.version == getattr(other, "version", None)


def _bare_game(*, password="", started=False, max_players=2):
    admin = _FakeAdmin()
    game = Game.__new__(Game)
    game.id = 7
    game.scenario = _FakeMap()
    game.scenario.nb_players_max = max_players
    game.started = started
    game.password = password
    game.is_public = not bool(password)
    game.server = _FakeServer()
    game.admin = admin
    game.players = [admin]
    game.guests = []
    game.spectators = []
    game.notify = lambda *args: None
    return game


def test_open_room_listed_and_joinable_without_password():
    game = _bare_game()
    guest = _FakeClient("guest")
    assert game.is_listed_room(guest) is True
    assert game.can_join_from_lobby(guest) is True
    packed = game.room_pack()
    raw = unquote(packed)
    parts = raw.split(",")
    assert parts[5] == "0"  # not started
    assert parts[6] == "0"  # unlocked
    assert parts[8] == "1"  # joinable
    assert parts[9] == "1"  # spectatable while waiting


def test_password_blocks_join_and_spectate_until_offered():
    game = _bare_game(password="secret")
    guest = _FakeClient("guest")
    assert game.is_listed_room(guest) is True
    assert game.can_join_from_lobby(guest) is False
    assert game.can_join_from_lobby(guest, "secret") is True
    assert game.can_join_from_lobby(guest, "nope") is False
    started = _bare_game(password="secret", started=True)
    assert started.can_spectate_from_lobby(guest) is False
    assert started.can_spectate_from_lobby(guest, "secret") is True
    assert "secret" not in unquote(game.room_pack())
    assert unquote(game.room_pack()).split(",")[6] == "1"


def test_invited_guest_skips_password_to_join():
    game = _bare_game(password="secret")
    guest = _FakeClient("guest")
    game.guests.append(guest)
    assert game.can_join_from_lobby(guest) is True
    assert game.can_join_from_lobby(guest, "") is True


def test_started_room_is_spectatable_not_joinable():
    game = _bare_game(started=True)
    guest = _FakeClient("guest")
    assert game.is_listed_room(guest) is True
    assert game.can_join_from_lobby(guest) is False
    assert game.can_spectate_from_lobby(guest) is True
    parts = unquote(game.room_pack()).split(",")
    assert parts[8] == "0"
    assert parts[9] == "1"


def test_full_waiting_room_not_joinable():
    game = _bare_game(max_players=1)
    guest = _FakeClient("guest")
    assert game.can_join_from_lobby(guest) is False
    assert unquote(game.room_pack()).split(",")[8] == "0"
    assert unquote(game.room_pack()).split(",")[9] == "1"


def test_waiting_room_is_spectatable():
    game = _bare_game()
    guest = _FakeClient("guest")
    assert game.can_spectate_from_lobby(guest) is True
    assert unquote(game.room_pack()).split(",")[9] == "1"


def test_incompatible_version_hidden():
    game = _bare_game()
    stranger = _FakeClient("guest", version="old")
    assert game.is_listed_room(stranger) is False
    assert game.can_join_from_lobby(stranger) is False


def test_send_rooms_lists_waiting_and_started():
    server = _FakeServer()
    waiting = _bare_game()
    started = _bare_game(started=True)
    started.id = 8
    server.games = [waiting, started]
    guest = ConnectionToClient.__new__(ConnectionToClient)
    guest.login = "guest"
    guest.version = "1.4.9.3"
    guest.server = server
    guest.is_disconnected = False
    notes = []
    guest.notify = lambda *args: notes.append(args)
    guest.send_rooms()
    assert notes[0][0] == "rooms"
    assert waiting.room_pack() in notes[0]
    assert started.room_pack() in notes[0]


def test_send_rooms_empty_sends_no_rooms():
    server = _FakeServer()
    server.games = []
    guest = ConnectionToClient.__new__(ConnectionToClient)
    guest.login = "guest"
    guest.version = "1.4.9.3"
    guest.server = server
    guest.is_disconnected = False
    notes = []
    guest.notify = lambda *args: notes.append(args)
    guest.send_rooms()
    assert notes == [("no_rooms",)]


def test_create_init_does_not_auto_invite():
    guest = _FakeClient("guest")
    server = _FakeServer()
    server.available_players = lambda client=None: [guest]
    admin = _FakeAdmin()
    game = Game(_FakeMap(), 1.0, server, admin, password="abc")
    assert guest not in game.guests
    assert game.password == "abc"
    assert game.is_public is False


def test_sanitize_and_lobby_wiring():
    assert sanitize_room_password("ab-c!1") == "abc1"
    src = _source("soundrts", "clientservermenu.py")
    assert "mp.ROOM_LIST" in src
    assert "class RoomListMenu" in src
    assert "_room_list_menu" in src
    assert "mp.START_A_PUBLIC_GAME_ON" not in src.split("def make_menu")[1].split("def srv_welcome")[0]
    assert "mp.SPECTATE_GAME, self._spectate_games_menu" not in src
    lobby = _source("soundrts", "serverroom.py").split("class InTheLobby")[1].split("class OrganizingAGame")[0]
    assert "list_rooms" in lobby
    reg = _source("soundrts", "serverclient.py").split("def cmd_register(self, args")[1].split("\n    def ")[0]
    assert "wrong_password" in reg
    assert "password_accepted" in reg
    spec = _source("soundrts", "serverclient.py").split("def cmd_spectate(self, args")[1].split("\n    def ")[0]
    assert "wrong_password" in spec
    menu = _source("soundrts", "clientservermenu.py")
    assert "class WaitingToSpectateMenu" in menu
    assert "srv_waiting_to_spectate" in menu
    waiting = menu.split("class WaitingToSpectateMenu")[1].split("class SpectateMenu")[0]
    assert "update_menu(self.make_menu())" in waiting
    assert "quit_spectating" in waiting
    assert "mp.QUIT2" in waiting
    assert "waiting_to_spectate" in _source("soundrts", "serverroom.py")


def test_tts_room_list_ids():
    assert "ROOM_LIST = [5823]" in _source("soundrts", "msgparts.py")
    zh = _source("res", "ui-zh", "tts.txt")
    assert "5823" in zh and "房间列表" in zh
    assert "5827" in zh and "请输入房间密码" in zh


def test_coop_password_join_replaces_ai_partner():
    game = _bare_game(max_players=2)
    game.is_coop_campaign = True
    ai = _Computer("aggressive", coop_partner=True)
    ai.alliance = 2
    game.players.append(ai)
    guest = _FakeClient("guest")
    assert game.can_join_from_lobby(guest) is True
    assert game.register(guest) is True
    assert guest.alliance == 2
