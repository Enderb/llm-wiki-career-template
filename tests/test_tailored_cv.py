"""Deterministic checks: a tailored CV may only state facts found in the sources.

Run through scripts/check_cv.sh, or directly:
    python -m pytest tests --cv 20_Wiki/Career/Applications/Acme/CV_Acme_Role.md
Sources and limits are configured in tests/cv_checks.toml.
"""
import os
import subprocess
import sys
import tempfile

import pytest

from cvcheck import (VAULT, appears_in, fmt_month_year, metric_index, metric_supported,
                     metrics, month_years, word_count, years)


def _fail(title, items, hint):
    lines = [title] + [f"- {i}" for i in items] + [hint]
    pytest.fail("\n".join(lines), pytrace=False)


def test_companies_in_sources(cv, sources):
    assert cv.companies, "no '### Company' headings found under PROFESSIONAL EXPERIENCE"
    missing = [c for c in cv.companies if not appears_in(c, sources)]
    if missing:
        _fail(f"{len(missing)} company name(s) not found in any source:", missing,
              "Fix: use the employer name exactly as the master CV / LinkedIn spells it.")


def test_job_titles_in_sources(cv, sources):
    assert cv.titles, "no '**Job Title**' lines found under PROFESSIONAL EXPERIENCE"
    missing = [t for t in cv.titles if not appears_in(t, sources)]
    if missing:
        _fail(f"{len(missing)} job title(s) not found in any source:", missing,
              "Fix: copy the title verbatim from the master CV / LinkedIn (no upgraded or merged titles).")


def test_dates_in_sources(cv, sources):
    src_my, src_years = month_years(sources.text), years(sources.text)
    body = cv.body_text
    bad = [fmt_month_year(my) for my in sorted(month_years(body), key=lambda t: (t[1], t[0]))
           if my not in src_my]
    bad += [str(y) for y in sorted(years(body)) if y not in src_years]
    if bad:
        _fail(f"{len(bad)} date(s) not found in any source:", bad,
              "Fix: use the start/end dates exactly as the sources give them.")


def test_numbers_in_sources(cv, sources):
    index = metric_index(sources.text)
    seen, bad = set(), []
    for m in metrics(cv.body_text):
        if (m.value, m.unit) in seen:
            continue
        seen.add((m.value, m.unit))
        if not metric_supported(m, index):
            bad.append(m.raw)
    if bad:
        _fail(f"{len(bad)} number(s)/metric(s) not found in any source:", bad,
              "Fix: remove the figure or use the exact number the sources state.")


def test_word_count(cv, conf, request):
    limit = conf["limits"]["max_words"]
    n = word_count(cv)
    request.node._cv_info = f"{n} / {limit} words"
    if n > limit:
        pytest.fail(f"{n} words; the limit is {limit}. Cut {n - limit} words.", pytrace=False)


def test_page_count(cv_path, conf, request):
    try:
        from pdfminer.pdfpage import PDFPage
    except ImportError:
        pytest.skip("pdfminer.six is not installed; run scripts/setup.sh")
    limit = conf["limits"]["max_pages"]
    renderer = os.path.join(VAULT, "scripts", "cv_pdf.py")
    with tempfile.TemporaryDirectory() as tmp:
        out = os.path.join(tmp, "cv.pdf")
        proc = subprocess.run([sys.executable, renderer, cv_path, "--out", out],
                              capture_output=True, text=True, cwd=VAULT)
        if proc.returncode != 0:
            pytest.fail("could not render the PDF with scripts/cv_pdf.py:\n"
                        + proc.stderr.strip()[-800:], pytrace=False)
        with open(out, "rb") as fh:
            pages = sum(1 for _ in PDFPage.get_pages(fh))
    request.node._cv_info = f"{pages} / {limit} pages"
    if pages > limit:
        pytest.fail(f"renders to {pages} pages; the limit is {limit}.", pytrace=False)
