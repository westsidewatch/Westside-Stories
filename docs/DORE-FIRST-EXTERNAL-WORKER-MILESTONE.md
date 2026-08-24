# Doré First External Worker — Westside Stories Subtitle Proofreader

Status: **COMPLETE / PASS**

Westside Stories is now the first product outside the main Westside Watch site to consume a Doré service contract.

## Contract

Doré endpoint: `/api/dore/subtitle-proofread`
Schema: `dore.subtitle-proofread.v1`
Worker: `westside-stories.subtitle-proofreader`

The first production-safe behavior is intentionally conservative: normalize only high-confidence canonical biblical terminology and preserve uncertain subtitle language unchanged. This makes Doré a proofreader rather than a generative subtitle rewriter.

## Westside Stories integration

- `app/dore_proofreader.py` is the reusable product client.
- `scripts/dore_proofread_srt.py` is the first executable worker path.
- SRT sequence numbers and timestamps are never sent for rewriting and are preserved byte-for-structure; only subtitle text lines are candidates.
- Endpoint can be overridden with `DORE_PROOFREADER_URL` or `--endpoint`.
- Failure is explicit; the client does not silently invent corrections if Doré is unavailable.

## Architecture

`Westside Stories SRT -> Doré client -> Doré subtitle-proofread service -> conservative canonical-term corrections -> corrected SRT`

This proves the cross-product service boundary established by the Doré Service Layer. Future expansion can add scripture-context verification, church vocabulary, speaker/name dictionaries, and review suggestions without coupling Westside Stories to Doré's internal indexes.

## Milestone result

**PASS.** Doré has its first external worker contract and Westside Stories has a concrete executable consumer. This closes the final major milestone of the initial infrastructure/service reorganization.
