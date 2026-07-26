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


def offer_pending_update(timeout: float = 8.0) -> None:
    """If a newer release was found, prompt and optionally apply it.

    Call from the main thread after media init (needs pygame + TTS).
    """
    import sys

    from .clientmenu import confirm_yes_no
    from .lib.msgs import literal_text_msg

    info = auto_update.get_pending(wait_timeout=timeout)
    if info is None:
        return

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

    voice.alert(mp.UPDATE_DOWNLOADING)

    last_spoken = [-1]

    def _progress(pct, _done, _total):
        if pct >= last_spoken[0] + 20 or pct == 100:
            last_spoken[0] = pct
            voice.alert(list(mp.UPDATE_DOWNLOAD_PROGRESS) + [literal_text_msg(f"{pct}%")])

    try:
        script = auto_update.prepare_and_apply(info, progress_callback=_progress)
    except Exception:
        voice.alert(mp.UPDATE_FAILED)
        return

    voice.alert(mp.UPDATE_APPLYING)
    try:
        from .clientmedia import close_media

        close_media()
    except Exception:
        pass
    auto_update.launch_apply_and_exit(script)
    raise SystemExit(0)
