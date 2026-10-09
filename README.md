# LLM Wiki Career Starter Kit

An intelligent, persistent career knowledge base for **Obsidian**, built on the **LLM Wiki pattern**. Drop in a job posting and a local AI agent (e.g. [OpenCode](https://opencode.ai)) ingests it, builds a company page, tailors your résumé, renders a styled PDF, drafts outreach, and tracks the application — while your raw source material stays untouched.

Everything is plain markdown on your own machine. No server, no account, no lock-in.

---

## ✨ What this gives you

- **Automated job ingestion** — paste a URL or a clipped posting; the agent saves it, researches the company, and scores the fit.
- **Tailored, ATS-friendly résumés** — one CV per role, always sourced from a single ground truth so facts never drift.
- **Styled PDF output** — CVs render to PDF matching your existing résumé's fonts, colors, and spacing.
- **Per-company application folders** — CV, cover letter, outreach message, and interview prep for each employer live together.
- **An applications tracker** — one hub table listing every application with match %, status, and links.
- **A living résumé** — feed it feedback and project wins; it distills them into an accomplishment log and refreshes your master résumé automatically.
- **Outreach & interview workflows** — connection notes, prep docs, and post-interview debriefs.

---

## 🧠 How it works (the mental model)

The vault is split into two layers:

- **`10_Raw/` — Immutable (facts).** Your CV, LinkedIn export, raw job postings, clippings, and career inputs. The agent reads these but **never edits** them. They are your ground truth.
- **`20_Wiki/` — Compiled (interpretation).** Company pages, tailored CVs, cover letters, outreach messages, interview prep, the tracker, and the living résumé. The agent creates and maintains everything here.

Because raw facts and derived notes are kept separate, any wiki page can always be re-derived from the originals. On every change the agent also keeps two ledgers current: **`index.md`** (catalog of every page) and **`log.md`** (timestamped audit trail).

**Obsidian** is your display and database: it renders the markdown, graphs the `[[bi-directional links]]`, and gives you a pleasant workspace. **OpenCode** is the execution engine: it reads `AGENTS.md`, then reads/writes the markdown files directly. Instead of re-pasting your résumé into web tools, you keep a local knowledge base that compounds.

---

## 🚀 Quick Start

### 0. Prerequisites

- **[Obsidian](https://obsidian.md/)** (free) — to view and navigate the vault.
- **[OpenCode](https://opencode.ai)** (or any terminal AI agent that reads `AGENTS.md`) — the execution engine.
- **Git** and **Python 3** — Python is only needed for PDF rendering.

### 1. Clone and open

```bash
git clone https://github.com/<your-username>/llm-wiki-career-template.git my-career-wiki
```

Open the folder as an Obsidian vault, and open the same folder in OpenCode (it auto-detects `AGENTS.md`). The Obsidian attachment folder is pre-configured to `10_Raw/Assets`.

### 2. Initialize your ground truth

Export your LinkedIn profile (profile page → **More** → **Save to PDF**) and drop it, plus your current CV (PDF or DOCX), into `10_Raw/Ground-Truth/`. Then prompt the agent:

> "Run Workflow 0 to initialize my ground-truth files from the PDFs in `10_Raw/Ground-Truth/`."

This writes `Master_CV.md` and `LinkedIn_Profile.md`, and renames the career templates so `[[Accomplishment-Log]]`, `[[Living-Resume]]`, and `[[Applications-Tracker]]` resolve.

### 3. Run your first application

Paste any job URL (or a clipped posting file) into chat and prompt:

> "Run Workflow C on <job posting URL>" — or — "Run Workflow C on `@10_Raw/Job-Postings/acme-role.md`"

The agent ingests the posting, creates a company page, generates a match analysis, writes a tailored CV, renders the PDF, and adds a row to the tracker — end to end.

### 4. Generate styled PDF résumés

```bash
scripts/setup.sh   # run once: creates a venv with reportlab + pdfminer.six
```

If you onboarded with a PDF CV (Workflow 0), the styling is auto-detected into `scripts/cv_style.json` from `10_Raw/Assets/source-cv.pdf`. No PDF? Rendering falls back to clean defaults — no action needed. Re-render any CV manually:

```bash
scripts/cv_pdf.py 20_Wiki/Career/Applications/[Company]/CV_[Company]_[Role].md
```

Output lands in `20_Wiki/Assets/` as `Your_Name_CV_[Company]_[Role].pdf`; override the prefix with `--prefix Maria_Lopez`.

---

## 🗂️ How applications are organized

One folder per company, holding everything for that employer together:

```
20_Wiki/Career/Applications/Acme/
├── CV_Acme_Senior-Backend-Engineer.md
├── Cover_Letter_Acme_Senior-Backend-Engineer.md
├── Message_Acme_Senior-Backend-Engineer.md      # outreach / LinkedIn note
└── Interview_Prep_Acme_2026-11-05.md
```

`20_Wiki/Career/Applications-Tracker.md` is the single navigation hub: one row per application with **company · role · match % · status · notes · links to CV / cover letter / PDF**. Multiple roles at the same company share one folder.

---

## 🔄 Available Workflows

Prompt the agent using any of these; the full instructions live in [`AGENTS.md`](AGENTS.md).

| # | Workflow | Example prompt | What it does |
|---|----------|----------------|--------------|
| **0** | Ground-Truth Onboarding | *"Run Workflow 0 to initialize my ground-truth files."* | Import your CV + LinkedIn → `Master_CV.md`, `LinkedIn_Profile.md`, career templates |
| **A** | General Knowledge Ingest | *"Run Workflow A on `@10_Raw/Sources/article.md`."* | Distill sources into company/tool/concept pages |
| **B** | CV Tailoring & Application Synthesis | *"Run Workflow B on `@10_Raw/Job-Postings/role.md`."* | Match analysis → tailored CV → PDF → tracker row |
| **C** | Job Discovery & Web Ingest | *"Run Workflow C on <job URL>."* | Save the posting, then auto-run Workflow B |
| **D** | Career Input Ingest | *"Log this feedback"*, *"Add my latest project."* | STAR entry → accomplishment log → refresh living résumé |
| **E** | Outreach & Networking | *"Draft a connection note for the hiring manager."* | Outreach/LinkedIn message saved in the company folder |
| **F** | Interview Prep & Debrief | *"Prep me for my Acme interview."* | Prep doc; later, debrief → accomplishment log |
| **G** | Vault Maintenance / Lint | *"Lint the vault."* | Reconcile `index.md`, fix broken/orphan links, catch duplicates |

---

## 🌐 Optional: Fast Web Clipping

Instead of copying and pasting job descriptions manually, use the official **[Obsidian Web Clipper](https://obsidian.md/clipper)** extension for Chrome, Firefox, or Safari:

1. Install the extension in your browser.
2. Open any job posting on LinkedIn, Indeed, or Greenhouse.
3. Click the Web Clipper icon.
4. Set the save location folder to `10_Raw/Job-Postings/` and hit **Save**.
5. Tell the agent: *"Run Workflow C on `@10_Raw/Job-Postings/[Clipped_Note_Name].md`."*

---

## 🗓️ Tracking Your Career Over Time

The vault grows with you. Feed it small inputs and it keeps your résumé current automatically:

1. **Log feedback** — after a 1:1, review, or praise from a colleague, drop the note into `10_Raw/Career-Inputs/Feedback/` (or just say *"Log this feedback"*).
2. **Save project notes** — when a project wraps or hits a milestone, drop a short note into `10_Raw/Career-Inputs/Projects/` with what you did and the measured result.
3. **Workflow D does the rest** — it stores the raw input, distills a STAR entry into the [[Accomplishment-Log]], updates company/tool entity pages, and regenerates the [[Living-Resume]] without ever touching your immutable `Master_CV.md`.
4. **Tailored CVs stay fresh** — Workflow B sources from the accomplishment log + living résumé, so every CV you generate already includes your latest work.

Use the templates in `10_Raw/Career-Inputs/` to keep inputs consistent.

---

## 💻 Step-by-Step Tool Setup for Beginners

**Obsidian**
1. Download and install **[Obsidian](https://obsidian.md/)** (free, Windows/macOS/Linux).
2. Launch it and choose **Open folder as vault**.
3. Select this repository folder (or your cloned copy).

**OpenCode**
1. Download and install **[OpenCode](https://opencode.ai)** (or your preferred local terminal AI engine).
2. Open it and choose **Open Project / Workspace**.
3. Point it at the same vault folder.
4. Confirm it detects `AGENTS.md` — that file is the system's brain (rules + workflows).

---

## 📁 Vault Structure Overview

| Directory / File | Description | Layer |
| :--- | :--- | :--- |
| `10_Raw/Ground-Truth/` | Your unalterable source CV and LinkedIn text (`Master_CV.md`, `LinkedIn_Profile.md`). | **Read-only facts** |
| `10_Raw/Job-Postings/` | Raw target job descriptions scraped or clipped from the web. | **Read-only facts** |
| `10_Raw/Sources/` | Web articles, market research, industry notes. | **Read-only facts** |
| `10_Raw/Career-Inputs/` | Raw personal inputs: `Feedback/`, `Projects/`, `Notes/`. | **Read-only facts** |
| `10_Raw/Assets/` | Images, attachments, and the reference CV PDF for styling detection. | **Binary media** |
| `20_Wiki/Career/` | The accomplishment log, the living résumé, the applications tracker, and one folder per company under `Applications/[Company]/`. | **Compiled AI layer** |
| `20_Wiki/Entities/` | Knowledge pages for companies, tools, and people. | **Compiled AI layer** |
| `20_Wiki/Concepts/` | Evergreen topic and domain summaries synthesized across sources. | **Compiled AI layer** |
| `20_Wiki/Assets/` | Generated PDF résumés rendered by `scripts/cv_pdf.py`. | **Generated output** |
| `scripts/` | CV PDF pipeline: `cv_style.py` (detect styling → `cv_style.json`), `cv_pdf.py` (render `CV_*.md` → PDF), bundled fonts, `setup.sh`. | **Local tooling** |
| `AGENTS.md` | The rules and workflows the agent follows. | **System config** |
| `index.md` | Catalog of every wiki note, auto-updated by the agent. | **Navigation ledger** |
| `log.md` | Timestamped audit trail of every agent action. | **Audit ledger** |

---

## 🛠️ Troubleshooting & FAQ

- **A PDF won't render.** Run `scripts/setup.sh` once (it installs `reportlab` + `pdfminer.six` into a venv).
- **The PDF looks unstyled.** `scripts/cv_style.json` is missing — run Workflow 0 with a PDF CV so styling is auto-detected (DOCX/text CVs fall back to clean defaults).
- **The PDFs land in the wrong folder.** Run `scripts/cv_pdf.py` against a file under `20_Wiki/Career/`; the resolver finds `20_Wiki/Assets/` automatically from any subfolder.
- **Links like `[[Accomplishment-Log]]` are red/unresolved.** Run Workflow 0 to rename the `*_TEMPLATE.md` files to their real names.
- **Empty folders are missing after a fresh clone.** Git doesn't track empty directories; the template ships `.gitkeep` markers so the full structure is restored.
- **Can I use a different AI tool?** Yes — any agent that reads `AGENTS.md` works. OpenCode is just the reference engine.

---

## 🔒 Privacy

Everything is local markdown files you own. The vault itself uploads nothing; only the AI tool you run sees the content you show it. Because `10_Raw/` is immutable, your ground truth stays exactly as you saved it.

---

## 🙏 Credits

Built on the **LLM Wiki pattern** — using a plain-markdown vault as shared, transparent memory between you and an AI agent.
