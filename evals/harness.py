"""Lucid evaluation harness.

Pipeline:
  1. Load eval prompts from prompts.yaml.
  2. For each prompt, run baseline (raw prompt → execution model) and
     Lucid (intent → Lucid pipeline → execution model). Save outputs.
  3. Pairwise judge each (baseline, lucid) pair using a stronger model
     with positional debiasing — judge twice with positions swapped;
     disagreements count as ties.
  4. Aggregate: win rate, by domain, by difficulty.

This module is testable without an API key: every external boundary
takes a client argument that defaults to None (stub mode).

Run via the CLI:
    python -m evals.harness compare --limit 5
    python -m evals.harness compare --domain document
    python -m evals.harness compare --all
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Optional, TYPE_CHECKING

import yaml

if TYPE_CHECKING:
    from anthropic import Anthropic


# ----- Models ------------------------------------------------------------


# Strong model used for pairwise judging — must be different from the
# execution model to reduce self-preference bias.
JUDGE_MODEL = "claude-opus-4-6"
JUDGE_MAX_TOKENS = 1024

# Default execution model used for both baseline and Lucid runs.
EXECUTION_MODEL = "claude-sonnet-4-6"
EXECUTION_MAX_TOKENS = 4096


# ----- Data ---------------------------------------------------------------


@dataclass
class EvalPrompt:
    id: str
    domain: str
    difficulty: str
    key_challenge: str
    prompt: str


@dataclass
class RunResult:
    prompt_id: str
    runner: str  # "baseline" or "lucid"
    output: str
    error: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class JudgeVerdict:
    prompt_id: str
    winner: str  # "baseline", "lucid", or "tie"
    raw_decisions: list[str]  # one per swapped run
    reasoning: str
    confidence: float


@dataclass
class CompareReport:
    n_prompts: int
    n_lucid_wins: int
    n_baseline_wins: int
    n_ties: int
    by_domain: dict[str, dict[str, int]]
    by_difficulty: dict[str, dict[str, int]]
    skipped: list[str]
    verdicts: list[JudgeVerdict]

    @property
    def lucid_win_rate(self) -> float:
        decisive = self.n_lucid_wins + self.n_baseline_wins
        return (self.n_lucid_wins / decisive) if decisive else 0.0


# ----- Loading ------------------------------------------------------------


def load_prompts(path: Path | str) -> list[EvalPrompt]:
    with open(path) as f:
        raw = yaml.safe_load(f)
    return [EvalPrompt(**p) for p in raw["prompts"]]


# ----- Runners ------------------------------------------------------------


def run_baseline(
    prompt: EvalPrompt,
    *,
    client: Optional["Anthropic"] = None,
    model: str = EXECUTION_MODEL,
    max_tokens: int = EXECUTION_MAX_TOKENS,
) -> RunResult:
    """Send the raw prompt directly to the execution model."""
    if client is None:
        return RunResult(
            prompt_id=prompt.id,
            runner="baseline",
            output=f"[stub: no client] {prompt.prompt[:80]}...",
            metadata={"model": "(stub)"},
        )
    try:
        response = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt.prompt}],
        )
        text = "\n".join(b.text for b in response.content if getattr(b, "type", None) == "text")
        return RunResult(
            prompt_id=prompt.id,
            runner="baseline",
            output=text.strip(),
            metadata={"model": model},
        )
    except Exception as e:  # noqa: BLE001
        return RunResult(prompt_id=prompt.id, runner="baseline", output="", error=str(e))


SKILL_PATH = Path(__file__).resolve().parents[1] / "skill" / "lucid-fluency" / "SKILL.md"


def _load_skill_body(skill_path: Path = SKILL_PATH) -> str:
    """Load the standalone skill SKILL.md and strip the YAML frontmatter.

    The skill body is what would be loaded into a Claude session as the
    skill's instructions. We send it as a system prompt for the eval.
    """
    raw = skill_path.read_text()
    # Strip the YAML frontmatter (between the first two '---' delimiters).
    if raw.startswith("---"):
        end = raw.find("---", 3)
        if end != -1:
            return raw[end + 3:].lstrip()
    return raw


def run_skill(
    prompt: EvalPrompt,
    *,
    client: Optional["Anthropic"] = None,
    model: str = EXECUTION_MODEL,
    max_tokens: int = EXECUTION_MAX_TOKENS,
    skill_path: Path = SKILL_PATH,
) -> RunResult:
    """Run the prompt through the standalone fluency skill.

    The skill body is sent as a system prompt to the execution model. This
    simulates what happens when a user has the skill installed in Claude
    Desktop or Cowork and the skill activates on their request.

    No clarification round-trip is performed — for the eval we measure
    one-shot output quality. The skill version's true two-turn behavior
    (asking for missing dimensions) cannot be measured in a one-shot eval
    and is captured separately by manual usability testing.
    """
    if client is None:
        return RunResult(
            prompt_id=prompt.id,
            runner="skill",
            output=f"[stub: no client] {prompt.prompt[:80]}...",
            metadata={"model": "(stub)"},
        )
    try:
        skill_body = _load_skill_body(skill_path)
        response = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=skill_body,
            messages=[{"role": "user", "content": prompt.prompt}],
        )
        text = "\n".join(b.text for b in response.content if getattr(b, "type", None) == "text")
        return RunResult(
            prompt_id=prompt.id,
            runner="skill",
            output=text.strip(),
            metadata={"model": model, "skill_path": str(skill_path)},
        )
    except Exception as e:  # noqa: BLE001
        return RunResult(prompt_id=prompt.id, runner="skill", output="", error=str(e))


def run_lucid(
    prompt: EvalPrompt,
    *,
    client: Optional["Anthropic"] = None,
    model: str = EXECUTION_MODEL,
) -> RunResult:
    """Run the prompt through Lucid's pipeline.

    Triage selects a specialized vertical when one matches; otherwise the
    `general.fluency` fallback vertical handles the request. Every prompt
    therefore gets a real Lucid run — no domain-based skip list.

    If the Listener still surfaces clarification (e.g. a specialized
    vertical's required questions are unrecoverable from the intent), the
    eval marks that prompt as skipped — the harness measures one-shot
    output quality.
    """
    from lucid.server import run_lucid as lucid_pipeline

    result = lucid_pipeline(intent=prompt.prompt, client=client)

    if result.get("status") == "complete":
        return RunResult(
            prompt_id=prompt.id,
            runner="lucid",
            output=result["result"],
            metadata={
                "model": result.get("model_used", "(stub)"),
                "vertical": result["vertical"]["id"],
                "answers_used": result.get("answers_used", {}),
            },
        )
    if result.get("status") == "needs_clarification":
        return RunResult(
            prompt_id=prompt.id,
            runner="lucid",
            output="",
            error="Lucid asked for clarification — eval measures one-shot quality.",
            metadata={"questions_to_ask": result.get("questions_to_ask", [])},
        )
    return RunResult(
        prompt_id=prompt.id,
        runner="lucid",
        output="",
        error=f"Lucid status: {result.get('status')}",
    )


# ----- Judge --------------------------------------------------------------


JUDGE_TOOL = {
    "name": "decide_winner",
    "description": "Decide which response better delivers what the user asked for.",
    "input_schema": {
        "type": "object",
        "properties": {
            "winner": {
                "type": "string",
                "enum": ["A", "B", "tie"],
                "description": "Which response wins, or tie if neither is clearly better.",
            },
            "reasoning": {
                "type": "string",
                "description": "One to three sentences explaining the decision.",
            },
            "confidence": {
                "type": "number",
                "description": "Confidence in the decision, 0.0-1.0.",
            },
        },
        "required": ["winner", "reasoning", "confidence"],
    },
}


def _judge_once(
    user_prompt: str,
    output_a: str,
    output_b: str,
    *,
    client: "Anthropic",
    model: str = JUDGE_MODEL,
) -> dict[str, Any]:
    """One judging pass with a fixed A/B assignment."""
    judge_user = (
        "You are evaluating two responses to the same user request. Decide "
        "which response better delivers what the user asked for. Consider:\n"
        "- Does it accomplish the actual task or answer the actual question?\n"
        "- Does it respect implicit constraints (audience, tone, format, stakes, hidden requirements)?\n"
        "- Is it well-crafted: specific, concrete, non-generic, appropriate length?\n"
        "- For documents/structured output: does the form match what the user needed?\n"
        "If neither response is clearly better, return 'tie'.\n\n"
        f"USER REQUEST:\n{user_prompt}\n\n"
        f"RESPONSE A:\n{output_a}\n\n"
        f"RESPONSE B:\n{output_b}"
    )
    response = client.messages.create(
        model=model,
        max_tokens=JUDGE_MAX_TOKENS,
        tools=[JUDGE_TOOL],
        tool_choice={"type": "tool", "name": "decide_winner"},
        messages=[{"role": "user", "content": judge_user}],
    )
    for block in response.content:
        if getattr(block, "type", None) == "tool_use" and getattr(block, "name", None) == "decide_winner":
            return getattr(block, "input", {}) or {}
    return {"winner": "tie", "reasoning": "judge did not return a tool call", "confidence": 0.0}


def judge_pair(
    prompt: EvalPrompt,
    baseline: RunResult,
    lucid: RunResult,
    *,
    client: "Anthropic",
    model: str = JUDGE_MODEL,
) -> JudgeVerdict:
    """Pairwise judge with positional debiasing.

    Run the judge twice — once with Lucid as A, once with Lucid as B.
    Only count a win if both passes agree. Disagreements are ties.
    """
    pass_one = _judge_once(prompt.prompt, baseline.output, lucid.output, client=client, model=model)
    pass_two = _judge_once(prompt.prompt, lucid.output, baseline.output, client=client, model=model)

    # In pass_one A=baseline, B=lucid. In pass_two A=lucid, B=baseline.
    p1_winner = pass_one.get("winner")
    p2_winner = pass_two.get("winner")

    p1_normalized = (
        "lucid" if p1_winner == "B" else "baseline" if p1_winner == "A" else "tie"
    )
    p2_normalized = (
        "lucid" if p2_winner == "A" else "baseline" if p2_winner == "B" else "tie"
    )

    if p1_normalized == p2_normalized:
        winner = p1_normalized
    else:
        winner = "tie"

    confidence_avg = (
        (pass_one.get("confidence", 0.0) + pass_two.get("confidence", 0.0)) / 2.0
    )

    return JudgeVerdict(
        prompt_id=prompt.id,
        winner=winner,
        raw_decisions=[p1_normalized, p2_normalized],
        reasoning=f"pass1: {pass_one.get('reasoning', '')} | pass2: {pass_two.get('reasoning', '')}",
        confidence=confidence_avg,
    )


# ----- Compare ------------------------------------------------------------


def compare(
    prompts: list[EvalPrompt],
    baseline_runs: dict[str, RunResult],
    lucid_runs: dict[str, RunResult],
    *,
    judge_client: Optional["Anthropic"] = None,
) -> CompareReport:
    """Run pairwise judging across a prompt set, return a CompareReport.

    Prompts where either runner has no usable output are skipped (counted
    in `skipped`). Judging requires a real client; with judge_client=None
    every comparable prompt counts as a tie (useful for harness tests).
    """
    by_domain: dict[str, dict[str, int]] = {}
    by_difficulty: dict[str, dict[str, int]] = {}
    skipped: list[str] = []
    verdicts: list[JudgeVerdict] = []

    n_lucid_wins = n_baseline_wins = n_ties = 0

    for prompt in prompts:
        baseline = baseline_runs.get(prompt.id)
        lucid = lucid_runs.get(prompt.id)
        if not baseline or not lucid or baseline.error or lucid.error or not lucid.output:
            skipped.append(prompt.id)
            continue

        if judge_client is None:
            verdict = JudgeVerdict(
                prompt_id=prompt.id,
                winner="tie",
                raw_decisions=["stub", "stub"],
                reasoning="no judge client; harness test mode",
                confidence=0.0,
            )
        else:
            verdict = judge_pair(prompt, baseline, lucid, client=judge_client)

        verdicts.append(verdict)
        if verdict.winner == "lucid":
            n_lucid_wins += 1
        elif verdict.winner == "baseline":
            n_baseline_wins += 1
        else:
            n_ties += 1

        for bucket, key in (("by_domain", prompt.domain), ("by_difficulty", prompt.difficulty)):
            target = by_domain if bucket == "by_domain" else by_difficulty
            target.setdefault(key, {"lucid": 0, "baseline": 0, "tie": 0})
            target[key][verdict.winner] += 1

    return CompareReport(
        n_prompts=len(prompts),
        n_lucid_wins=n_lucid_wins,
        n_baseline_wins=n_baseline_wins,
        n_ties=n_ties,
        by_domain=by_domain,
        by_difficulty=by_difficulty,
        skipped=skipped,
        verdicts=verdicts,
    )


def render_report(report: CompareReport) -> str:
    """Plain-text summary of a CompareReport for the CLI."""
    lines = []
    lines.append(f"Prompts evaluated: {report.n_prompts}")
    lines.append(f"  Lucid wins:    {report.n_lucid_wins}")
    lines.append(f"  Baseline wins: {report.n_baseline_wins}")
    lines.append(f"  Ties:          {report.n_ties}")
    lines.append(f"  Skipped:       {len(report.skipped)}")
    if report.n_lucid_wins + report.n_baseline_wins > 0:
        lines.append(f"  Lucid win rate (decisive only): {report.lucid_win_rate:.1%}")
    if report.by_domain:
        lines.append("")
        lines.append("By domain:")
        for domain, counts in sorted(report.by_domain.items()):
            lines.append(f"  {domain:<12} L:{counts['lucid']:<3} B:{counts['baseline']:<3} T:{counts['tie']}")
    if report.skipped:
        lines.append("")
        lines.append(f"Skipped prompt ids ({len(report.skipped)}):")
        for sid in report.skipped:
            lines.append(f"  - {sid}")
    return "\n".join(lines)


# ----- CLI ---------------------------------------------------------------


def _build_client() -> Optional["Anthropic"]:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return None
    from anthropic import Anthropic

    return Anthropic()


def cli_compare(args: argparse.Namespace) -> int:
    prompts_path = Path(args.prompts)
    prompts = load_prompts(prompts_path)
    if args.ids:
        wanted = [s.strip() for s in args.ids.split(",") if s.strip()]
        by_id = {p.id: p for p in prompts}
        missing = [i for i in wanted if i not in by_id]
        if missing:
            print(f"ERROR: prompt ids not found in {prompts_path}: {missing}")
            return 2
        prompts = [by_id[i] for i in wanted]
    else:
        if args.domain:
            prompts = [p for p in prompts if p.domain == args.domain]
        if args.limit:
            prompts = prompts[: args.limit]

    print(f"Loaded {len(prompts)} prompts from {prompts_path}")
    print(f"Treatment runner: {args.runner}")

    client = _build_client()
    if client is None:
        print(
            "ANTHROPIC_API_KEY not set. The harness will run in stub mode "
            "and produce no real measurements."
        )
        return 1

    treatment_runner = run_skill if args.runner == "skill" else run_lucid
    runner_name = args.runner

    print("Running baseline...")
    baseline_runs: dict[str, RunResult] = {}
    for p in prompts:
        baseline_runs[p.id] = run_baseline(p, client=client)
        if baseline_runs[p.id].error:
            print(f"  baseline: {p.id}  [ERROR] {baseline_runs[p.id].error}")
        else:
            print(f"  baseline: {p.id}  ({len(baseline_runs[p.id].output)} chars)")

    print(f"Running {runner_name}...")
    treatment_runs: dict[str, RunResult] = {}
    for p in prompts:
        treatment_runs[p.id] = treatment_runner(p, client=client)
        if treatment_runs[p.id].error:
            print(f"  {runner_name}: {p.id}  [ERROR] {treatment_runs[p.id].error}")
        else:
            print(f"  {runner_name}: {p.id}  ({len(treatment_runs[p.id].output)} chars)")

    print("Judging...")
    # The compare() function expects a `lucid_runs` dict; pass the treatment
    # runs in that slot. The runner name in each RunResult preserves which
    # treatment was actually run.
    report = compare(prompts, baseline_runs, treatment_runs, judge_client=client)

    print()
    print(render_report(report))

    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w") as f:
            json.dump(
                {
                    "report": asdict(report),
                    "runner": runner_name,
                    "baseline": {k: asdict(v) for k, v in baseline_runs.items()},
                    "treatment": {k: asdict(v) for k, v in treatment_runs.items()},
                },
                f,
                indent=2,
            )
        print(f"Wrote results to {out_path}")
    return 0


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="evals.harness",
        description="Lucid evaluation harness — measure win rate vs. raw prompt baseline.",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    compare_parser = sub.add_parser("compare", help="Run baseline + Lucid + judge, print report.")
    compare_parser.add_argument(
        "--prompts",
        default=str(Path(__file__).parent / "prompts.yaml"),
        help="Path to prompts.yaml",
    )
    compare_parser.add_argument("--domain", help="Restrict to a single domain (e.g. 'document').")
    compare_parser.add_argument(
        "--ids",
        help="Comma-separated list of prompt ids to run. Overrides --limit and "
        "--domain. Useful for running a curated cross-vertical sample.",
    )
    compare_parser.add_argument("--limit", type=int, help="Run at most N prompts.")
    compare_parser.add_argument("--output", help="Write full results JSON to this path.")
    compare_parser.add_argument(
        "--runner",
        choices=["skill", "lucid"],
        default="skill",
        help="Treatment runner: 'skill' (the standalone fluency skill, default) or 'lucid' (MCP server).",
    )
    compare_parser.set_defaults(func=cli_compare)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
