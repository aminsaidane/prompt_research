"""
generate_figures.py - Create visualizations and statistical tests
"""

from importlib import util
from pathlib import Path
import sys

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator, FormatStrFormatter
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = Path(__file__).resolve().parent

# Remove the source directory temporarily so seaborn can import the stdlib
# statistics module instead of src/statistics.py.
if str(SRC_DIR) in sys.path:
    sys.path.remove(str(SRC_DIR))

import seaborn as sns

sys.path.insert(0, str(SRC_DIR))

statistics_spec = util.spec_from_file_location("prompt_statistics", SRC_DIR / "statistics.py")
statistics_module = util.module_from_spec(statistics_spec)
assert statistics_spec.loader is not None
statistics_spec.loader.exec_module(statistics_module)
StatisticalAnalyzer = statistics_module.StatisticalAnalyzer


RESULTS_PATH = ROOT / "outputs" / "raw_responses" / "results_with_metrics.csv"
FIGURES_DIR = ROOT / "outputs" / "figures"


def generate_all_figures():
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(RESULTS_PATH)

    analyzer = StatisticalAnalyzer()

    sns.set_style("whitegrid")
    plt.rcParams["figure.figsize"] = (10, 6)

    fig1, ax = plt.subplots()
    pivot = df.pivot_table(index="model", columns="prompt_type", values="accuracy", aggfunc="mean")
    pivot.plot(kind="bar", ax=ax)
    ax.set_title("Accuracy by Model and Prompt Type")
    ax.set_ylabel("Accuracy")
    ax.set_xlabel("Model")
    ax.legend(title="Prompt Type")
    pivot_values = pivot.to_numpy().flatten()
    pivot_values = pivot_values[~pd.isna(pivot_values)]
    ax.set_ylim([max(0, pivot_values.min() - 0.02), min(1, pivot_values.max() + 0.02)])
    ax.yaxis.set_major_locator(MultipleLocator(0.01))
    ax.yaxis.set_major_formatter(FormatStrFormatter("%.2f"))
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "accuracy_by_model_prompt.png", dpi=300)
    plt.close(fig1)

    fig2, ax = plt.subplots()
    hall_by_prompt = df.groupby("prompt_id")["hallucination_rate"].mean().sort_values()
    hall_by_prompt.plot(kind="bar", ax=ax, color="coral")
    ax.set_title("Hallucination Rate by Prompt Variant")
    ax.set_ylabel("Hallucination Rate")
    ax.set_xlabel("Prompt Variant")
    ax.set_ylim([0, 0.02])
    ax.yaxis.set_major_locator(MultipleLocator(0.0025))
    ax.yaxis.set_major_formatter(FormatStrFormatter("%.3f"))
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "hallucination_by_prompt.png", dpi=300)
    plt.close(fig2)

    fig3, ax = plt.subplots()
    density_df = df[df["prompt_id"].isin(["C1", "C2", "C3"])]
    sns.boxplot(data=density_df, x="prompt_id", y="accuracy", ax=ax, palette="Blues")
    ax.set_title("Accuracy by Constraint Density")
    ax.set_xlabel("Constraint Density (C1=Low, C2=Medium, C3=High)")
    ax.set_ylabel("Accuracy")
    ax.set_ylim([-0.05, 1.05])
    ax.yaxis.set_major_locator(MultipleLocator(0.1))
    ax.yaxis.set_major_formatter(FormatStrFormatter("%.1f"))
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "accuracy_by_density.png", dpi=300)
    plt.close(fig3)

    fig4, ax = plt.subplots()
    redundancy_df = df[df["prompt_id"].isin(["R1", "R2", "R3"])]
    sns.boxplot(data=redundancy_df, x="prompt_id", y="accuracy", ax=ax, palette="Greens")
    ax.set_title("Accuracy by Redundancy Level")
    ax.set_xlabel("Redundancy (R1=None, R2=Medium, R3=High)")
    ax.set_ylabel("Accuracy")
    ax.set_ylim([-0.05, 1.05])
    ax.yaxis.set_major_locator(MultipleLocator(0.1))
    ax.yaxis.set_major_formatter(FormatStrFormatter("%.1f"))
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "accuracy_by_redundancy.png", dpi=300)
    plt.close(fig4)

    length_df = df[df["prompt_type"] == "length"].copy()
    length_scores = (
        length_df.assign(prompt_group=length_df["prompt_id"])[["prompt_group", "accuracy"]]
        .groupby("prompt_group")["accuracy"]
        .apply(list)
        .to_list()
    )
    _ = analyzer.anova(*length_scores)

    fig5, ax = plt.subplots()
    length_pivot = length_df.pivot_table(index="dataset", columns="prompt_id", values="accuracy", aggfunc="mean")
    sns.heatmap(length_pivot, annot=True, fmt=".3f", cmap="viridis", ax=ax)
    ax.set_title("Length Prompts - Accuracy by Dataset")
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "length_accuracy_heatmap.png", dpi=300)
    plt.close(fig5)

    fig6, ax = plt.subplots()
    dataset_acc = df.groupby("dataset")["accuracy"].mean().sort_values()
    dataset_acc.plot(kind="bar", ax=ax, color="purple")
    ax.set_title("Accuracy by Dataset")
    ax.set_ylabel("Accuracy")
    ax.set_ylim([0, 0.7])
    ax.yaxis.set_major_locator(MultipleLocator(0.05))
    ax.yaxis.set_major_formatter(FormatStrFormatter("%.2f"))
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "accuracy_by_dataset.png", dpi=300)
    plt.close(fig6)

    print("✅ All figures saved to outputs/figures/")


if __name__ == "__main__":
    generate_all_figures()