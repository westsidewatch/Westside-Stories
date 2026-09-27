from pathlib import Path
from tempfile import TemporaryDirectory

from dore_subtitle.context_retriever import CorpusTerm, retrieve_context
from dore_subtitle.local_memory import LearnedTerm, MemoryScope, save_memory


def main() -> None:
    scope = MemoryScope("Living Water West", "speaker-a", "Matthew")
    other = MemoryScope("Other Church", "speaker-b", "Romans")
    with TemporaryDirectory() as tmp:
        path = Path(tmp) / "memory.json"
        save_memory(path, [
            LearnedTerm("observed-a", "confirmed-a", "local", scope, confirmations=4),
            LearnedTerm("observed-b", "confirmed-b", "local", other, confirmations=20),
        ])
        context = retrieve_context(
            scope=scope,
            memory_path=path,
            query="今天繼續馬太福音的洗禮段落",
            corpus_terms=[
                CorpusTerm("施洗約翰", "馬太福音 洗禮 約旦河", 1.0),
                CorpusTerm(" unrelated-term ", "unrelated evidence", 0.2),
            ],
            limit=64,
        )
        texts = [item.text for item in context]
        assert "confirmed-a" in texts
        assert "confirmed-b" not in texts
        assert "施洗約翰" in texts
        assert len(context) <= 64
    print("context retriever: PASS")


if __name__ == "__main__":
    main()
