"""
analyze_results.py - Evaluate all collected results
Run this AFTER Phase 3 data collection is complete
"""

import json
from importlib import util
from itertools import combinations
from pathlib import Path

import pandas as pd

from evaluation import MetricsCalculator


ROOT = Path(__file__).resolve().parents[1]
RESULTS_PATH = ROOT / "outputs" / "raw_responses" / "results.json"
METRICS_DIR = ROOT / "outputs" / "metrics"
RAW_OUTPUT_DIR = ROOT / "outputs" / "raw_responses"
STATS_DIR = METRICS_DIR / "statistics"
SRC_DIR = Path(__file__).resolve().parent

statistics_spec = util.spec_from_file_location("prompt_statistics", SRC_DIR / "statistics.py")
statistics_module = util.module_from_spec(statistics_spec)
assert statistics_spec.loader is not None
statistics_spec.loader.exec_module(statistics_module)
StatisticalAnalyzer = statistics_module.StatisticalAnalyzer


def analyze_all_results():
    print("=" * 60)
    print("PHASE 4: EVALUATION AND ANALYSIS")
    print("=" * 60)

    METRICS_DIR.mkdir(parents=True, exist_ok=True)

    print("\n1. Loading results...")
    with open(RESULTS_PATH, "r", encoding="utf-8") as f:
        results = json.load(f)

    print(f"   Loaded {len(results)} responses")

    calc = MetricsCalculator()

    print("\n2. Computing metrics...")
    for i, r in enumerate(results):
        if i % 1000 == 0:
            print(f"   Processing: {i}/{len(results)}")

        eval_result = calc.evaluate_response(
            prediction=r["response"],
            ground_truth=r["gold_answer"],
            task_type=r["dataset"],
        )
        r["accuracy"] = eval_result["accuracy"]
        r["hallucination_rate"] = eval_result["hallucination_rate"]
        r["response_length"] = eval_result["response_length"]

    print("\n3. Saving enriched results...")
    results_json_path = RAW_OUTPUT_DIR / "results_with_metrics.json"
    results_csv_path = RAW_OUTPUT_DIR / "results_with_metrics.csv"
    with open(results_json_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    df = pd.DataFrame(results)
    df.to_csv(results_csv_path, index=False)

    print("\n4. Generating summaries...")

    overall = {
        "total_responses": len(df),
        "overall_accuracy": df["accuracy"].mean(),
        "overall_hallucination_rate": df["hallucination_rate"].mean(),
        "avg_response_length": df["response_length"].mean(),
    }

    by_model = df.groupby("model").agg(
        {
            "accuracy": "mean",
            "hallucination_rate": "mean",
            "response_length": "mean",
        }
    ).round(4)

    by_dataset = df.groupby("dataset").agg(
        {
            "accuracy": "mean",
            "hallucination_rate": "mean",
            "response_length": "mean",
        }
    ).round(4)

    by_prompt_type = df.groupby("prompt_type").agg(
        {
            "accuracy": "mean",
            "hallucination_rate": "mean",
            "response_length": "mean",
        }
    ).round(4)

    by_prompt_id = df.groupby("prompt_id").agg(
        {
            "accuracy": "mean",
            "hallucination_rate": "mean",
            "response_length": "mean",
        }
    ).round(4)

    cross_model_prompt = pd.crosstab(
        df["model"],
        df["prompt_type"],
        values=df["accuracy"],
        aggfunc="mean",
    ).round(4)

    overall_df = pd.DataFrame([overall])
    overall_df.to_csv(METRICS_DIR / "overall.csv", index=False)
    by_model.to_csv(METRICS_DIR / "by_model.csv")
    by_dataset.to_csv(METRICS_DIR / "by_dataset.csv")
    by_prompt_type.to_csv(METRICS_DIR / "by_prompt_type.csv")
    by_prompt_id.to_csv(METRICS_DIR / "by_prompt_id.csv")
    cross_model_prompt.to_csv(METRICS_DIR / "cross_model_prompt.csv")

    print("\n5. Generating statistical tables...")
    STATS_DIR.mkdir(parents=True, exist_ok=True)

    analyzer = StatisticalAnalyzer()
    stat_rows = []

    # Pairwise prompt-type comparisons within each model.
    for model_name, model_df in df.groupby("model"):
        for prompt_a, prompt_b in combinations(model_df["prompt_type"].unique(), 2):
            scores_a = model_df[model_df["prompt_type"] == prompt_a]["accuracy"].tolist()
            scores_b = model_df[model_df["prompt_type"] == prompt_b]["accuracy"].tolist()
            ttest_result = analyzer.paired_ttest(scores_a, scores_b)
            stat_rows.append(
                {
                    "scope": "model_prompt_type",
                    "group": model_name,
                    "condition_a": prompt_a,
                    "condition_b": prompt_b,
                    **ttest_result,
                }
            )

    # Pairwise prompt-variant comparisons within each prompt family.
    for prompt_type, prompt_df in df.groupby("prompt_type"):
        prompt_ids = sorted(prompt_df["prompt_id"].unique())
        for prompt_a, prompt_b in combinations(prompt_ids, 2):
            scores_a = prompt_df[prompt_df["prompt_id"] == prompt_a]["accuracy"].tolist()
            scores_b = prompt_df[prompt_df["prompt_id"] == prompt_b]["accuracy"].tolist()
            ttest_result = analyzer.paired_ttest(scores_a, scores_b)
            stat_rows.append(
                {
                    "scope": "prompt_variant",
                    "group": prompt_type,
                    "condition_a": prompt_a,
                    "condition_b": prompt_b,
                    **ttest_result,
                }
            )

    ttest_df = pd.DataFrame(stat_rows)
    ttest_df.to_csv(STATS_DIR / "paired_ttests.csv", index=False)

    anova_rows = []
    for model_name, model_df in df.groupby("model"):
        groups = [group["accuracy"].tolist() for _, group in model_df.groupby("prompt_type")]
        anova_result = analyzer.anova(*groups)
        anova_rows.append({"scope": "model_prompt_type", "group": model_name, **anova_result})

    for prompt_type, prompt_df in df.groupby("prompt_type"):
        groups = [group["accuracy"].tolist() for _, group in prompt_df.groupby("prompt_id")]
        if len(groups) >= 2:
            anova_result = analyzer.anova(*groups)
            anova_rows.append({"scope": "prompt_variant", "group": prompt_type, **anova_result})

    anova_df = pd.DataFrame(anova_rows)
    anova_df.to_csv(STATS_DIR / "anova.csv", index=False)

    print(f"   Saved paired t-tests to {STATS_DIR / 'paired_ttests.csv'}")
    print(f"   Saved ANOVA results to {STATS_DIR / 'anova.csv'}")

    print("\n" + "=" * 60)
    print("RESULTS SUMMARY")
    print("=" * 60)

    print("\n📊 OVERALL:")
    print(f"   Total responses: {overall['total_responses']}")
    print(f"   Accuracy: {overall['overall_accuracy']:.3f}")
    print(f"   Hallucination rate: {overall['overall_hallucination_rate']:.3f}")
    print(f"   Avg response length: {overall['avg_response_length']:.1f} words")

    print("\n🤖 BY MODEL:")
    print(by_model.to_string())

    print("\n📚 BY DATASET:")
    print(by_dataset.to_string())

    print("\n📝 BY PROMPT TYPE:")
    print(by_prompt_type.to_string())

    print("\n🔢 BY PROMPT VARIANT:")
    print(by_prompt_id.to_string())

    print("\n📊 MODEL × PROMPT TYPE (Accuracy):")
    print(cross_model_prompt.to_string())

    print("\n✅ All summaries saved to outputs/metrics/")
    print("✅ Statistical tables saved to outputs/metrics/statistics/")

    return df


if __name__ == "__main__":
    analyze_all_results()