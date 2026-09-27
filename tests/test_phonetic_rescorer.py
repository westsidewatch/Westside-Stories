from dore_subtitle.dynamic_context import DynamicTerm
from dore_subtitle.phonetic_rescorer import candidates_for_span


def main() -> None:
    context = [
        DynamicTerm("慕道", 0.98, "retriever"),
        DynamicTerm("錫安堂", 0.97, "local-memory"),
        DynamicTerm("恩召", 0.95, "retriever"),
        DynamicTerm("完全無關", 0.99, "retriever"),
    ]

    # These are evidence cases only: no source->target replacement exists in product code.
    cases = [("木道", "慕道"), ("西安堂", "錫安堂"), ("恩趙", "恩召")]
    for observed, expected in cases:
        ranked = candidates_for_span(observed, context, minimum_phonetic_similarity=0.65)
        assert ranked, f"no phonetic candidate for {observed}"
        assert ranked[0].candidate == expected, (observed, ranked)

    unrelated = candidates_for_span("今天下雨", context, minimum_phonetic_similarity=0.72)
    assert not unrelated, unrelated
    print("phonetic rescorer: PASS")


if __name__ == "__main__":
    main()
