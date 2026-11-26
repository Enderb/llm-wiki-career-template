"""Shared helpers for the tailored-CV quality checks.

Reads a tailored CV markdown file, extracts the CV body exactly as
scripts/cv_pdf.py renders it (Match Summary / Application Notes / Sources are
working notes and are ignored), and loads the source files every claim must
trace back to. Nothing here ever writes to 10_Raw/.
"""
from __future__ import annotations

import fnmatch
import glob
import os
import re
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation

try:
    import tomllib
except ModuleNotFoundError:  # Python < 3.11
    tomllib = None

VAULT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(VAULT, "tests", "cv_checks.toml")

DEFAULT_CONFIG = {
    "sources": {
        "include": [
            "10_Raw/Ground-Truth/*.md",
            "10_Raw/Career-Inputs/**/*.md",
            "20_Wiki/Career/Accomplishment-Log.md",
        ],
        "exclude": ["*_TEMPLATE.md"],
    },
    "cvs": {
        "include": [
            "20_Wiki/Career/Applications/**/CV_*.md",
            "20_Wiki/Career/CV_*.md",
        ],
        "exclude": ["*_TEMPLATE.md"],
    },
    "limits": {"max_words": 900, "max_pages": 2},
    "judge": {
        "backend": "auto",
        "anthropic_model": "claude-opus-5-5",
        "claude_model": "",
        "opencode_model": "",
        "timeout_seconds": 600,
    },
}


def load_config() -> dict:
    conf = {k: dict(v) for k, v in DEFAULT_CONFIG.items()}
    if tomllib and os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "rb") as fh:
            user = tomllib.load(fh)
        for section, values in user.items():
            conf.setdefault(section, {}).update(values)
    env = os.environ
    if env.get("CV_MAX_WORDS"):
        conf["limits"]["max_words"] = int(env["CV_MAX_WORDS"])
    if env.get("CV_MAX_PAGES"):
        conf["limits"]["max_pages"] = int(env["CV_MAX_PAGES"])
    return conf


def _expand(patterns, excludes):
    out = []
    for pat in patterns:
        for path in sorted(glob.glob(os.path.join(VAULT, pat), recursive=True)):
            name = os.path.basename(path)
            if any(fnmatch.fnmatch(name, ex) for ex in excludes):
                continue
            if path not in out:
                out.append(path)
    return out


def find_cvs(conf=None) -> list[str]:
    conf = conf or load_config()
    return _expand(conf["cvs"]["include"], conf["cvs"]["exclude"])


def rel(path: str) -> str:
    return os.path.relpath(path, VAULT)


# --------------------------------------------------------------------- sources
@dataclass
class Sources:
    files: dict[str, str]  # vault-relative path -> raw text

    @property
    def text(self) -> str:
        return "\n\n".join(self.files.values())

    def norm(self) -> str:
        if not hasattr(self, "_norm"):
            self._norm = normalize_text(self.text)
        return self._norm


def load_sources(conf=None) -> Sources:
    conf = conf or load_config()
    paths = _expand(conf["sources"]["include"], conf["sources"]["exclude"])
    files = {}
    for p in paths:
        with open(p, encoding="utf-8") as fh:
            files[rel(p)] = fh.read()
    return Sources(files)


# ------------------------------------------------------------------- CV parse
@dataclass
class CV:
    path: str
    header: list[str] = field(default_factory=list)   # name + contact lines
    body: list[str] = field(default_factory=list)     # everything after contact
    companies: list[str] = field(default_factory=list)
    titles: list[str] = field(default_factory=list)

    @property
    def text(self) -> str:
        return "\n".join(self.header + self.body)

    @property
    def body_text(self) -> str:
        return "\n".join(self.body)


STOP_SECTIONS = ("## APPLICATION NOTES", "## SOURCES")
DASHES = "—–‒−-"  # em, en, figure, minus, hyphen


def parse_cv(path: str) -> CV:
    """Extract the rendered CV body, mirroring scripts/cv_pdf.py."""
    cv = CV(path=path)
    started = False
    in_header = False
    section = ""
    with open(path, encoding="utf-8") as fh:
        lines = fh.read().splitlines()
    for line in lines:
        raw = line.strip()
        if not started:
            # The body starts at the name H1 (e.g. "# JANE DOE"); skip the
            # working-document title ("# CV — Company Role").
            if raw.startswith("# ") and not raw[2:].strip().upper().startswith("CV"):
                started = True
                in_header = True
                cv.header.append(raw[2:].strip())
            continue
        if raw.startswith(STOP_SECTIONS):
            break
        if raw.startswith("## "):
            in_header = False
            section = raw[3:].strip().upper()
        if in_header:
            if raw:
                cv.header.append(raw)
            continue
        cv.body.append(line)
        if "EXPERIENCE" in section:
            if raw.startswith("### "):
                cv.companies.append(_company_name(raw[4:]))
            elif raw.startswith("**"):
                m = re.match(r"\*\*(.+?)\*\*", raw)
                if m:
                    cv.titles.append(m.group(1).strip())
    return cv


