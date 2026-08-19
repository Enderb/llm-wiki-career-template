# LLM Wiki Career Starter Kit

An intelligent, persistent career knowledge base for Obsidian built on top of the **LLM Wiki pattern**. Features automated job ingestion, market context cross-linking, and resume tailoring workflows powered by AI.

---

## 🚀 Quick Setup Guide

### 1. Initialize Your Ground Truth

**Option A: Automated Onboarding (Recommended)**
1. Export your LinkedIn profile: Go to your LinkedIn profile page -> Click **More** -> Select **Save to PDF**.
2. Drop your LinkedIn PDF and your current CV file (PDF or DOCX) into `/10_Raw/Ground-Truth/`.
3. Open Open Code inside this folder and run:
   > *"Run Workflow 0 to initialize my ground-truth files from the PDFs in `/10_Raw/Ground-Truth/`."*

**Option B: Manual Setup**
1. Navigate to `/10_Raw/Ground-Truth/`.
2. Copy `Master_CV_TEMPLATE.md` to `Master_CV.md` and fill in your experience.
3. Copy `LinkedIn_Profile_TEMPLATE.md` to `LinkedIn_Profile.md` and paste your profile context.

### 2. Run Automated Application Workflows
Paste any target job URL or raw job description into your AI agent chat and execute:
> *"Run Workflow C on [Job Posting URL or File]"*

### 3. Generate Styled PDF Resumes

Workflow B renders every tailored CV to a PDF automatically (matching the styling of the reference CV you onboarded with). To enable it:

1. Run `scripts/setup.sh` once — it creates a Python venv (`~/.opencode-cv/venv`) and installs `reportlab` + `pdfminer.six`.
2. If you onboarded with a PDF CV (Workflow 0), styling is auto-detected into `scripts/cv_style.json` from `10_Raw/Assets/source-cv.pdf`. No PDF? Rendering falls back to clean defaults — no action needed.
3. Manual re-render any time: `scripts/cv_pdf.py 20_Wiki/Career/CV_[Company]_[Role].md`

Output lands in `20_Wiki/Assets/` as `Ender_Barillas_CV_[Company]_[Role].pdf` by default; pass `--prefix YourName_` (e.g. `--prefix Maria_Lopez_`) to change the filename prefix for your own name.

---

## 🌐 Optional: Fast Web Clipping

