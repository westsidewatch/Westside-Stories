from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))

from dore_subtitle.context_candidates import Candidate, ContextTerm, propose
from dore_subtitle.evidence_packet import EvidencePacket
from dore_subtitle.local_memory import LearnedTerm, MemoryScope, applicable_terms
from dore_subtitle.rescore import rescore
from dore_subtitle.suspicion_gate import Suspicion
from subtitle_style import profile_for_video


def test_context_never_proposes_without_suspicion():
    packet = EvidencePacket("1", "麥基洗徳", 0, 1)
    clean = Suspicion("1", ())
    assert propose(packet, clean, [ContextTerm("麥基洗德", "bible")]) == []


def test_rescore_is_review_only_even_when_high():
    candidate = Candidate("1", "麥基洗徳", "麥基洗德", "bible", 1.0, 2.5, "local-confirmed")
    result = rescore(candidate, Suspicion("1", ("low_avg_logprob",)))
    assert result.decision == "review-high"
    assert result.authority == "review-only"
    assert result.mutates_subtitles is False


def test_speaker_memory_does_not_cross_scope():
    learned = LearnedTerm("老高", "高牧師", "person", MemoryScope("church-a", "speaker-a", ""))
    assert applicable_terms([learned], MemoryScope("church-a", "speaker-a", "")) == [learned]
    assert applicable_terms([learned], MemoryScope("church-a", "speaker-b", "")) == []
    assert applicable_terms([learned], MemoryScope("church-b", "speaker-a", "")) == []


def test_portrait_style_is_larger_and_higher_margin():
    landscape = profile_for_video(1920, 1080)
    portrait = profile_for_video(1080, 1920)
    assert portrait.font_size > landscape.font_size
    assert portrait.margin_v > landscape.margin_v
