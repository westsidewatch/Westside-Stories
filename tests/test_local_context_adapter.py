"""Regression gate for on-device scoped subtitle memory."""
from pathlib import Path
from tempfile import TemporaryDirectory

from dore_subtitle.local_context_adapter import build_local_context
from dore_subtitle.local_memory import MemoryScope, confirm, load_memory, save_memory


def confirm_term(path: Path, scope: MemoryScope, *, observed: str, confirmed: str, category: str) -> None:
    terms = load_memory(path)
    terms = confirm(
        terms,
        observed=observed,
        confirmed=confirmed,
        category=category,
        scope=scope,
    )
    save_memory(path, terms)


def main():
    with TemporaryDirectory() as folder:
        path = Path(folder) / "memory.json"
        scope_a = MemoryScope(organisation="church-a", speaker="speaker-a", series="series-a")
        scope_b = MemoryScope(organisation="church-b", speaker="speaker-b", series="series-b")

        confirm_term(path, scope_a, observed="sample-a", confirmed="confirmed-a", category="person")
        confirm_term(path, scope_b, observed="sample-b", confirmed="confirmed-b", category="person")

        context = build_local_context(path, scope_a)
        pairs = {(item["observed"], item["confirmed"]) for item in context["terms"]}
        assert ("sample-a", "confirmed-a") in pairs
        assert ("sample-b", "confirmed-b") not in pairs
        assert context["scope"]["speaker"] == "speaker-a"

        empty = build_local_context(Path(folder) / "missing.json", scope_a)
        assert empty["terms"] == []

    print("local context adapter gate: PASS")


if __name__ == "__main__":
    main()
