from dore_subtitle.runtime_ab import evaluate_runtime_pair


def main() -> None:
    report = evaluate_runtime_pair(
        whisper_text="我們今天在西安堂聚會木道友也來了",
        challenger_text="我們今天在錫安堂聚會慕道友也來了",
        reference_text="我們今天在錫安堂聚會慕道友也來了",
        domain_terms=("錫安堂", "慕道友"),
    )
    assert report["promoted"], report

    try:
        evaluate_runtime_pair(
            whisper_text="有內容",
            challenger_text="有內容",
            reference_text="",
        )
    except ValueError:
        pass
    else:
        raise AssertionError("promotion must require a human-verified reference")
    print("runtime A/B gate: PASS")


if __name__ == "__main__":
    main()
