#! .venv\Scripts\python.exe
import os
import shutil
from os.path import join, relpath, splitext

from docutils import core
from docutils.utils import SystemMessage

import rules2doc

SRC = "doc_src/src"

_SETTINGS = {
    "halt_level": 5,
    "exit_status_level": 5,
    "report_level": 4,
    "input_encoding": "utf-8",
    "output_encoding": "utf-8",
}


def _publish_one(src_path, dest_path):
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
    core.publish_file(
        source_path=src_path,
        writer_name="html",
        destination_path=dest_path,
        settings_overrides=_SETTINGS,
    )


def _publish_rst(lang, dest_pkg):
    """Build RST under doc_src into HTML under doc/{lang}/ only."""
    p = join(SRC, lang)
    dp = join(dest_pkg, lang)
    os.makedirs(dp, exist_ok=True)
    for root, _dirs, files in os.walk(p):
        for n in files:
            if not n.endswith(".rst"):
                continue
            src_path = join(root, n)
            rel = relpath(src_path, p)
            htm_rel = splitext(rel)[0] + ".htm"
            _publish_one(src_path, join(dp, htm_rel))
    if lang in ("en", "pt-BR"):
        with open(join(p, "stats.inc"), "w", encoding="utf-8") as f:
            f.write(rules2doc.stats)


def build(dest="."):
    DEST = join(dest, "doc")
    os.makedirs(DEST, exist_ok=True)

    for lang in ("es", "it"):
        p = join(SRC, lang, "htm")
        dp = join(DEST, lang)
        os.makedirs(dp, exist_ok=True)
        if os.path.isdir(p):
            for n in os.listdir(p):
                shutil.copyfile(join(p, n), join(dp, n))

    for lang in ("en", "zh"):
        _publish_rst(lang, DEST)

    pt_br = join(DEST, "pt-BR")
    os.makedirs(pt_br, exist_ok=True)
    shutil.copyfile(join(SRC, "en/stats.inc"), join(SRC, "pt-BR/stats.inc"))
    try:
        _publish_rst("pt-BR", DEST)
    except (UnicodeError, SystemMessage):
        shutil.copyfile(join(DEST, "en/units.htm"), join(pt_br, "units.htm"))

    shutil.copyfile(join(DEST, "en/units.htm"), join(DEST, "it/units.htm"))
    pt_mod = join(pt_br, "mod")
    os.makedirs(pt_mod, exist_ok=True)
    for n in ("mapmaking", "modding", "aimaking"):
        shutil.copyfile(join(DEST, "en/mod/%s.htm" % n), join(pt_mod, "%s.htm" % n))


if __name__ == "__main__":
    build()
