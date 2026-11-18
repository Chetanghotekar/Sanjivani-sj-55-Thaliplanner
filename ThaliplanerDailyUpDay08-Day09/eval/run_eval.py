"""Compare two retrieval configurations on the 15-row ThaliPlanner eval set.

Run from the repository root: python -m eval.run_eval
The script writes eval/eval_results.md and replaces the winner section in README.md.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

from app.chunking import ROOT, chunk_documents
from app.embed import embed_texts, MODEL_NAME
from app.rag import should_abstain

EVAL_FILE = ROOT / "eval" / "eval_set.json"
RESULTS_FILE = ROOT / "eval" / "eval_results.md"
README_FILE = ROOT / "README.md"
CONFIGS = [
    {"name": "Config A", "chunk_size": 700, "overlap": 100, "top_k": 3},
    {"name": "Config B", "chunk_size": 900, "overlap": 120, "top_k": 5},
]


def load_eval_set() -> list[dict[str, Any]]:
    rows = json.loads(EVAL_FILE.read_text(encoding="utf-8"))
    if not isinstance(rows, list) or len(rows) != 15:
        raise ValueError("eval/eval_set.json must contain exactly 15 rows")
    return rows


def evaluate_config(rows: list[dict[str, Any]], config: dict[str, Any]) -> dict[str, Any]:
    chunks = chunk_documents(chunk_size=config["chunk_size"], overlap=config["overlap"])
    if not chunks:
        raise RuntimeError("No document chunks found. Check data/records.json and docs/")

    corpus = embed_texts([chunk["text"] for chunk in chunks])
    question_vectors = embed_texts([row["question"] for row in rows])
    detail_rows = []
    passed = 0
    total_expected_terms = 0
    matched_terms = 0

    for row, q_vector in zip(rows, question_vectors):
        scores = np.dot(corpus, q_vector)
        indices = np.argsort(scores)[::-1][:config["top_k"]]
        selected = [chunks[int(i)] for i in indices]
        retrieved_text = "\n".join(
            chunk["text"] + " " + str(chunk["metadata"].get("source", ""))
            for chunk in selected
        ).lower()

        if row["should_abstain"]:
            question_pass = should_abstain(row["question"])
            matched = []
            missing = []
            total_expected_terms += 1
            matched_terms += int(question_pass)
        else:
            expected = row["expected_terms"]
            matched = [term for term in expected if term.lower() in retrieved_text]
            missing = [term for term in expected if term.lower() not in retrieved_text]
            total_expected_terms += len(expected)
            matched_terms += len(matched)
            question_pass = not missing

        passed += int(question_pass)
        detail_rows.append({
            "id": row["id"], "question": row["question"],
            "pass": question_pass, "matched": matched,
            "missing": missing,
            "top_sources": [c["metadata"].get("source", "") for c in selected],
        })

    return {
        **config,
        "chunks": len(chunks),
        "passed": passed,
        "accuracy": passed / len(rows) * 100,
        "term_recall": matched_terms / total_expected_terms * 100 if total_expected_terms else 0,
        "details": detail_rows,
    }


def update_readme(winner: dict[str, Any], results: list[dict[str, Any]]) -> None:
    start = "<!-- RETRIEVAL_EVAL_START -->"
    end = "<!-- RETRIEVAL_EVAL_END -->"
    table = [
        start,
        "## Retrieval configuration experiment",
        "",
        "`python -m eval.run_eval` compares two chunk-size/top-k configurations on all 15 rows in `eval/eval_set.json`. A row passes when all expected evidence terms appear in the retrieved top-k chunks; Q6 passes only when the system is configured to abstain. Term recall is the fraction of expected evidence checks found (Q6 abstention counts as one check).",
        "",
        "| Configuration | Chunk size | Overlap | Top-k | Chunks | Questions passed | Accuracy | Evidence / abstention recall |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for r in results:
        table.append(
            f"| {r['name']} | {r['chunk_size']} | {r['overlap']} | {r['top_k']} | "
            f"{r['chunks']} | {r['passed']}/15 | {r['accuracy']:.1f}% | {r['term_recall']:.1f}% |"
        )
    table += [
        "",
        f"**Winner: {winner['name']}** (highest question-level accuracy: {winner['accuracy']:.1f}%).",
        "",
        end,
    ]
    content = README_FILE.read_text(encoding="utf-8") if README_FILE.exists() else "# ThaliPlanner\n"
    if start in content and end in content:
        before = content.split(start, 1)[0].rstrip()
        after = content.split(end, 1)[1].lstrip()
        updated = before + "\n\n" + "\n".join(table) + ("\n\n" + after if after else "\n")
    else:
        updated = content.rstrip() + "\n\n" + "\n".join(table) + "\n"
    README_FILE.write_text(updated, encoding="utf-8")


def main() -> None:
    rows = load_eval_set()
    results = [evaluate_config(rows, config) for config in CONFIGS]
    # Stable tie-break: choose the smaller/faster configuration when accuracy ties.
    winner = sorted(results, key=lambda r: (r["accuracy"], -r["chunk_size"], -r["top_k"]), reverse=True)[0]

    report = [
        "# ThaliPlanner Retrieval Evaluation",
        "",
        f"- Dataset: `eval/eval_set.json` ({len(rows)} rows)",
        f"- Embedding model: `{MODEL_NAME}`",
        "- Metric: question-level accuracy; every expected term must occur in retrieved top-k evidence. Q6 is correct only when it abstains.",
        "",
        "| Configuration | Chunk size | Overlap | Top-k | Chunks | Passed | Accuracy | Evidence / abstention recall |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for r in results:
        report.append(
            f"| {r['name']} | {r['chunk_size']} | {r['overlap']} | {r['top_k']} | "
            f"{r['chunks']} | {r['passed']}/15 | {r['accuracy']:.1f}% | {r['term_recall']:.1f}% |"
        )
    report += ["", f"**Winner: {winner['name']}**", ""]
    for r in results:
        report += [f"## {r['name']} details", ""]
        for item in r["details"]:
            status = "PASS" if item["pass"] else "FAIL"
            report.append(f"- **Q{item['id']} [{status}]:** {item['question']}")
            if item["missing"]:
                report.append(f"  - Missing evidence terms: {', '.join(item['missing'])}")
        report.append("")
    RESULTS_FILE.write_text("\n".join(report), encoding="utf-8")
    update_readme(winner, results)
    print(f"Evaluation complete: {RESULTS_FILE.relative_to(ROOT)}")
    print(f"README updated with winner table. Winner: {winner['name']} ({winner['accuracy']:.1f}%)")


if __name__ == "__main__":
    main()
