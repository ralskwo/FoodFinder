import re
from html import unescape

_HANGUL_RE = re.compile(r"[가-힣]")
_ASCII_RE = re.compile(r"[A-Za-z0-9]")
_MOJIBAKE_HINT_RE = re.compile(r"[ÃÂìíîïðñòóôõöùúûüýþÿ�]")


def _score_text(value: str) -> int:
    hangul = len(_HANGUL_RE.findall(value))
    ascii_count = len(_ASCII_RE.findall(value))
    mojibake = len(_MOJIBAKE_HINT_RE.findall(value))
    return (hangul * 4) + ascii_count - (mojibake * 3)


def looks_like_mojibake(value: str) -> bool:
    if not value:
        return False

    if "�" in value:
        return True

    hint_count = len(_MOJIBAKE_HINT_RE.findall(value))
    return hint_count >= 2 and len(_HANGUL_RE.findall(value)) == 0


def repair_mojibake_text(value: str) -> str:
    if value is None:
        return ""

    text = unescape(str(value)).strip()
    if not text:
        return ""

    candidates = [text]

    for src_encoding in ("latin1", "cp1252"):
        try:
            candidates.append(text.encode(src_encoding).decode("utf-8"))
        except Exception:
            pass

    if "\\u" in text:
        try:
            candidates.append(text.encode("utf-8").decode("unicode_escape"))
        except Exception:
            pass

    best = max(candidates, key=_score_text)
    current = text

    best_score = _score_text(best)
    current_score = _score_text(current)

    # Prefer repaired text when score clearly improves or when mojibake patterns disappear.
    if best_score >= current_score + 2 or (
        looks_like_mojibake(current) and not looks_like_mojibake(best)
    ):
        current = best

    current = re.sub(r"\s+", " ", current).strip()
    return current


def normalize_menu_name(value: str, fallback: str = "메뉴명 확인 필요") -> str:
    text = repair_mojibake_text(value)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\s+", " ", text).strip()

    if not text:
        return fallback

    if len(text) < 2:
        return fallback

    if re.fullmatch(r"[\W_]+", text):
        return fallback

    if looks_like_mojibake(text):
        return fallback

    return text[:100]
