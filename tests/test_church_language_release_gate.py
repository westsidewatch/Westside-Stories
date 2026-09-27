"""Release gate for the local Chinese church-language layer.

This is intentionally broad-domain rather than a one-word correction test. It
protects Scripture books, proper names, theology/church vocabulary, uniqueness,
and the proofreader contract before an app build is allowed.
"""
from church_language_context import BIBLICAL_NAMES, SCRIPTURE_BOOKS, THEOLOGY_AND_CHURCH, context_payload, vocabulary


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    terms = vocabulary()
    payload = context_payload()

    # Coverage gates: catch accidental thinning of an entire domain.
    require(len(SCRIPTURE_BOOKS) >= 60, "Scripture-book coverage regressed")
    require(len(BIBLICAL_NAMES) >= 40, "Biblical proper-name coverage regressed")
    require(len(THEOLOGY_AND_CHURCH) >= 50, "Church/theology coverage regressed")
    require(len(terms) == len(set(terms)), "Church language vocabulary contains duplicates")

    # Representative probes across categories, not typo replacement rules.
    probes = {
        "創世記", "申命記", "以賽亞書", "馬太福音", "使徒行傳", "啟示錄",
        "亞伯拉罕", "摩西", "耶穌", "保羅", "麥基洗德", "尼布甲尼撒", "耶路撒冷",
        "救贖", "稱義", "成聖", "恩召", "挽回祭", "施恩座", "聖靈充滿",
        "主日", "團契", "牧養", "洗禮", "聖餐", "查經", "講道",
    }
    missing = sorted(probes.difference(terms))
    require(not missing, "Representative church-language coverage missing: " + ", ".join(missing))

    require(payload["language"] == "zh-Hant", "Language context must remain Traditional Chinese")
    require(payload["preserve_spoken_wording"] is True, "Spoken-word preservation must remain enabled")
    require(payload["terms"] == terms, "Context payload must carry the complete local vocabulary")

    print(f"church language release gate: PASS ({len(terms)} local domain terms)")


if __name__ == "__main__":
    main()
