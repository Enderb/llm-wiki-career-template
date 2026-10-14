---
description: Ingest a career input (feedback, project, or reflection) into the Accomplishment-Log
agent: build
---

Execute **Workflow D: Career Input Ingest** from `AGENTS.md` on the input below.

Input: $ARGUMENTS

Steps:
1. If the input names an existing file, read it from its subfolder (`Feedback/`, `Projects/`, or `Notes/`); otherwise save the provided text verbatim to `10_Raw/Career-Inputs/[Subfolder]/[PascalCase-Name].md`. Never edit the raw note after ingestion.
2. Distill the note into one or more STAR entries (Situation, Task, Action, Result) with dates and measurable outcomes where possible.
3. Append the entries to `20_Wiki/Career/Accomplishment-Log.md`, newest first, tagged with `[[Entity]]` links.
4. Update or create relevant pages in `20_Wiki/Entities/` and `20_Wiki/Concepts/`.
5. Regenerate `20_Wiki/Career/Living-Resume.md` from the [[Accomplishment-Log]] + `Master_CV.md` (keep `Master_CV.md` immutable).
6. Run the Standard Maintenance Protocol (update `index.md`, append to `log.md`).

Do not stop to confirm intermediate steps — report the entries added and pages updated.