Instead of copying and pasting job descriptions manually, use the official **[Obsidian Web Clipper](https://obsidian.md/clipper)** extension for Chrome, Firefox, or Safari:

1. Install the extension in your browser.
2. Open any job posting on LinkedIn, Indeed, or Greenhouse.
3. Click the Web Clipper extension icon.
4. Set the save location folder to `10_Raw/Job-Postings/` and hit **Save**.
5. Tell Open Code: *"Run Workflow C on `@10_Raw/Job-Postings/[Clipped_Note_Name].md`"*

---

## 🧠 How Obsidian & Open Code Work Together

This vault uses the **LLM Wiki pattern**: a system where human-readable markdown files serve as a shared, transparent memory between you and an AI assistant.

* **Obsidian is your display & database:** It stores all notes locally on your computer as standard text files (`.md`). It gives you dynamic graphs, bi-directional linking (`[[Note Title]]`), and a visually pleasing workspace.
* **Open Code is your execution engine:** It is an AI developer tool/agent that reads, writes, and reorganizes the markdown files in your vault directly.
* **Together:** Instead of pasting resumes into web AI tools over and over, Open Code reads your ground-truth files locally, writes tailored resumes into `/20_Wiki/Career/`, builds company knowledge pages in `/20_Wiki/Entities/`, and logs every action automatically.

---

## 🗓️ Tracking Your Career Over Time

The vault is designed to grow with you. Feed it small inputs as you go, and it keeps your resume current automatically:

1. **Log feedback** — after a 1:1, a review, or praise from a colleague, drop the note into `10_Raw/Career-Inputs/Feedback/` (or just tell Open Code: *"Log this feedback"*).
2. **Save project notes** — when a project wraps (or hits a milestone), drop a short note into `10_Raw/Career-Inputs/Projects/` with what you did and the measured result.
3. **Open Code (Workflow D) does the rest** — it stores the raw input, distills it into a STAR entry in the [[Accomplishment-Log]], updates company/tool entity pages, and regenerates the [[Living-Resume]] — all without touching your immutable `Master_CV.md`.
4. **Tailored CVs stay fresh** — Workflow B sources from the Accomplishment Log + Living Resume, so every CV you generate already includes your latest work.

Use the templates in `10_Raw/Career-Inputs/` to keep inputs consistent.

---

## 💻 Step-by-Step Tool Setup for Beginners

### 1. Setting Up Obsidian
1. Download and install **[Obsidian](https://obsidian.md/)** (free for Windows, Mac, Linux).
2. Launch Obsidian and select **"Open folder as vault"**.
3. Choose this repository folder (`llm-wiki-career-template` or your cloned copy). The attachment folder is already pre-configured to `10_Raw/Assets` via `.obsidian/app.json`.

### 2. Setting Up Open Code
1. Download and install **[Open Code](https://opencode.ai)** (or your preferred local terminal AI engine/extension).
2. Open Open Code and select **Open Project / Workspace**.
3. Point it to this same Obsidian vault folder.
4. Verify that Open Code detects `AGENTS.md` in the root directory. This file serves as the system instructions for Open Code.

---

## 📁 Vault Structure Overview

| Directory / File | Description | Layer Type |
| :--- | :--- | :--- |
| `10_Raw/Ground-Truth/` | Holds your unalterable source CV and LinkedIn text (`Master_CV.md`, `LinkedIn_Profile.md`). | **Read-Only Context** |
| `10_Raw/Job-Postings/` | Stores raw target job descriptions scraped from URLs or clipped from the web. | **Read-Only Context** |
| `10_Raw/Sources/` | Web articles, market research, or industry notes. | **Read-Only Context** |
| `10_Raw/Career-Inputs/` | Raw personal career inputs: feedback, project notes, and reflections (`Feedback/`, `Projects/`, `Notes/`). | **Read-Only Context** |
| `10_Raw/Assets/` | Central bucket for images, attachments, and PDF exports. | **Binary Media Storage** |
| `20_Wiki/Career/` | AI-generated tailored resumes (`CV_[Company]_[Role].md`), match reports, the running [[Accomplishment-Log]], and the compiled [[Living-Resume]]. | **Compiled AI Layer** |
| `20_Wiki/Entities/` | Knowledge pages for companies, tools, and recruiters automatically created by the agent. | **Compiled AI Layer** |
| `20_Wiki/Concepts/` | Evergreen topic pages and domain summaries synthesized across sources. | **Compiled AI Layer** |
| `20_Wiki/Assets/` | Generated PDF resumes rendered by `scripts/cv_pdf.py` from `CV_*.md`. | **Generated Binary Output** |
| `scripts/` | CV PDF pipeline: `cv_style.py` (detect styling → `cv_style.json`), `cv_pdf.py` (render `CV_*.md` → PDF), bundled fonts, `setup.sh`. | **Local Tooling** |
| `AGENTS.md` | The brain/schema of the system. Contains operational rules and workflows for Open Code. | **System System Config** |
| `index.md` | Master catalog listing all created wiki notes, auto-updated by the agent. | **Navigation Ledger** |
| `log.md` | Timestamped audit log tracking all actions taken by the agent. | **Audit Ledger** |

---

## ⚡ Available Workflows Reference

Simply prompt Open Code using any of these commands:

* **Workflow 0 (Initial Setup):** *"Run Workflow 0 to initialize my ground-truth files."*
* **Workflow A (General Ingestion):** *"Run Workflow A on `@10_Raw/Sources/article.md`."*
* **Workflow B (Local Tailoring):** *"Run Workflow B on `@10_Raw/Job-Postings/role.md`."* — also renders `20_Wiki/Assets/CV_*.pdf`
* **Workflow C (Full Web Ingestion & Application):** *"Run Workflow C on [Job Posting URL]"*
* **Workflow D (Career Input Ingest):** *"Log this feedback"*, *"Add my recent project"*, or *"Update my resume with my latest project"*