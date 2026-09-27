# ASR Engine v2 — Production Baseline

## Goal
Upgrade Chinese church-sermon transcription as a class of language recognition problems. This is not a word-replacement project.

## Decision
Use mature upstream components. Do not build a custom ASR model or Doré proofreading path.

### Primary production path
1. `fsmn-vad` — speech segmentation
2. `paraformer-zh` / contextual Paraformer — Mandarin ASR with timestamps and native hotword/context bias
3. `ct-punc` — punctuation restoration
4. Existing subtitle segmentation / SRT writer
5. FFmpeg — optional burn-in

### Challenger
`FunAudioLLM/Fun-ASR-Nano-2512` remains an evaluation candidate for general Chinese accuracy, but does not replace the primary path until representative sermon tests show that it preserves the contextual-domain advantage required by this product.

### Removed from the critical recognition path
- Doré proofreading
- fixed 182-term replacement lists
- hard-coded `木道 -> 慕道` style substitutions
- Whisper as the sole Chinese production recognizer

Whisper may remain temporarily as rollback/fallback while ASR v2 is integrated, but it is not the target Chinese engine.

## Context design
Context is retrieval, not replacement.

Sources may grow without requiring an App rebuild:
- Bible names, places, books, phrases
- Christian/theological vocabulary
- church vocabulary and proper nouns
- user/local memory
- current sermon metadata and nearby recognized context

For each speech segment, retrieve a bounded relevant set and pass it to the contextual ASR hotword/context interface. Do not inject the entire corpus into every segment.

## Release gate
No release is called an ASR upgrade merely because modules were added.

Promotion requires representative real-sermon regression evidence across classes including:
- homophones
- Bible people and places
- Bible book names
- theological vocabulary
- church vocabulary
- proper nouns
- Mandarin accents / mixed English where present

`慕道`, `錫安`, and `恩召` are canaries only. They are not the scope of the upgrade.

Track at minimum:
- Chinese CER on referenced samples
- domain-term recall
- false-correction rate
- subtitle timestamp integrity

## Packaging principle
Prefer upstream-supported runtimes and model artifacts. Keep Westside Stories glue thin. Models should not remain resident after a completed job when the runtime allows release.
