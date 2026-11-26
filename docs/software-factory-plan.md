# Software Factory Plan: building v2 of llm-wiki-career-template with AI agents

Status: **design, not built yet**. Written 2026-11-26.

## 1. Why this exists

This template was built in an AI-assisted way, one prompt at a time, with a human steering every step. The next step is a **software factory**: a repeatable pipeline where specs go in, coding agents implement them in parallel, automated gates decide what is good enough, and a human reviews only what needs judgement. Every step is measured.

Goals, in order:

1. **Ship v2 of the template** with less human time per change than v1 took.
2. **Make quality measurable**: every merge passes gates the agent cannot skip, and the numbers (pass rate, rework, wait time, lead time) are recorded for every issue.
3. **Learn the flows at zero spend**: subscription models plus free and local models only. Every place that would normally need paid API calls is marked, along with the free or local option used instead.

Non-goals: building a general agent platform, running agents in the cloud, or hosting anything.

## 2. Decisions taken (interview, 2026-11-26)

| Question | Decision |
|---|---|
| What v2 is | **The factory decides.** Its first job is to write a v2 spec, which the human approves. |
| Autonomy | **Auto-merge low-risk.** Agents open PRs. PRs that only touch docs or tests merge on green. Everything else gets a human review. |
| Budget | **No spend.** Claude Code (Opus, subscription), opencode free models, and local models through Ollama. The Google API key is only used if it stays on the free tier. |
| Runtime | **Local first, CI for the gates.** Agents run on the Mac in git worktrees. GitHub Actions runs the deterministic gates. The LLM gates run locally and report back to the PR as commit statuses. |

Machine: Apple M1 Max, 32 GB RAM. Ollama is installed and has `gemma4:12b-it-qat` (7.2 GB). The disk is **97% full (15 GB free)**, which limits local models to about 12–14B unless space is freed.

## 3. What the current repo gives us, and what is missing

**Reusable:**
- `tests/` already has the right pattern for *CV* quality: deterministic pytest checks (companies, titles, dates, numbers, word and page limits) plus an LLM judge. The judge returns schema-validated JSON, falls back across backends automatically (anthropic → claude → opencode), and caches verdicts.
- `scripts/check_cv.sh` gives one exit code as the definition of done. AGENTS.md Core Rule 8 already says "a SKIP is not done" and "never loosen `cv_checks.toml` without the user's say-so". These rules carry straight over to factory gates.

**Missing before agents can be trusted with the code:**
- **No tests of the template's own code.** The checks test CVs. Nothing tests `cvcheck.py`'s metric parsing, `cv_pdf.py`'s rendering, or the judge's answer parsing.
- **No fixture data.** The repo ships only `*_TEMPLATE.md` placeholders, so the CV checks have nothing to run on in CI. We need a fictional persona vault.
- **No CI** (no `.github/workflows/`).
- **No instructions written for developers.** `AGENTS.md` tells an agent how to *use* the vault, and it ships to end users. Factory agents need separate instructions for *developing* the template, kept in `.factory/` and passed explicitly, so they never ship as user instructions. A `CLAUDE.md` at the root would be picked up by users' agents.
- **No gate on the gates.** Nothing proves that the checks catch what they claim to catch.

## 4. The factory at a glance

```
 ┌─────────┐   ┌──────────┐   ┌───────────┐   ┌────────────┐   ┌──────────┐   ┌────────┐
 │ 1 Intake │──▶│ 2 Plan   │──▶│ 3 Build   │──▶│ 4 Gates    │──▶│ 5 Review │──▶│ 6 Merge│
 │ issue +  │   │ agent    │   │ agent in  │   │ CI (det.)  │   │ auto if  │   │ squash │
 │ criteria │   │ refines, │   │ worktree, │   │ + local    │   │ low-risk,│   │ + log  │
 │          │   │ human OK │   │ own branch│   │ LLM judge  │   │ else human│  │        │
 └─────────┘   └──────────┘   └─────▲─────┘   └─────┬──────┘   └────┬─────┘   └────────┘
                                    │  fail report   │               │ changes requested
                                    └────────────────┘◀──────────────┘
                     every step appends an event to factory/metrics.jsonl  ──▶ 7 Measure
```

