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
| `10_Raw/Assets/` | Central bucket for images, attachments, and PDF exports. | **Binary Media Storage** |
| `20_Wiki/Career/` | AI-generated tailored resumes (`CV_[Company]_[Role].md`) and match reports. | **Compiled AI Layer** |
| `20_Wiki/Entities/` | Knowledge pages for companies, tools, and recruiters automatically created by the agent. | **Compiled AI Layer** |
| `20_Wiki/Concepts/` | Evergreen topic pages and domain summaries synthesized across sources. | **Compiled AI Layer** |
| `AGENTS.md` | The brain/schema of the system. Contains operational rules and workflows for Open Code. | **System System Config** |
| `index.md` | Master catalog listing all created wiki notes, auto-updated by the agent. | **Navigation Ledger** |
| `log.md` | Timestamped audit log tracking all actions taken by the agent. | **Audit Ledger** |

---

## ⚡ Available Workflows Reference

Simply prompt Open Code using any of these commands:

* **Workflow 0 (Initial Setup):** *"Run Workflow 0 to initialize my ground-truth files."*
* **Workflow A (General Ingestion):** *"Run Workflow A on `@10_Raw/Sources/article.md`."*
* **Workflow B (Local Tailoring):** *"Run Workflow B on `@10_Raw/Job-Postings/role.md`."*
* **Workflow C (Full Web Ingestion & Application):** *"Run Workflow C on [Job Posting URL]"*