def _company_name(heading: str) -> str:
    # "Accretive Technology Group — Live Video Streaming · *Aug. 2019 – Jul. 2025*"
    name = re.split(r"\s+[—–|·]\s+|\s+-\s+", heading)[0]
    name = re.sub(r"\s*\([^)]*\)", "", name)  # drop a parenthetical such as a repo URL
    return strip_md(name).strip()


# --------------------------------------------------------------- normalizing
def strip_md(text: str) -> str:
    text = re.sub(r"\[\[([^\]|]+)\|([^\]]+)\]\]", r"\2", text)  # [[Page|alias]]
    text = re.sub(r"\[\[([^\]]+)\]\]", r"\1", text)              # [[Page]]
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)         # [text](url)
    text = re.sub(r"[*_`>]", "", text)
    return text


def normalize_text(text: str) -> str:
    """Lowercase, unify dashes/quotes/whitespace so wording can be compared."""
    text = strip_md(text).lower()
    text = re.sub("[" + DASHES + "]", " - ", text)
    text = text.replace("’", "'").replace("&", " and ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def appears_in(phrase: str, sources: Sources) -> bool:
    """True if the phrase is in the sources. A dash separator in the CV
    ("Intern — Data Protection") may be written as "for", "at", "," or "|"
    in the source ("Intern for Data Protection")."""
    norm = normalize_text(phrase)
    if norm in sources.norm():
        return True
    parts = [re.escape(p.strip()) for p in norm.split(" - ")]
    if len(parts) < 2:
        return False
    pattern = r"\s*(?:-|for|at|,|\|)\s*".join(parts)
    return re.search(pattern, sources.norm()) is not None


# --------------------------------------------------------------------- dates
MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}
MONTH_YEAR = re.compile(
    r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?,?\s+((?:19|20)\d{2})\b", re.I)
YEAR = re.compile(r"(?<![\d.])((?:19|20)\d{2})(?![\d.%xXkK])")


def month_years(text: str) -> set[tuple[int, int]]:
    return {(MONTHS[m.group(1).lower()[:3]], int(m.group(2))) for m in MONTH_YEAR.finditer(text)}


def years(text: str) -> set[int]:
    return {int(y) for y in YEAR.findall(text)}


def fmt_month_year(my: tuple[int, int]) -> str:
    name = [k for k, v in MONTHS.items() if v == my[0]][0].capitalize()
    return f"{name} {my[1]}"


# ------------------------------------------------------------------- numbers
# A number not glued to a word on its left (so "ZCU216", "v2", "Q3" are skipped),
# with an optional unit glued to it: x/× (multiplier), K/M (thousand/million), %.
NUMBER = re.compile(
    r"(?<![\w.$])(\d+(?:,\d{3})*(?:\.\d+)?)(?:\s*(x(?![a-zA-Z])|×|%)|([kKmM])(?![a-zA-Z]))?(?![\d])")


@dataclass(frozen=True)
class Metric:
    value: str  # canonical numeric string, e.g. "500", "44.3"
    unit: str   # "", "x", "%", "k", "m"
    raw: str

    def label(self) -> str:
        return self.raw


def _canon(num: str) -> str:
    try:
        d = Decimal(num.replace(",", ""))
    except InvalidOperation:
        return num
    s = format(d.normalize(), "f")
    return s


def _prep_numbers(text: str) -> str:
    text = strip_md(text)
    text = re.sub(r"https?://\S+|\b[\w.-]+\.(?:com|org|io|net)\S*", " ", text)
    text = re.sub(r"(\d)\s*(?:times|fold)\b", r"\1x", text, flags=re.I)
    text = re.sub(r"(\d)\s*percent\b", r"\1%", text, flags=re.I)
    text = text.replace("→", " ")  # 3→6
    text = re.sub(r"\b24\s*/\s*7\b", " ", text)  # "24/7" is an expression, not a metric
    return text


def metrics(text: str, skip_years: bool = True) -> list[Metric]:
    out = []
    for m in NUMBER.finditer(_prep_numbers(text)):
        num, unit1, unit2 = m.group(1), m.group(2), m.group(3)
        unit = (unit1 or unit2 or "").lower().replace("×", "x")
        value = _canon(num)
        if skip_years and not unit and re.fullmatch(r"(19|20)\d{2}", num):
            continue  # years are covered by the date check
        out.append(Metric(value, unit, m.group(0).strip()))
    return out


def metric_index(text: str) -> tuple[set[tuple[str, str]], set[str]]:
    found = metrics(text, skip_years=False)
    return {(m.value, m.unit) for m in found}, {m.value for m in found}


def metric_supported(m: Metric, index) -> bool:
    with_unit, bare = index
    if (m.value, m.unit) in with_unit:
        return True
    if not m.unit:
        return m.value in bare
    return False


# ----------------------------------------------------------------- word count
def word_count(cv: CV) -> int:
    text = strip_md(cv.text)
    text = text.replace("|", " ")
    text = re.sub(r"^[\s:-]+$", " ", text, flags=re.M)  # table separator rows
    return len([w for w in text.split() if re.search(r"[A-Za-z0-9]", w)])
