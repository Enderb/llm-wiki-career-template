"""LLM-as-judge check: fails if the model finds any CV claim it cannot trace to a
source file. Backend selection and caching live in tests/llm_judge.py."""
import pytest

from llm_judge import JudgeError, JudgeUnavailable, judge


@pytest.mark.llm
def test_llm_judge(cv, sources, conf, request):
    try:
        verdict = judge(cv.text, sources.files, conf)
    except JudgeUnavailable as exc:
        pytest.skip(str(exc))
    except JudgeError as exc:
        pytest.fail(f"judge could not run: {exc}", pytrace=False)

    info = f"{verdict.backend}, {verdict.model}, {verdict.claims_checked} claims checked"
    if verdict.skipped_backends:
        info += ", fell back from " + "/".join(verdict.skipped_backends)
    request.node._cv_info = info + (", cached" if verdict.cached else "")
    if verdict.unsupported:
        lines = [f"{len(verdict.unsupported)} claim(s) the judge could not trace to a source:"]
        for c in verdict.unsupported:
            excerpt = c.get("cv_excerpt") or c.get("claim", "")
            lines.append(f'- "{excerpt}"')
            if c.get("reason"):
                lines.append(f"    why: {c['reason']}")
        lines.append("Fix: remove or reword each claim, or add the evidence to a raw source first.")
        pytest.fail("\n".join(lines), pytrace=False)