Everything is plain scripts in `factory/` (bash + Python) driving `gh`, `git worktree`, `claude -p` and `opencode run`. There is no orchestration framework, so each step stays inspectable.

## 5. Stations

### 5.1 Intake: how work comes in

- **GitHub Issues are the queue.** One issue template (`.github/ISSUE_TEMPLATE/factory-task.yml`) with these fields:
  - **Goal**: one paragraph.
  - **Acceptance criteria**: written as *runnable checks* wherever possible, e.g. "`pytest tests/unit -k metrics` passes", "`scripts/check_cv.sh fixtures/persona/bad/inflated_number.md` exits 1 and names `500K`".
  - **Touches**: the expected paths, used to keep parallel agents from colliding.
  - **Risk**: `low` | `normal` | `high`. This is a hint only; the actual merge policy is computed from the diff (§5.5).
  - **Size**: `S` (< 1 h agent time) or `M`. Anything bigger is split before it is ready.
- **Labels drive state:** `factory:draft` → `factory:ready` → `factory:in-progress` → `factory:in-review` → closed, with `factory:stuck` as the escape hatch.
- **Bootstrapping v2:** the first issue is *"Write the v2 spec"*. A planning agent (Opus) reads the repo, README, AGENTS.md, the open issues and this plan, then writes `docs/specs/v2.md`: problems, proposed scope, out of scope, and risks. The human edits and approves it by merging. A second run splits the spec into `factory:draft` issues. **The human moves issues to `factory:ready`**: this is the main point of human control over *what* gets built.

### 5.2 Plan: per issue (cheap, optional for S)

Before writing code on an `M` issue, the agent posts a short plan as an issue comment: approach, files, how each acceptance criterion will be shown. This catches a wrong approach before it costs a build loop. The human can reply or skip it. After a time limit (say 2 h) the agent proceeds with the plan as written.

### 5.3 Build: agents in parallel worktrees

`factory/run.sh <issue>`:

1. Creates a worktree `../llm-wiki-factory/<issue>-<slug>` on branch `factory/<issue>-<slug>` from `origin/main`.
2. Runs Claude Code headless in that worktree:
   `claude -p "<issue body + acceptance criteria>" --append-system-prompt "$(cat .factory/developer-brief.md)" --permission-mode acceptEdits --allowedTools "Read,Edit,Write,Bash(pytest:*),Bash(scripts/*:*),Bash(git diff:*),Bash(git status:*)" --output-format json --max-turns 60`
   - The agent may edit, run tests and commit locally. It **cannot push or call `gh`**: the runner script does that, so an agent can never merge its own work.
   - The JSON output gives the session id (for `--resume` on rework) and turn/usage numbers for the metrics.
3. Runs the local gates (§5.4). If they fail, it runs the rework loop (§5.6). If they pass, it pushes and opens a PR whose body is generated from a template: what changed, evidence per acceptance criterion, gate report, known risks.

**Parallelism:** a small scheduler (`factory/dispatch.py`) picks `factory:ready` issues whose `Touches` paths don't overlap any in-progress issue. Start with **2 concurrent workers**. The Claude subscription's rate limits, not the CPU, are the bottleneck. Raise it only once metrics show the limits aren't being hit. Worktrees are small, so the 15 GB of free disk is not a constraint here.

**`.factory/developer-brief.md`** (the developer instructions): repo map; "never edit `10_Raw/**`, `tests/fixtures/**/expected*`, or loosen `tests/cv_checks.toml` unless the issue says so"; "write the test first, and make every acceptance criterion a command you ran"; commit message format; "stop and write `BLOCKED: <question>` instead of guessing".

### 5.4 Gates: what decides a merge

The gates run in tiers, cheapest first, and stop at the first failure. Deterministic gates are **blocking**. LLM gates are blocking only in the ways §5.4.2 makes safe, because a judge's verdict varies from run to run.

#### 5.4.1 Deterministic gates (GitHub Actions on every PR, and locally before push)

