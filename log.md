# Vault Activity Log

## [2026-08-05] init | Template repository initialized
## [2026-08-07] schema | Added Career-Inputs structure, Accomplishment-Log + Living-Resume placeholders, and Workflow D (Career Input Ingest)
## [2026-08-13] pipeline | Bundled CV PDF pipeline (`scripts/`): cv_style.py detects reference CV styling → cv_style.json; cv_pdf.py renders CV_*.md → 20_Wiki/Assets/CV_*.pdf. Added to Workflow 0 (style detection from onboarding PDF) and Workflow B (automatic PDF render). README updated with setup + usage.
## [2026-10-09] schema | Per-company Applications layout: added `20_Wiki/Career/Applications/[Company]/` (one folder per company holding CV + cover letter + outreach Message + interview prep) and an `Applications-Tracker_TEMPLATE.md` hub. Updated AGENTS.md (Directory Map, Career Workspace Layout, Workflow B paths + outreach step) and README; synced `scripts/cv_pdf.py` output resolver so PDFs land in `20_Wiki/Assets/` from any subfolder; added `.gitkeep` markers (incl. `20_Wiki/Assets/`, `Applications/`) so the full empty structure is tracked; neutralized the default PDF filename prefix to `Your_Name` (template no longer ships an owner's name).
