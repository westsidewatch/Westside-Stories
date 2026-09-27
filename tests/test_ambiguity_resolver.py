from dore_subtitle.ambiguity_resolver import build_ambiguity_evidence
from dore_subtitle.dynamic_context import DynamicTerm


def main() -> None:
    context = [
        DynamicTerm("慕道", 0.98, "retriever"),
        DynamicTerm("錫安堂", 0.97, "local-memory"),
        DynamicTerm("恩召", 0.95, "retriever"),
    ]
    evidence = build_ambiguity_evidence(["木道", "西安堂", "恩趙", "今天下雨"], context, minimum_phonetic_similarity=0.65)
    by_observed = {item.observed: item for item in evidence}
    assert by_observed["木道"].candidates[0]["candidate"] == "慕道"
    assert by_observed["西安堂"].candidates[0]["candidate"] == "錫安堂"
    assert by_observed["恩趙"].candidates[0]["candidate"] == "恩召"
    assert "今天下雨" not in by_observed
    print("ambiguity resolver evidence gate: PASS")


if __name__ == "__main__":
    main()
