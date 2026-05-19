"""
evaluation.py - Metrics calculation for LLM responses
Measures: Accuracy, BERTScore, Hallucination Rate, Compliance Score
"""

import numpy as np
from typing import List, Dict, Any
import json

class MetricsCalculator:
    def __init__(self):
        # Initialize BERTScore lazily so accuracy/hallucination analysis can run
        # without loading a large model unless semantic similarity is requested.
        self.bertscorer = None
        self._bertscore_model_type = "microsoft/deberta-xlarge-mnli"

    def _get_bertscorer(self):
        if self.bertscorer is None:
            try:
                import torch

                device = "cuda" if torch.cuda.is_available() else "cpu"
            except Exception:
                device = "cpu"

            from bert_score import BERTScorer

            self.bertscorer = BERTScorer(
                model_type=self._bertscore_model_type,
                lang="en",
                rescale_with_baseline=True,
                device=device,
            )
        return self.bertscorer
    
    def calculate_accuracy(self, prediction: str, ground_truth: str) -> float:
        """
        Exact match accuracy for MMLU and GSM8K.
        Returns 1.0 if correct answer appears anywhere in prediction.
        """
        # Strip whitespace and convert to lowercase for comparison
        pred_clean = prediction.strip().lower()
        truth_clean = ground_truth.strip().lower()
        
        # Check if ground truth appears in prediction
        if truth_clean in pred_clean:
            return 1.0
        return 0.0
    
    def calculate_bertscore(self, predictions: List[str], references: List[str]) -> Dict[str, float]:
        """
        Calculate BERTScore (precision, recall, F1) for a batch of responses.
        """
        scorer = self._get_bertscorer()
        P, R, F1 = scorer.score(predictions, references)
        return {
            "precision": P.mean().item(),
            "recall": R.mean().item(),
            "f1": F1.mean().item()
        }
    
    def calculate_hallucination_rate(self, prediction: str, ground_truth: str) -> float:
        """
        Estimate hallucination rate for TruthfulQA and HaluEval.
        Returns proportion of claims in prediction that are false.
        """
        # Simple heuristic: count contradictory statements
        # In full implementation, use NLI model for verification
        pred_sentences = prediction.split('.')
        truth_sentences = ground_truth.split('.')
        
        hallucinated = 0
        for pred_sent in pred_sentences:
            if len(pred_sent.strip()) < 5:  # Skip empty/short sentences
                continue
            # Check if prediction contradicts ground truth
            if self._contradicts(pred_sent, ground_truth):
                hallucinated += 1
        
        total = max(len(pred_sentences), 1)
        return hallucinated / total
    
    def _contradicts(self, sentence: str, ground_truth: str) -> bool:
        """
        Simple contradiction detection.
        In production, use a proper NLI model (DeBERTa, RoBERTa-large-MNLI)
        """
        # Placeholder logic - will be replaced with NLI
        sentence_lower = sentence.lower()
        truth_lower = ground_truth.lower()
        
        # If sentence claims something opposite to truth
        negation_words = ["not", "never", "no", "incorrect", "false", "wrong"]
        if any(word in sentence_lower for word in negation_words):
            # Check if the claim contradicts known truth
            common_truths = truth_lower.split('.')
            for truth in common_truths:
                if len(truth.strip()) > 10 and truth.strip() in sentence_lower:
                    return True
        return False
    
    def calculate_compliance_score(self, prediction: str, rules: List[str]) -> float:
        """
        Measure how many rules the model followed.
        For redundancy and constraint density experiments.
        """
        followed_rules = 0
        prediction_lower = prediction.lower()
        
        for rule in rules:
            rule_keywords = self._extract_keywords(rule)
            if any(kw in prediction_lower for kw in rule_keywords):
                followed_rules += 1
        
        return followed_rules / len(rules) if rules else 1.0
    
    def _extract_keywords(self, rule: str) -> List[str]:
        """
        Convert rule text to keywords for detection.
        Example: "Cite your sources" → ["cite", "source", "reference"]
        """
        rule_lower = rule.lower()
        keyword_map = {
            "cite": ["cite", "citation", "source", "reference", "according to"],
            "uncertain": ["don't know", "not sure", "uncertain", "cannot confirm"],
            "reasoning": ["step", "first", "second", "then", "because", "therefore"],
            "concise": ["in short", "briefly", "to summarize"]
        }
        
        for key, keywords in keyword_map.items():
            if key in rule_lower or any(kw in rule_lower for kw in keywords):
                return keywords
        return [rule_lower[:10]]  # Fallback: first 10 chars
    
    def evaluate_response(self, 
                          prediction: str, 
                          ground_truth: str, 
                          task_type: str,
                          rules: List[str] = None) -> Dict[str, Any]:
        """
        Main evaluation function combining all metrics.
        """
        results = {
            "accuracy": self.calculate_accuracy(prediction, ground_truth),
            "hallucination_rate": self.calculate_hallucination_rate(prediction, ground_truth),
        }
        
        if rules:
            results["compliance_score"] = self.calculate_compliance_score(prediction, rules)
        
        # Add token efficiency (response length)
        results["response_length"] = len(prediction.split())
        
        return results


# Example usage
if __name__ == "__main__":
    calc = MetricsCalculator()
    
    # Test
    pred = "Paris is the capital of France."
    truth = "Paris"
    rules = ["Answer accurately", "Be concise"]
    
    result = calc.evaluate_response(pred, truth, "mmlu", rules)
    print(json.dumps(result, indent=2))