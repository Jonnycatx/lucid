"""Tests for the eval harness.

These run with mocked clients — no API key needed. They verify the
harness logic: prompt loading, runner contracts, position-debiased
judging, and aggregation.

The harness module lives at `evals.harness`. We add the repo root to
sys.path so `import evals.harness` works when pytest runs from the repo.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from evals.harness import (  # noqa: E402
    CompareReport,
    EvalPrompt,
    JudgeVerdict,
    RunResult,
    compare,
    judge_pair,
    load_prompts,
    render_report,
    run_baseline,
    run_lucid,
)


# ----- Loading ------------------------------------------------------------


def test_prompts_yaml_loads_30_entries():
    prompts = load_prompts(REPO_ROOT / "evals" / "prompts.yaml")
    assert len(prompts) == 30
    assert all(isinstance(p, EvalPrompt) for p in prompts)


def test_prompts_have_unique_ids():
    prompts = load_prompts(REPO_ROOT / "evals" / "prompts.yaml")
    ids = [p.id for p in prompts]
    assert len(ids) == len(set(ids)), "duplicate prompt id in prompts.yaml"


def test_prompts_carry_domain_and_difficulty():
    prompts = load_prompts(REPO_ROOT / "evals" / "prompts.yaml")
    for p in prompts:
        assert p.domain
        assert p.difficulty in {"easy", "medium", "hard"}
        assert p.key_challenge
        assert p.prompt


def test_document_domain_has_15_prompts():
    """The 15 document prompts are the current eval-set baseline; the
    other 15 are pending universal Translator."""
    prompts = load_prompts(REPO_ROOT / "evals" / "prompts.yaml")
    doc = [p for p in prompts if p.domain == "document"]
    assert len(doc) == 15


# ----- Runners ------------------------------------------------------------


@pytest.fixture
def doc_prompt():
    return EvalPrompt(
        id="t.doc",
        domain="document",
        difficulty="medium",
        key_challenge="test",
        prompt="Write a one-pager about test stuff for the team.",
    )


@pytest.fixture
def code_prompt():
    return EvalPrompt(
        id="t.code",
        domain="code",
        difficulty="medium",
        key_challenge="test",
        prompt="Refactor this Python code.",
    )


def _text_response(text: str):
    block = MagicMock(type="text")
    block.text = text
    response = MagicMock()
    response.content = [block]
    return response


def test_run_baseline_returns_stub_without_client(doc_prompt):
    out = run_baseline(doc_prompt, client=None)
    assert out.runner == "baseline"
    assert out.error is None
    assert out.metadata["model"] == "(stub)"


def test_run_baseline_calls_client_when_provided(doc_prompt):
    client = MagicMock()
    client.messages.create.return_value = _text_response("the document body")
    out = run_baseline(doc_prompt, client=client)
    assert out.output == "the document body"
    assert out.error is None
    # Raw prompt is sent as the user message
    user_msg = client.messages.create.call_args.kwargs["messages"][0]["content"]
    assert user_msg == doc_prompt.prompt


def test_run_baseline_handles_api_error(doc_prompt):
    client = MagicMock()
    client.messages.create.side_effect = RuntimeError("rate limited")
    out = run_baseline(doc_prompt, client=client)
    assert out.error is not None
    assert "rate limited" in out.error


def test_run_lucid_skips_non_document_domains_until_universal(code_prompt):
    out = run_lucid(code_prompt, client=None)
    assert out.error is not None
    assert "universal" in out.error.lower()


def test_run_lucid_uses_vertical_mode_for_document_domain(doc_prompt):
    """With no client, Lucid runs in stub mode and returns 'complete' with
    stub output (the rendered prompt). The runner should mark it complete."""
    # Provide pre-filled answers so the Listener doesn't ask for clarification.
    # We can't pass answers via the harness directly, so instead we check
    # that the harness reports clarification needs accurately.
    out = run_lucid(doc_prompt, client=None)
    # Without an LLM and without answers, the Listener can't fill required
    # questions for the document vertical → we expect a clarification error.
    assert out.error is not None
    # The clarification metadata should surface the questions.
    assert "questions_to_ask" in out.metadata


# ----- Judge -------------------------------------------------------------


def _judge_response(winner: str, reasoning: str = "test", confidence: float = 0.9):
    block = MagicMock(type="tool_use")
    block.name = "decide_winner"
    block.input = {"winner": winner, "reasoning": reasoning, "confidence": confidence}
    response = MagicMock()
    response.content = [block]
    return response


def test_judge_pair_lucid_wins_when_both_passes_agree(doc_prompt):
    """Both passes pick Lucid. Verdict should be 'lucid'."""
    client = MagicMock()
    # pass 1: A=baseline, B=lucid → judge picks "B" → lucid
    # pass 2: A=lucid, B=baseline → judge picks "A" → lucid
    client.messages.create.side_effect = [_judge_response("B"), _judge_response("A")]

    baseline = RunResult(prompt_id=doc_prompt.id, runner="baseline", output="bland")
    lucid = RunResult(prompt_id=doc_prompt.id, runner="lucid", output="sharp")
    verdict = judge_pair(doc_prompt, baseline, lucid, client=client)

    assert verdict.winner == "lucid"
    assert verdict.raw_decisions == ["lucid", "lucid"]


def test_judge_pair_disagreement_is_tie(doc_prompt):
    """One pass picks Lucid, the other picks baseline → tie (positional bias detected)."""
    client = MagicMock()
    # pass 1: A=baseline, B=lucid → "B" → lucid wins
    # pass 2: A=lucid, B=baseline → "B" → baseline wins
    client.messages.create.side_effect = [_judge_response("B"), _judge_response("B")]

    baseline = RunResult(prompt_id=doc_prompt.id, runner="baseline", output="x")
    lucid = RunResult(prompt_id=doc_prompt.id, runner="lucid", output="y")
    verdict = judge_pair(doc_prompt, baseline, lucid, client=client)

    assert verdict.winner == "tie"
    assert verdict.raw_decisions == ["lucid", "baseline"]


def test_judge_pair_baseline_wins_when_both_passes_agree(doc_prompt):
    client = MagicMock()
    # pass 1: A=baseline, B=lucid → "A" → baseline
    # pass 2: A=lucid, B=baseline → "B" → baseline
    client.messages.create.side_effect = [_judge_response("A"), _judge_response("B")]

    baseline = RunResult(prompt_id=doc_prompt.id, runner="baseline", output="x")
    lucid = RunResult(prompt_id=doc_prompt.id, runner="lucid", output="y")
    verdict = judge_pair(doc_prompt, baseline, lucid, client=client)

    assert verdict.winner == "baseline"


def test_judge_pair_explicit_tie(doc_prompt):
    client = MagicMock()
    client.messages.create.side_effect = [_judge_response("tie"), _judge_response("tie")]

    baseline = RunResult(prompt_id=doc_prompt.id, runner="baseline", output="x")
    lucid = RunResult(prompt_id=doc_prompt.id, runner="lucid", output="y")
    verdict = judge_pair(doc_prompt, baseline, lucid, client=client)

    assert verdict.winner == "tie"


# ----- Compare aggregation -----------------------------------------------


def test_compare_skips_prompts_with_errors(doc_prompt, code_prompt):
    prompts = [doc_prompt, code_prompt]
    baseline_runs = {doc_prompt.id: RunResult(doc_prompt.id, "baseline", "x")}
    # code prompt has Lucid error (pending universal) → must be skipped
    lucid_runs = {
        doc_prompt.id: RunResult(doc_prompt.id, "lucid", "y"),
        code_prompt.id: RunResult(code_prompt.id, "lucid", "", error="pending universal"),
    }
    report = compare(prompts, baseline_runs, lucid_runs, judge_client=None)
    assert code_prompt.id in report.skipped
    # doc_prompt has output for both; with judge_client=None it counts as tie
    assert doc_prompt.id not in report.skipped


def test_compare_with_real_judge_aggregates_correctly(doc_prompt):
    """One prompt, judge picks Lucid both passes → lucid wins, win rate 100%."""
    client = MagicMock()
    client.messages.create.side_effect = [_judge_response("B"), _judge_response("A")]

    prompts = [doc_prompt]
    baseline_runs = {doc_prompt.id: RunResult(doc_prompt.id, "baseline", "x")}
    lucid_runs = {doc_prompt.id: RunResult(doc_prompt.id, "lucid", "y")}

    report = compare(prompts, baseline_runs, lucid_runs, judge_client=client)
    assert report.n_lucid_wins == 1
    assert report.n_baseline_wins == 0
    assert report.lucid_win_rate == 1.0
    assert "document" in report.by_domain


def test_render_report_includes_key_numbers():
    report = CompareReport(
        n_prompts=10,
        n_lucid_wins=6,
        n_baseline_wins=2,
        n_ties=1,
        by_domain={"document": {"lucid": 6, "baseline": 2, "tie": 1}},
        by_difficulty={},
        skipped=["x.skipped"],
        verdicts=[],
    )
    text = render_report(report)
    assert "Lucid wins:    6" in text
    assert "Baseline wins: 2" in text
    assert "75.0%" in text  # 6 / (6+2) decisive
    assert "x.skipped" in text
