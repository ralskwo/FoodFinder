from utils.text_normalizer import normalize_menu_name, repair_mojibake_text


def test_repair_mojibake_text_from_latin1_utf8_mix():
    original = "생삼겹살(180g)"
    broken = original.encode("utf-8").decode("latin1")

    repaired = repair_mojibake_text(broken)
    assert repaired == original


def test_normalize_menu_name_keeps_valid_text():
    assert normalize_menu_name("김치찌개") == "김치찌개"


def test_normalize_menu_name_returns_fallback_for_unreadable_text():
    unreadable = "Ã¥Ã¼Ã©ÃµÃ¼"
    assert normalize_menu_name(unreadable) == "메뉴명 확인 필요"
