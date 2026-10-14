---
description: Ingest a new source into the wiki (Concepts + Entities)
agent: build
---

Execute **Workflow A: General Knowledge Ingest** from `AGENTS.md` on the input below.

Input: $ARGUMENTS

Steps:
1. If the input is a URL or pasted text, save the raw clip to `10_Raw/Sources/[PascalCase-Name].md`. If it names an existing file, read it from `10_Raw/Sources/`. Never modify existing raw files.
2. Extract the main concepts and entity mentions.
3. Create or update pages in `20_Wiki/Concepts/` and `20_Wiki/Entities/`, adding `[[Wikilinks]]` between related pages.
4. Run the Standard Maintenance Protocol (update `index.md`, append to `log.md`).

Do not stop to confirm intermediate steps — report the pages created or updated.
