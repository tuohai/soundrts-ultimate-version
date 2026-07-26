import threading

from . import auto_update
from . import msgparts as mp
from . import stats
from .clientmedia import voice
from .metaserver import METASERVER_URL
from .paths import STATS_PATH
from .update import update_packages_from_servers


class RevisionChecker(threading.Thread):

    daemon = True
    never_started = True

    def run(self):
        try:
            auto_update.run_background_check()
        except Exception:
            pass
        try:
            stats.Stats(STATS_PATH, METASERVER_URL).send()
        except Exception:
            pass
        try:
            update_packages_from_servers()
        except Exception:
            pass

    def start_if_needed(self):
        if self.never_started:
            self.start()
            self.never_started = False


revision_checker = RevisionChecker()


def offer_update(info) -> None:
    """Prompt and optionally apply a known newer release (main thread)."""
    import sys

    from .clientmenu import confirm_yes_no
    from .lib.msgs import literal_text_msg

    prompt = list(mp.UPDATE_AVAILABLE) + list(mp.UPDATE_PROMPT_DETAIL)
    prompt.append(literal_text_msg(info.version))
    if not confirm_yes_no(prompt):
        return

    if info.body and confirm_yes_no(mp.UPDATE_CHANGELOG_PROMPT):
        voice.item([literal_text_msg(info.body)])
        # Wait until the player acknowledges before downloading.
        confirm_yes_no(mp.UPDATE_CHANGELOG_DONE)

    if not auto_update.is_packaged_install() or sys.platform != "win32":
        voice.alert(mp.UPDATE_OPENING_DOWNLOAD_PAGE)
        auto_update.open_release_page(info)
        return

    # Packaged Windows: leave download/install to a separate update window
    # so the game UI is not frozen / "Not Responding".
    voice.alert(mp.UPDATE_LAUNCHING_EXTERNAL)
    try:
        job = auto_update.write_update_job(info)
        auto_update.launch_external_updater(job)
    except Exception:
        voice.alert(mp.UPDATE_FAILED)
        return

    try:
        from .clientmedia import close_media

        close_media()
    except Exception:
        pass
    raise SystemExit(0)


def offer_pending_update(timeout: float = 8.0) -> None:
    """If a newer release was found at startup, prompt and optionally apply it.

    Call from the main thread after media init (needs pygame + TTS).
    """
    info = auto_update.get_pending(wait_timeout=timeout)
    if info is None:
        return
    offer_update(info)


def check_for_updates_now() -> None:
    """Synchronous update check from the options menu (ignores startup toggle)."""
    voice.alert(mp.CHECKING_FOR_UPDATES)
    try:
        info = auto_update.check_for_update()
    except Exception:
        voice.alert(mp.UPDATE_CHECK_FAILED)
        return
    if info is None:
        voice.alert(mp.UPDATE_UP_TO_DATE)
        return
    offer_update(info)
