---
description: Ingest a job posting and build the tailored application
agent: build
---

Execute **Workflow C: Job Discovery & Web Ingest** (which triggers Workflow B) from `AGENTS.md` on the input below.

Input: $ARGUMENTS

Steps:
1. If the input is a URL, fetch the posting. If it is pasted text, use it as-is. Derive `[Company]` and `[Role]` in PascalCase.
2. Save the raw posting to `10_Raw/Job-Postings/[Company]_[Role].md`. Never modify existing raw files.
3. Immediately run **Workflow B** on the new file: produce the match summary (Match Score %, Key Strengths, Skill Gaps), create/update `20_Wiki/Entities/[Company].md`, write the tailored CV to `20_Wiki/Career/Applications/[Company]/CV_[Company]_[Role].md`, and render the PDF via `scripts/cv_pdf.py`.
4. Add/update the row in `20_Wiki/Career/Applications-Tracker.md`.
5. Run the Standard Maintenance Protocol (update `index.md`, append to `log.md`).

Do not stop to confirm intermediate steps — carry the ingest through to the tracker row and PDF, then report the file paths and Match Score.
