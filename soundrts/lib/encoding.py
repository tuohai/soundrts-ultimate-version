# similar to http://www.python.org/dev/peps/pep-0263/
import codecs
import locale
import os
import re

from soundrts.lib.log import warning

TTS_FILENAME = "tts.txt"
TTS_REPLACEMENT_CHAR = "\ufffd"


def is_tts_file(filename):
    return os.path.basename(filename) == TTS_FILENAME


def _get_encoding_from_first_or_second_line(text, filename):
    for line in text.split(b"\n")[:2]:
        m = re.search(br"coding[:=]\s*([-\w.]+)", line)
        if m is not None:
            e = m.group(1).decode("ascii")
            try:
                return codecs.lookup(e).name
            except LookupError:
                warning(f"unknown encoding in {filename}: {e}")


def encoding(text, filename="test/tts.txt"):
    if not is_tts_file(filename):
        return "utf-8"
    e = _get_encoding_from_first_or_second_line(text, filename)
    if text.startswith(b"\xef\xbb\xbf"):  # UTF-8 with BOM signature
        if e and e.lower() not in ["utf8", "utf-8", "utf_8"]:
            warning(
                f"{filename} starts with an UTF-8 BOM signature but specifies a {e} encoding! using utf-8-sig"
            )
        return "utf-8-sig"  # the signature will be skipped
    if e is None:
        # 默认 UTF-8；勿用 chardet/系统 locale 猜测（GBK 常被误判）。
        # 非 UTF-8 的遗留文件须在首行声明，例如 ; coding: gbk
        return "utf-8"
    return e


def validate_tts_text(text, filename):
    """检测已被错误编码保存的 tts（常见为 UTF-8 替换字符 U+FFFD）。"""
    if TTS_REPLACEMENT_CHAR not in text:
        return
    count = text.count(TTS_REPLACEMENT_CHAR)
    warning(
        "%s contains %s replacement character(s) (U+FFFD). "
        "The file was likely opened with the wrong encoding and re-saved. "
        "Restore from backup, or save as UTF-8 with '; coding: utf-8' on line 1.",
        filename,
        count,
    )


def decode_tts_bytes(raw, filename):
    """严格解码 tts.txt，避免 errors=replace 静默损坏译文。"""
    enc = encoding(raw, filename)
    try:
        text = raw.decode(enc, errors="strict")
    except UnicodeDecodeError as err:
        warning(
            "failed to decode %s as %s (%s). "
            "The '; coding:' line must match how the file was saved "
            "(recommended: UTF-8 with '; coding: utf-8').",
            filename,
            enc,
            err,
        )
        raise
    validate_tts_text(text, filename)
    return text


if __name__ == "__main__":
    GUESS_OR_DEFAULT = ["ascii", locale.getpreferredencoding()]
    assert encoding(b"; coding: big5\n") == "big5"
    assert encoding(b"; coding: big-5\n") in GUESS_OR_DEFAULT  # unknown encoding
    assert encoding(b"; coding: latin_1\n") == "iso8859-1"
    assert encoding(b"; coding: latin-1\n") == "iso8859-1"
    assert encoding(b"; test\n; coding: big5\n") == "big5"
    assert (
        encoding(b";\n; test\n; coding: big5\n") in GUESS_OR_DEFAULT
    )  # specified on third line
    assert encoding(b"; coding: big5\n") == "big5"
    assert encoding(b"; encoding: big5\n") == "big5"
    assert encoding(b"# -*- coding: big5 -*-") == "big5"
    assert encoding(b"# vim: set fileencoding=big5 :") == "big5"
    assert encoding(b"\xef\xbb\xbf; coding: big5\n") == "utf-8-sig"
    assert b"\xef\xbb\xbf; coding: big5\n".decode("utf-8-sig") == "; coding: big5\n"
