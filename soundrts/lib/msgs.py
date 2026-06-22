NB_ENCODE_SHIFT = 1000000

LITERAL_TEXT_PREFIX = "文本: "


def literal_text_msg(text):
    """用户键入/取名/聊天内容：强制按字面文本朗读，不按 tts ID 解析。"""
    if not text:
        return []
    return [LITERAL_TEXT_PREFIX + str(text)]


def encode_msg(msg):
    return "***".join(map(str, msg))


def eval_msg_and_volume(s):
    return [s.split("***")]


def format_signed_number(n, *, as_float=False):
    """整数/浮点均支持负值 TTS。"""
    if as_float:
        return nb2msg_float(n)
    n = int(n)
    if n < 0:
        return literal_text_msg(str(n))
    return [NB_ENCODE_SHIFT + n]


def nb2msg(n):
    return format_signed_number(int(n))


def coerce_voice_msg_parts(parts):
    result = []
    for part in parts:
        if isinstance(part, str) and part.isdigit():
            result.append(int(part))
        else:
            result.append(part)
    return result


_coerce_voice_msg_parts = coerce_voice_msg_parts


def _is_nb_encoded_number(part):
    if isinstance(part, int):
        return part >= NB_ENCODE_SHIFT
    if isinstance(part, str) and part.isdigit():
        return int(part) >= NB_ENCODE_SHIFT
    return False


def _chapter_number_from_map_name(map_name):
    if isinstance(map_name, str) and "/" in map_name:
        last = map_name.rsplit("/", 1)[-1]
        if last.isdigit():
            return int(last)
    return None


def _small_chapter_number(part):
    if isinstance(part, int):
        n = part
    elif isinstance(part, str) and part.isdigit():
        n = int(part)
    else:
        return None
    # Campaign chapter indices are small; TTS message IDs (e.g. 5033) must not match.
    if 0 <= n <= 999:
        return n
    return None


def normalize_map_title_for_voice(title, map_name=""):
    """Normalize campaign chapter map titles for TTS.

    Mission maps loaded from ``N.txt`` keep the chapter number as the first title
    token (e.g. ``1``). Without conversion that digit is resolved through
    ``tts.txt`` (Chinese ``1`` -> "你在") instead of being spoken as a number.
    """
    title = coerce_voice_msg_parts(list(title))
    if not title:
        return title
    if _is_nb_encoded_number(title[0]):
        return title

    if isinstance(map_name, str) and map_name.startswith("random_"):
        try:
            from ..randommap import map_voice_title_from_parts

            converted = map_voice_title_from_parts(title, map_name)
            if converted:
                return converted
        except ImportError:
            pass

    chap = _chapter_number_from_map_name(map_name)
    if chap is None:
        chap = _small_chapter_number(title[0])
        if chap is None:
            return title

    rest = title[1:]
    if rest:
        head = rest[0]
        if head in (60,) or (
            isinstance(head, str) and head.isdigit() and int(head) == 60
        ):
            rest = rest[1:]

    return nb2msg(chap) + rest


def _voice_text_for_key(sounds, key):
    """仅解析为可读文本，不加载 .ogg（留给 Message 统一处理音效 ID）。"""
    t = sounds.text(key)
    if t is not None:
        return t
    try:
        fb = sounds._global_lookup_text(key)
        if fb is not None:
            return fb
    except Exception:
        pass
    return key


def localize_voice_msg(parts):
    """将语音列表中的 tts 文本键解析为当前语言译文（如 loc_ch02_outpost）。"""
    try:
        from .sound_cache import Sound, sounds
    except ModuleNotFoundError:
        return list(parts)
    result = []
    for p in parts:
        if isinstance(p, Sound):
            result.append(p)
        elif isinstance(p, str) and not p.startswith(LITERAL_TEXT_PREFIX):
            result.append(_voice_text_for_key(sounds, p))
        else:
            result.append(p)
    return result


def nb2msg_float(n):
    """处理浮点数的版本，将浮点数转为字符串"""
    if n < 0:
        # 负值用于 *_vs 惩罚等；编码数字只支持非负，负值用字面文本朗读
        if n == int(n):
            return literal_text_msg(str(int(n)))
        return literal_text_msg(str(n))
    # 将浮点数转为字符串，如果是整数则不显示小数部分
    if n == int(n):
        return nb2msg(int(n))
    else:
        # 字符串形式的数字，例如"2.5"
        return [str(n)]
