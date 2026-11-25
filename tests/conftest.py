"""pytest wiring for the tailored-CV checks: --cv option, per-CV parametrization,
and the plain-language pass/fail report printed at the end of the run."""
from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from cvcheck import VAULT, find_cvs, load_config, load_sources, parse_cv, rel  # noqa: E402

CHECK_NAMES = {
    "test_companies_in_sources": "Company names appear in sources",
    "test_job_titles_in_sources": "Job titles appear in sources",
    "test_dates_in_sources": "Dates appear in sources",
    "test_numbers_in_sources": "Numbers / metrics appear in sources",
    "test_word_count": "Word count within limit",
    "test_page_count": "Page count within limit",
    "test_llm_judge": "LLM judge: every claim traceable",
}


def pytest_addoption(parser):
    parser.addoption("--cv", action="append", default=[],
                     help="tailored CV markdown to check (repeatable). Default: every CV in the vault.")


def pytest_configure(config):
    config.addinivalue_line("markers", "llm: calls an LLM (skip with -m 'not llm')")
    config._cv_results = []


def _cv_paths(config):
    given = config.getoption("--cv")
    if not given:
        return find_cvs()
    paths = []
    for p in given:
        full = p if os.path.isabs(p) else os.path.abspath(p)
        if not os.path.exists(full):
            full = os.path.join(VAULT, p)
        if not os.path.exists(full):
            raise pytest.UsageError(f"CV not found: {p}")
        paths.append(full)
    return paths


def pytest_generate_tests(metafunc):
    if "cv_path" in metafunc.fixturenames:
        paths = _cv_paths(metafunc.config)
        metafunc.config._cv_count = len(paths)
        metafunc.parametrize("cv_path", paths, ids=[os.path.basename(p) for p in paths])


@pytest.fixture(scope="session")
def conf():
    return load_config()


@pytest.fixture(scope="session")
def sources(conf):
    src = load_sources(conf)
    if not src.files:
        pytest.skip("no source files found (check [sources] in tests/cv_checks.toml)")
    return src


@pytest.fixture
def cv(cv_path):
    parsed = parse_cv(cv_path)
    if not parsed.body:
        pytest.fail(f"could not find the CV body in {rel(cv_path)} "
                    "(expected a '# YOUR NAME' heading)", pytrace=False)
    return parsed


# ------------------------------------------------------------------- report
@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    if not hasattr(item, "callspec") or not isinstance(item.callspec.params.get("cv_path"), str):
        return
    if report.when == "call" or (report.when == "setup" and report.outcome != "passed"):
        if report.passed:
            status, msg = "PASS", ""
        elif report.skipped:
            status = "SKIP"
            msg = report.longrepr[2] if isinstance(report.longrepr, tuple) else str(report.longrepr)
            msg = msg.removeprefix("Skipped: ")
        else:
            status = "FAIL"
            exc = call.excinfo.value if call.excinfo else None
            msg = str(exc) if exc is not None else str(report.longrepr)
        info = getattr(item, "_cv_info", "")
        item.config._cv_results.append(
            (rel(item.callspec.params["cv_path"]), item.originalname, status, msg, info))


def pytest_terminal_summary(terminalreporter, exitstatus, config):
    results = config._cv_results
    if not results:
        if getattr(config, "_cv_count", None) == 0:
            terminalreporter.write_line(
                "No CVs found to check. Pass a path (scripts/check_cv.sh path/to/CV.md) "
                "or see [cvs] in tests/cv_checks.toml.", yellow=True)
        return
    tr = terminalreporter
    colors = {"PASS": {"green": True}, "FAIL": {"red": True, "bold": True}, "SKIP": {"yellow": True}}
    tr.write_sep("=", "CV QUALITY REPORT")
    by_cv = {}
    for cv_rel, test, status, msg, info in results:
        by_cv.setdefault(cv_rel, []).append((test, status, msg, info))
    order = list(CHECK_NAMES)
    for cv_rel, rows in by_cv.items():
        rows.sort(key=lambda r: order.index(r[0]) if r[0] in order else 99)
        verdict = "FAIL" if any(r[1] == "FAIL" for r in rows) else "PASS"
        tr.write_line("")
        tr.write(f"{verdict}  ", **colors[verdict])
        tr.write_line(cv_rel, bold=True)
        for test, status, msg, info in rows:
            tr.write(f"   {status:<4} ", **colors[status])
            tr.write_line(CHECK_NAMES.get(test, test) + (f"  ({info})" if info else ""))
            if status != "PASS" and msg:
                for line in msg.strip().splitlines():
                    tr.write_line(f"          {line}")
    counts = {s: sum(1 for r in results if r[2] == s) for s in ("PASS", "FAIL", "SKIP")}
    failed_cvs = sum(1 for rows in by_cv.values() if any(r[1] == "FAIL" for r in rows))
    tr.write_line("")
    tr.write_sep("-", f"{len(by_cv)} CV(s): {len(by_cv) - failed_cvs} passed, {failed_cvs} failed  |  "
                      f"checks: {counts['PASS']} passed, {counts['FAIL']} failed, {counts['SKIP']} skipped")
    if counts["FAIL"] == 0 and counts["SKIP"]:
        tr.write_line("Some checks were SKIPPED; the CV is not done until they run and pass.", yellow=True)
