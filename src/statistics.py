"""
statistics.py - Statistical analysis for prompt comparison
Includes: paired t-tests, p-value heatmaps, ANOVA, Cohen's d
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats
from scipy.stats import ttest_rel, f_oneway
from typing import List, Dict, Tuple

SRC_DIR = Path(__file__).resolve().parent

if str(SRC_DIR) in sys.path:
    sys.path.remove(str(SRC_DIR))

import seaborn as sns
import matplotlib.pyplot as plt

sys.path.insert(0, str(SRC_DIR))

class StatisticalAnalyzer:
    def __init__(self):
        self.results = None
    
    def paired_ttest(self, condition_a: List[float], condition_b: List[float]) -> Dict[str, float]:
        """
        Paired t-test comparing two prompt variants.
        Returns t-statistic, p-value, and significance decision.
        """
        t_stat, p_value = ttest_rel(condition_a, condition_b)
        
        return {
            "t_statistic": t_stat,
            "p_value": p_value,
            "significant": p_value < 0.05,
            "effect_direction": "better" if np.mean(condition_a) > np.mean(condition_b) else "worse"
        }
    
    def cohens_d(self, condition_a: List[float], condition_b: List[float]) -> float:
        """
        Calculate Cohen's d effect size.
        Small = 0.2, Medium = 0.5, Large = 0.8
        """
        mean_a, mean_b = np.mean(condition_a), np.mean(condition_b)
        std_a, std_b = np.std(condition_a, ddof=1), np.std(condition_b, ddof=1)
        
        # Pooled standard deviation
        n_a, n_b = len(condition_a), len(condition_b)
        pooled_std = np.sqrt(((n_a - 1) * std_a**2 + (n_b - 1) * std_b**2) / (n_a + n_b - 2))
        
        return (mean_a - mean_b) / pooled_std
    
    def anova(self, *groups: List[float]) -> Dict[str, float]:
        """
        One-way ANOVA for comparing 3+ conditions.
        Example: length variants (short, medium, long)
        """
        f_stat, p_value = f_oneway(*groups)
        
        return {
            "f_statistic": f_stat,
            "p_value": p_value,
            "significant": p_value < 0.05
        }
    
    def create_pvalue_heatmap(self, 
                              results_matrix: pd.DataFrame, 
                              title: str = "P-value Heatmap",
                              output_path: str = "outputs/figures/pvalue_heatmap.png"):
        """
        Create p-value heatmap following Errica et al. (2024) Figure 3.
        Green = better performance, Red = worse performance.
        """
        # Create mask for upper triangle (to avoid redundancy)
        mask = np.triu(np.ones_like(results_matrix, dtype=bool))
        
        # Create heatmap
        plt.figure(figsize=(10, 8))
        
        # Custom color map: green for low p-values (significant better)
        # Red for high p-values (significant worse)
        cmap = sns.diverging_palette(145, 10, as_cmap=True)
        
        ax = sns.heatmap(
            results_matrix,
            mask=mask,
            annot=True,  # Show p-values
            fmt='.3f',
            cmap=cmap,
            center=0.05,  # Center at alpha=0.05
            vmin=0,
            vmax=0.1,
            square=True,
            linewidths=0.5,
            cbar_kws={"label": "p-value"}
        )
        
        plt.title(title, fontsize=14)
        plt.tight_layout()
        plt.savefig(output_path, dpi=300)
        plt.close()
        
        print(f"Heatmap saved to {output_path}")
    
    def compare_prompt_variants(self, 
                                data: pd.DataFrame,
                                metric: str = "accuracy",
                                prompt_variant_col: str = "prompt_type") -> pd.DataFrame:
        """
        Compare all prompt variants pairwise.
        Returns matrix of p-values.
        """
        variants = data[prompt_variant_col].unique()
        n = len(variants)
        
        # Initialize p-value matrix
        p_matrix = pd.DataFrame(np.ones((n, n)), index=variants, columns=variants)
        
        # Pairwise comparisons
        for i, var_a in enumerate(variants):
            for j, var_b in enumerate(variants):
                if i < j:  # Only calculate upper triangle
                    scores_a = data[data[prompt_variant_col] == var_a][metric].values
                    scores_b = data[data[prompt_variant_col] == var_b][metric].values
                    
                    # Paired t-test
                    _, p_val = ttest_rel(scores_a, scores_b)
                    p_matrix.loc[var_a, var_b] = p_val
                    p_matrix.loc[var_b, var_a] = p_val
        
        return p_matrix
    
    def summarize_statistics(self, data: pd.DataFrame, group_col: str, metric_col: str) -> pd.DataFrame:
        """
        Generate summary statistics (mean, std, SEM) for each condition.
        """
        summary = data.groupby(group_col)[metric_col].agg([
            ('mean', 'mean'),
            ('std', 'std'),
            ('sem', lambda x: stats.sem(x, ddof=1)),
            ('n', 'count')
        ]).reset_index()
        
        # Add 95% confidence interval
        summary['ci_95_lower'] = summary['mean'] - 1.96 * summary['sem']
        summary['ci_95_upper'] = summary['mean'] + 1.96 * summary['sem']
        
        return summary


# Example usage
if __name__ == "__main__":
    analyzer = StatisticalAnalyzer()
    
    # Example data
    short_scores = [0.85, 0.82, 0.88, 0.84, 0.86]
    medium_scores = [0.90, 0.89, 0.92, 0.88, 0.91]
    long_scores = [0.87, 0.85, 0.89, 0.86, 0.88]
    
    # Paired t-test
    result = analyzer.paired_ttest(short_scores, medium_scores)
    print(f"Short vs Medium: p={result['p_value']:.4f}, {result['effect_direction']}")
    
    # Cohen's d
    d = analyzer.cohens_d(short_scores, medium_scores)
    print(f"Effect size (Cohen's d): {d:.3f}")
    
    # ANOVA
    anova_result = analyzer.anova(short_scores, medium_scores, long_scores)
    print(f"ANOVA: F={anova_result['f_statistic']:.3f}, p={anova_result['p_value']:.4f}")