from dore_subtitle.asr_benchmark import BenchmarkCase, decide


def main() -> None:
    cases = [
        BenchmarkCase("church", "我們今天在錫安堂聚會", "我們今天在西安堂聚會", "我們今天在錫安堂聚會", ("錫安堂",)),
        BenchmarkCase("calling", "這是神給我們的恩召", "這是神給我們的恩趙", "這是神給我們的恩召", ("恩召",)),
        BenchmarkCase("seeker", "慕道友也可以參加", "木道友也可以參加", "慕道友也可以參加", ("慕道友",)),
        BenchmarkCase("ordinary", "今天下午可能會下雨", "今天下午可能會下雨", "今天下午可能會下雨"),
    ]
    decision = decide(cases)
    assert decision.promoted, decision.reason

    bad = [
        BenchmarkCase("ordinary", "今天下午可能會下雨", "今天下午可能會下雨", "今天下午可能會下雪"),
    ]
    rejected = decide(bad)
    assert not rejected.promoted, rejected.reason
    print("ASR benchmark gate: PASS")
    print(decision.reason)


if __name__ == "__main__":
    main()
