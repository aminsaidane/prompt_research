# -*- coding: utf-8 -*-
"""
analyze_results.py - Evaluate all collected results
Run this AFTER Phase 3 data collection is complete
"""

import json
import sys
import importlib.util
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

# Dynamic import to avoid name collision with stdlib statistics
spec = importlib.util.spec_from_file_location("prompt_statistics", str(SRC_DIR / "statistics.py"))
stats_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(stats_module)
StatisticalAnalyzer = stats_module.StatisticalAnalyzer


def analyze_all_results():
    print("=" * 60)
    print("PHASE 4: EVALUATION AND ANALYSIS")
    print("=" * 60)

    METRICS_DIR.mkdir(parents=True, exist_ok=True)
    STATS_DIR.mkdir(parents=True, exist_ok=True)

    print("\n1. Loading results...")
    with open(RESULTS_PATH, "r", encoding="utf-8") as f:
        results = json.load(f)

    print("   Loaded {} responses".format(len(results)))

    calc = MetricsCalculator()

    print("\n2. Computing metrics...")
    for i, r in enumerate(results):
        if i % 1000 == 0:
            print("   Processing: {}/{}".format(i, len(results)))

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

    analyzer = StatisticalAnalyzer()

    print("\n5. Running paired t-tests...")
    paired_results = []
    
    # Within-model comparisons
    for model in df["model"].unique():
        model_data = df[df["model"] == model]
        for prompt_type_a, prompt_type_b in combinations(["length", "redundancy", "density"], 2):
            data_a = model_data[model_data["prompt_type"] == prompt_type_a]["accuracy"].values
            data_b = model_data[model_data["prompt_type"] == prompt_type_b]["accuracy"].values
            
            if len(data_a) > 1 and len(data_b) > 1:
                test_result = analyzer.paired_ttest(data_a.tolist(), data_b.tolist())
                paired_results.append({
                    "scope": "model_prompt_type",
                    "group": model,
                    "condition_a": prompt_type_a,
                    "condition_b": prompt_type_b,
                    "t_statistic": test_result["t_statistic"],
                    "p_value": test_result["p_value"],
                    "significant": test_result["significant"],
                    "effect_direction": test_result["effect_direction"]
                })
    
    # Within-prompt-family comparisons
    for prompt_type in ["length", "redundancy", "density"]:
        prompt_data = df[df["prompt_type"] == prompt_type]
        prompt_ids = sorted(prompt_data["prompt_id"].unique())
        
        for id_a, id_b in combinations(prompt_ids, 2):
            data_a = prompt_data[prompt_data["prompt_id"] == id_a]["accuracy"].values
            data_b = prompt_data[prompt_data["prompt_id"] == id_b]["accuracy"].values
            
            if len(data_a) > 1 and len(data_b) > 1:
                test_result = analyzer.paired_ttest(data_a.tolist(), data_b.tolist())
                paired_results.append({
                    "scope": "prompt_variant",
                    "group": prompt_type,
                    "condition_a": id_a,
                    "condition_b": id_b,
                    "t_statistic": test_result["t_statistic"],
                    "p_value": test_result["p_value"],
                    "significant": test_result["significant"],
                    "effect_direction": test_result["effect_direction"]
                })
    
    paired_df = pd.DataFrame(paired_results)
    paired_df.to_csv(STATS_DIR / "paired_ttests.csv", index=False)

    print("\n6. Running ANOVA tests...")
    anova_results = []
    
    # Model × Prompt Type ANOVA
    for model in df["model"].unique():
        model_data = df[df["model"] == model]
        length_acc = model_data[model_data["prompt_type"] == "length"]["accuracy"].values
        density_acc = model_data[model_data["prompt_type"] == "density"]["accuracy"].values
        redundancy_acc = model_data[model_data["prompt_type"] == "redundancy"]["accuracy"].values
        
        if len(length_acc) > 0 and len(density_acc) > 0 and len(redundancy_acc) > 0:
            anova_result = analyzer.anova(length_acc.tolist(), density_acc.tolist(), redundancy_acc.tolist())
            anova_results.append({
                "scope": "model_prompt_type",
                "group": model,
                "f_statistic": anova_result["f_statistic"],
                "p_value": anova_result["p_value"],
                "significant": anova_result["significant"]
            })
    
    # Prompt Family ANOVA
    for prompt_type in ["length", "redundancy", "density"]:
        prompt_data = df[df["prompt_type"] == prompt_type]
        prompt_ids = sorted(prompt_data["prompt_id"].unique())
        
        groups = [prompt_data[prompt_data["prompt_id"] == pid]["accuracy"].values.tolist() 
                  for pid in prompt_ids if len(prompt_data[prompt_data["prompt_id"] == pid]) > 0]
        
        if len(groups) >= 2:
            anova_result = analyzer.anova(*groups)
            anova_results.append({
                "scope": "prompt_variant",
                "group": prompt_type,
                "f_statistic": anova_result["f_statistic"],
                "p_value": anova_result["p_value"],
                "significant": anova_result["significant"]
            })
    
    anova_df = pd.DataFrame(anova_results)
    anova_df.to_csv(STATS_DIR / "anova.csv", index=False)

    print("\n=== SUMMARY RESULTS ===")
    print("\n📊 OVERALL:")
    for key, value in overall.items():
        print("  {}: {:.4f}".format(key, value))

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
