import threading

from . import auto_update
from . import config
from . import msgparts as mp
from . import stats
from .clientmedia import voice
from .metaserver import METASERVER_URL
from .paths import STATS_PATH
from .update import update_packages_from_servers

_update_prompt_done = False


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
    from .lib.pygame_ui import (
        end_narrative,
        ensure_window_for_ui,
        msgparts_to_text,
        show_narrative,
        show_status_banner,
    )

    ensure_window_for_ui()
    prompt = list(mp.UPDATE_AVAILABLE) + list(mp.UPDATE_PROMPT_DETAIL)
    prompt.append(literal_text_msg(info.version))
    if not confirm_yes_no(prompt):
        return

    if info.body and confirm_yes_no(mp.UPDATE_CHANGELOG_PROMPT):
        # literal_text_msg already returns a list; do not wrap it again.
        # Use menu (blocking) so the notes finish (or are skipped) before the
        # "continue updating" prompt — voice.item would be cut off immediately.
        # Show notes on screen for sighted players while TTS speaks.
        try:
            show_narrative(
                msgparts_to_text(literal_text_msg(info.body)),
                hint="Enter / Esc: continue",
            )
        except Exception:
            pass
        voice.menu(literal_text_msg(info.body))
        try:
            end_narrative()
        except Exception:
            pass
        # Wait until the player acknowledges before downloading.
        confirm_yes_no(mp.UPDATE_CHANGELOG_DONE)

    if not auto_update.is_packaged_install() or sys.platform != "win32":
        try:
            show_status_banner(
                msgparts_to_text(mp.UPDATE_OPENING_DOWNLOAD_PAGE),
                hint="",
            )
        except Exception:
            pass
        voice.alert(mp.UPDATE_OPENING_DOWNLOAD_PAGE)
        auto_update.open_release_page(info)
        try:
            end_narrative()
        except Exception:
            pass
        return

    # Packaged Windows: leave download/install to a separate update window
    # so the game UI is not frozen / "Not Responding".
    try:
        show_status_banner(
            msgparts_to_text(mp.UPDATE_LAUNCHING_EXTERNAL),
            hint="",
        )
    except Exception:
        pass
    voice.alert(mp.UPDATE_LAUNCHING_EXTERNAL)
    try:
        job = auto_update.write_update_job(info)
        auto_update.launch_external_updater(job)
    except Exception:
        voice.alert(mp.UPDATE_FAILED)
        try:
            end_narrative()
        except Exception:
            pass
        return

    try:
        from .clientmedia import close_media

        close_media()
    except Exception:
        pass
    raise SystemExit(0)


def offer_pending_update(timeout: float = 30.0) -> None:
    """If a newer release was found at startup, prompt and optionally apply it.

    Call from the main thread after media init (needs pygame + TTS).

    Waits for the background check to finish. If it is still running after
    ``timeout`` (e.g. slow GitHub access), falls back to a synchronous check
    so startup does not silently miss updates the Options menu would find.
    """
    global _update_prompt_done
    if _update_prompt_done:
        return
    if not int(getattr(config, "check_updates_on_start", 1)):
        _update_prompt_done = True
        return

    info = auto_update.get_pending(wait_timeout=timeout)
    if not auto_update.is_check_done():
        # Background thread still in flight (HTTP timeout is 20s; default
        # wait used to be only 8s and silently skipped the result).
        try:
            info = auto_update.check_for_update()
        except Exception:
            return
        auto_update.set_pending(info)

    _update_prompt_done = True
    if info is None:
        return
    offer_update(info)


def check_for_updates_now() -> None:
    """Synchronous update check from the options menu (ignores startup toggle)."""
    from .lib.pygame_ui import (
        end_narrative,
        ensure_window_for_ui,
        msgparts_to_text,
        show_status_banner,
    )

    ensure_window_for_ui()
    try:
        show_status_banner(msgparts_to_text(mp.CHECKING_FOR_UPDATES), hint="")
    except Exception:
        pass
    voice.alert(mp.CHECKING_FOR_UPDATES)
    try:
        info = auto_update.check_for_update()
    except Exception:
        try:
            show_status_banner(msgparts_to_text(mp.UPDATE_CHECK_FAILED), hint="")
        except Exception:
            pass
        voice.alert(mp.UPDATE_CHECK_FAILED)
        try:
            end_narrative()
        except Exception:
            pass
        return
    if info is None:
        try:
            show_status_banner(msgparts_to_text(mp.UPDATE_UP_TO_DATE), hint="")
        except Exception:
            pass
        voice.alert(mp.UPDATE_UP_TO_DATE)
        try:
            end_narrative()
        except Exception:
            pass
        return
    try:
        end_narrative()
    except Exception:
        pass
    offer_update(info)