| Gate | What it checks | Blocks? |
|---|---|---|
| **G0 Hygiene** | `ruff` lint/format; no secrets (`gitleaks`); no file > 1 MB; no change to `10_Raw/**` unless labelled `raw-ok`; no personal data (a check that the fixture persona's names are the only names present) | yes |
| **G1 Unit** | `pytest tests/unit`: new tests for `cvcheck` (metrics, `month_years`, `appears_in`, normalization), `llm_judge.parse_answer`, `cv_style` defaults | yes |
| **G2 Gate-the-gates** | `fixtures/persona/` is a fictional ground truth plus `good/` CVs that must PASS all deterministic checks and `bad/` CVs that each contain **one planted defect** (made-up company, wrong date, inflated number, over 900 words, 3 pages) and must FAIL **exactly** the matching check. `fixtures/persona/expected.toml` maps each bad CV to the test id that must fail. This is mutation testing for the checker: if an agent weakens a check, a planted defect slips through and G2 goes red. | yes |
| **G3 Render** | `cv_pdf.py` renders every fixture CV. Checks the page count, that the PDF text contains the persona's name and section headings, and that rendering is deterministic (the same input gives the same text layer). | yes |
| **G4 Acceptance** | Runs the issue's acceptance-criteria commands, which the runner extracts into `.factory/acceptance.sh` on the branch | yes |

CI needs no model credentials, so it costs nothing and is reproducible.

#### 5.4.2 LLM gates (local only, reported to the PR as commit statuses via `gh api`)

| Gate | Model (no spend) | How variation is handled | Blocks? |
|---|---|---|---|
| **J1 CV judge on fixtures**: the existing `llm_judge.py`, run on `fixtures/persona/good` and on `semantic-bad/` CVs whose defects only a reader catches ("led the team" when the source says "member of the team"; an untraceable tool) | local `gemma4:12b` via Ollama at temperature 0, **3 runs with majority vote**; opencode `big-pickle` as tie-breaker | A planted semantic defect must be flagged in ≥ 2 of 3 runs. A good CV may get at most 0 flags by majority. | yes, by majority vote. Any split between runs is logged as judge disagreement. |
| **J2 Diff reviewer**: a second model reviews the PR diff against the issue's acceptance criteria and the developer brief, and returns JSON `{criterion, met, evidence}` + `{concern, file, line, severity}` | opencode `big-pickle` (a different model family from the implementer, so its blind spots are less likely to be the same) | Run twice. Only a finding that appears in both runs is shown as a concern. | **Advisory**, except "acceptance criterion not met" with evidence, confirmed by G4 failing → blocking |

Only J1 and J2 would normally need paid API calls in CI. We avoid that cost by running them on the Mac and posting `factory/judge` and `factory/review` statuses. **Branch protection requires** the CI checks plus `factory/judge`.

**Why deterministic checks sit next to the judge:** the judge catches meaning ("upgraded a responsibility"), and the deterministic checks catch facts (a number, a date). The judge's recall is then measured *against planted defects*, rather than assumed. The judge's agreement rate (§7) tells us when a model swap or prompt change has made it less reliable.

### 5.5 Human review: what the human sees, and when

The merge policy is computed **from the diff, not from the agent's label** (`factory/policy.py`):

| Class | Rule | Path |
|---|---|---|
| **low** | Only `docs/**`, `*.md` outside `AGENTS.md`, or `tests/unit/**` *additions* | auto-merge (`gh pr merge --squash --auto`) once all required gates are green |
| **normal** | Code in `scripts/`, `tests/*.py`, new features | human review |
| **high** | `AGENTS.md`, `.opencode/command/**`, `tests/cv_checks.toml`, `fixtures/**/expected*`, `10_Raw/**`, `.factory/**`, `.github/**`, or any change that both edits a check *and* the fixtures it is tested by | human review **and** a mandatory diff read of the gate changes |

The PR body puts what the human needs first: a one-line summary, evidence for each acceptance criterion, the gate table, J2 concerns, and "what I was unsure about". The human reviews **behaviour and intent**. The gates already covered style, tests and facts.

**Spot-check auto-merges:** each week, read 1 in 5 auto-merged PRs. An auto-merged PR that needed a fix counts as an *escape* (§7). If more than one escape happens in a month, the low-risk path list shrinks.

### 5.6 Failure loop: rework

```
gates fail ─▶ factory/gate.py writes gate-report.json (failing gate, test id, message, hint)
          ─▶ claude -p --resume <session> "Gates failed: <report>. Fix the cause, not the check."
          ─▶ re-run gates   (max 3 attempts)
          ─▶ still failing ─▶ label factory:stuck, comment with all reports, worktree kept
```

- **Judge flakiness is not rework.** If only J1 fails and every deterministic gate passes, J1 re-runs once (cache bypassed) before the failure is sent back to the agent. The re-run is logged as `judge_retry`.
- **Review feedback is rework too.** A human "request changes" comment is sent to the same session (`factory/run.sh <issue> --address-review`) and counted separately from gate rework.
- **Guard against gaming:** if a rework attempt touches a high-class path (checks, fixtures, config) that the issue didn't list in `Touches`, the run stops and is labelled `factory:stuck`. It is not retried.

### 5.7 Measure: metrics

Each station appends one JSON line to `factory/metrics.jsonl` (committed by the runner on a `factory-metrics` branch, so `main` stays clean): `{ts, issue, pr, event, attempt, gate, result, model, turns, duration_s}`. Review timestamps come from the GitHub API. `factory/report.py` writes a weekly `docs/factory-report-YYYY-WW.md`.

| Metric | Definition | Why it matters |
|---|---|---|
| **First-pass gate rate** | share of PRs whose first gate run is all green | quality of specs + developer brief |
| **Gate pass rate, per gate** | pass / runs, per G0–G4, J1, J2 | shows which gate catches what; a gate that never fails may be useless |
| **Rework** | gate attempts per issue; human change-requests per PR | cost of poor specs or a weak implementer |
| **Stuck rate** | issues ending `factory:stuck` / issues started | where the factory gives up |
| **Review wait time** | PR ready → first human review (median, p90) | the human is often the bottleneck; this shows it |
| **Lead time** | issue `factory:ready` → merged (median, p90) | overall throughput |
| **Escape rate** | merged factory PRs later reverted or blamed by a bug issue within 14 days | quality that the gates missed |
| **Judge agreement** | share of J1/J2 verdicts that are the same across the repeated runs; recall on planted defects | how much to trust the LLM gates |
| **Human minutes per merged PR** | self-logged during review (one number per review) | the number that says whether the factory pays off |
| **Model usage** | turns and tokens per issue from `claude -p` / opencode JSON output | shows where spend *would* go once paid models are used |

## 6. Model routing at zero spend

| Role | Default | Local / free fallback | Notes |
|---|---|---|---|
| Spec writer, planner | Claude Code Opus (subscription) | — | Few calls, highest leverage |
| Implementer | Claude Code Opus (subscription) | opencode `big-pickle` for `S` docs/tests issues | 2 concurrent workers to stay inside subscription limits |
| Diff reviewer (J2) | opencode `big-pickle` (free) | local `gemma4:12b` | A different model family from the implementer, on purpose |
| CV judge (J1) | local `gemma4:12b` via Ollama | opencode free models | Local runs are free, so 3-run majority votes cost nothing. Needs a new `ollama` backend in `llm_judge.py` (§8, M2). |
| Bulk/cheap tasks (metrics summaries, PR body drafting) | local `gemma4:12b` | — | |
| Google Gemini | only if the key is on the free tier | — | An optional second-opinion judge. Check AI Studio's quota before enabling it, to stay at zero spend. |

**How the local flow works:** Ollama serves an OpenAI-compatible API at `http://localhost:11434/v1` and supports JSON-schema structured output (`format: <schema>`), which matches the judge's existing `SCHEMA`. Two ways to wire it up:
1. **Directly**: add a `ollama` backend to `llm_judge.py` that POSTs to `/api/chat` with `format=SCHEMA, options={temperature:0, seed:42}`. This is the most deterministic option and the simplest to test.
2. **Through opencode**: add an Ollama provider to `opencode.json` (`@ai-sdk/openai-compatible`, `baseURL: http://localhost:11434/v1`). Any opencode-driven step can then use `ollama/gemma4:12b-it-qat`.

**Limits to plan around:** a 12B model is a weaker judge than Opus. That is exactly why J1 is calibrated on planted defects: if its recall is below ~90%, use `big-pickle` for J1 and keep gemma for bulk work. 32 GB RAM fits quantized models up to ~30B, but at 15 GB free disk a model bigger than ~14B means clearing space first.

**Where money would go later (not now):** an Anthropic API key in repo secrets would let J1/J2 run in CI rather than locally, so PRs from any machine get gated. That is the one capability the zero-spend design gives up. The rest of the pipeline stays the same.

## 7. Safety and risks

| Risk | Mitigation |
|---|---|
| The agent games the tests (weakens a check, edits expected results) | G2 planted defects; the high-risk path class; the stop rule in §5.6; the developer brief |
| The judge is noisy | majority vote, deterministic checks alongside it, the agreement metric, a retry that doesn't count as rework |
| Personal data leaks into a public repo | the fixture persona is fictional; the G0 name check; factory logs on a separate branch hold no CV content, only ids and results |
| The agent runs harmful commands | headless runs use an `--allowedTools` allowlist inside a worktree; no `git push`/`gh` for agents; the runner owns the remote |
| Subscription limits stall the factory | 2 workers; `factory:stuck` on repeated rate-limit errors; opencode as overflow for `S` issues |
| Auto-merge lets a bad change through | low class = docs/tests-only by diff; weekly sample audit; escape-rate threshold shrinks the class |

## 8. Milestones

| # | Milestone | Done when |
|---|---|---|
| **M0** | **Gates first: fixture persona + unit tests + CI** | see §9 |
| M1 | Single-issue runner | `factory/run.sh <issue>` takes one `factory:ready` issue end to end: worktree → `claude -p` → local gates → up to 3 rework loops → PR with generated body → events in `metrics.jsonl`. Tried on 3 real issues. |
| M2 | LLM gates, local | `ollama` backend in `llm_judge.py`; `semantic-bad/` fixtures; J1 majority vote and J2 reviewer posting commit statuses; judge recall measured and written down. |
| M3 | v2 spec + parallel factory | The "write v2 spec" issue run and merged; backlog split; `dispatch.py` running 2 workers with the path-overlap check; `policy.py` auto-merging the low class. |
| M4 | Measure and tune | `report.py` weekly report; first retrospective with real numbers; adjust worker count, the brief and the low-risk list from the data. |

## 9. First milestone (M0): gates first

**Why first:** agents shouldn't be trusted before something can say "no" to them, and the current checks have never been tested themselves. M0 is also useful without any agents.

**Scope (one PR, roughly a day; a good first task for a single supervised `claude -p` run, so its numbers become the factory's baseline):**

1. `fixtures/persona/`: a fictional candidate (`Master_CV.md`, `LinkedIn_Profile.md`, one Career-Input, an `Accomplishment-Log.md`), plus:
   - `good/CV_Fixture_Good.md`: passes every deterministic check.
   - `bad/` with one file per defect: a made-up company, a made-up title, a wrong date, an inflated number, over the word limit, over the page limit.
   - `expected.toml`: bad file → test id that must fail.
2. `tests/conftest.py`: let `--sources-root` / `CV_SOURCES_ROOT` point the checks at the fixture persona, not the vault. This is the one code change to the existing checks, and the default behaviour stays the same.
3. `tests/unit/`: unit tests for `cvcheck` helpers and `llm_judge.parse_answer`.
4. `tests/test_gate_the_gates.py`: runs the checks on each fixture and asserts that good passes and that each bad file fails exactly its expected test.
5. `.github/workflows/gates.yml`: Python 3.12, `pip install -r scripts/requirements.txt pytest ruff`, then `ruff`, `pytest tests/unit tests/test_gate_the_gates.py -m "not llm"`.
6. Branch protection on `main`: require the `gates` check. (This is a repo setting, so the human does it or approves it.)

**M0 is done when:** CI is green on `main`. A throwaway PR that deletes the number check turns CI red through G2. `scripts/check_cv.sh` behaves as before in a real vault.
