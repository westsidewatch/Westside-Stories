from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))

from church_corrector import apply_to_srt_text, correct_text, load_terms


def test_first_use_known_sermon_errors_are_corrected():
    source = "今天我們談木道，也談神恩昭的指望，最後回到西安。"
    corrected, changes = correct_text(source)
    assert "木道" not in corrected
    assert "恩昭" not in corrected
    assert "慕道" in corrected
    assert "恩召" in corrected
    # 錫安/西安 is context-sensitive in general Chinese. It must be resolved by
    # church vocabulary evidence, not a global blind replacement.
    terms = load_terms()
    corrected2, _ = correct_text("我們仰望西安", terms=terms, explicit={"西安": "錫安"})
    assert corrected2 == "我們仰望錫安"


def test_srt_timestamps_are_byte_for_byte_preserved():
    source = "1\n00:00:01,000 --> 00:00:04,000\n木道與恩昭\n\n2\n00:00:05,000 --> 00:00:08,000\n耶穌基督\n"
    corrected, summary = apply_to_srt_text(source)
    assert "00:00:01,000 --> 00:00:04,000" in corrected
    assert "00:00:05,000 --> 00:00:08,000" in corrected
    assert "慕道與恩召" in corrected
    assert summary["corrections"] >= 2


def test_no_training_history_required():
    # The shipped corpus is the first-use authority. No user memory/history is
    # required for the corrector to be active.
    terms = load_terms()
    assert "慕道" in terms
    assert "恩召" in terms
    assert "錫安" in terms
    assert len(terms) >= 100
