import time

from soundrts.lib.screen import screen_subtitle_set
from soundrts.lib.sound import DEFAULT_VOLUME
from soundrts.lib.sound_cache import sounds


def is_text(o):
    return isinstance(o, str)


_COLLAPSE_CACHE = {}
_COLLAPSE_CACHE_MAX = 512


def clear_collapse_cache():
    """Drop cached translations when resource layers change (campaign/mod/map).

    Colliding numeric IDs (e.g. nathan ``7501.ogg`` vs Raynor ``7501`` TTS)
    must not reuse a previous campaign's collapsed result.
    """
    _COLLAPSE_CACHE.clear()


def _sound_numbers_key(parts):
    key = []
    for p in parts:
        if isinstance(p, list):
            key.append(_sound_numbers_key(p))
        else:
            key.append(p)
    return tuple(key)


class Message:
    def __init__(
        self,
        list_of_sound_numbers,
        lv=DEFAULT_VOLUME,
        rv=DEFAULT_VOLUME,
        said=False,
        expiration_delay=45,
        update_type=None,
        pan_fn=None,
        tts_channel=None,
    ):
        self.list_of_sound_numbers = list_of_sound_numbers
        self.lv = lv
        self.rv = rv
        self.said = said
        self.expiration_time = time.time() + expiration_delay
        self.update_type = update_type
        # Optional callable () -> (lv, rv); refreshed while the line plays so
        # pan follows the player when they change squares mid-utterance.
        self.pan_fn = pan_fn
        # None = use passive_channel() at play time; "primary" / "secondary"
        # forces that library (e.g. production complete → primary).
        self.tts_channel = tts_channel

    def has_expired(self):
        return self.expiration_time < time.time()

    def translate_and_collapse(self, remove_sounds=False):
        cache_key = (_sound_numbers_key(self.list_of_sound_numbers), remove_sounds)
        cached = _COLLAPSE_CACHE.get(cache_key)
        if cached is not None:
            return cached[:]

        q = [sounds.translate_sound_number(sn) for sn in self.list_of_sound_numbers]
        result = []
        
        # 尝试翻译词组 - 优化后的算法，查找最长匹配
        i = 0
        while i < len(q):
            # 如果当前元素是文本，尝试翻译词组
            if is_text(q[i]):
                # 检查是否为强制文本(以"文本: "开头)，如果是就跳过词组翻译
                if isinstance(q[i], str) and q[i].startswith("文本: "):
                    # 移除"文本: "前缀
                    q[i] = q[i][4:]
                    i += 1
                    continue
                
                # 从当前位置尝试查找最长的可翻译词组
                max_length = 0
                best_match = None
                best_end = i
                
                # 尝试从当前位置开始的各种长度的词组
                for j in range(i + 1, len(q) + 1):
                    # 只处理连续的文本元素
                    if j < len(q) and not is_text(q[j]):
                        break
                        
                    # 构建词组并尝试翻译
                    current_words = [q[k] for k in range(i, j) if is_text(q[k])]
                    if not current_words:
                        continue
                        
                    phrase = " ".join(current_words)
                    translated = sounds.translate_phrase(phrase)
                    
                    # 如果找到翻译，并且长度大于之前找到的最长匹配
                    if translated is not None and len(current_words) > max_length:
                        max_length = len(current_words)
                        best_match = translated
                        best_end = j
                
                # 如果找到翻译，替换元素
                if best_match is not None:
                    q[i] = best_match
                    # 将已处理的元素设为None
                    for k in range(i + 1, best_end):
                        q[k] = None
                    i = best_end
                    continue
            i += 1
        
        # 原有的合并逻辑
        i = 0
        while i < len(q):
            if remove_sounds and not is_text(q[i]):
                q[i] = None
                i += 1
                continue
            if is_text(q[i]) and i + 1 < len(q) and is_text(q[i + 1]):
                q[i + 1] = q[i] + " " + q[i + 1]
                q[i] = None
            i += 1
            
        for p in q:
            if p is not None:
                result.append(p)

        if len(_COLLAPSE_CACHE) >= _COLLAPSE_CACHE_MAX:
            _COLLAPSE_CACHE.clear()
        _COLLAPSE_CACHE[cache_key] = result[:]
        return result

    def display(self):
        txt = self.translate_and_collapse(remove_sounds=True)
        if txt:
            txt = txt[0]
        else:
            txt = ""
        screen_subtitle_set(txt)
