"""Lucid evaluation harness.

The harness measures whether Lucid's pipeline produces better output than a
raw prompt to the same execution model. Run via:

    python -m evals.harness --help

The eval set lives in prompts.yaml. Grading uses LLM-as-judge with
positional debiasing (each pair is judged twice with positions swapped;
disagreements count as ties).
"""
