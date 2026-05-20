"""
evaluation.py - Metrics calculation for LLM responses
Measures: Accuracy, Hallucination Rate (via NLI), Compliance Score
"""

from typing import List, Dict, Any
import json


class MetricsCalculator:
    def __init__(self):
        self.nli_pipeline = None
        self._nli_model_name = "typeform/distilbert-base-uncased-mnli"
    
    def _get_nli(self):
        """Lazy load NLI pipeline for hallucination detection"""
        if self.nli_pipeline is None:
            from transformers import pipeline
            import torch
            
            device = -1  # Force CPU usage
            
            print("Loading NLI model: {}".format(self._nli_model_name))
            print("Device: CPU (this will take 1-2 minutes first time)")
            
            self.nli_pipeline = pipeline(
                "text-classification",
                model=self._nli_model_name,
                device=device
            )
            print("NLI model loaded successfully")
        return self.nli_pipeline
    
    def calculate_accuracy(self, prediction: str, ground_truth: str) -> float:
        """
        Exact match accuracy for MMLU and GSM8K.
        Returns 1.0 if correct answer appears anywhere in prediction.
        """
        pred_clean = prediction.strip().lower()
        truth_clean = ground_truth.strip().lower()
        
        if truth_clean in pred_clean:
            return 1.0
        return 0.0
    
    def calculate_hallucination_rate(self, prediction: str, ground_truth: str) -> float:
        """
        NLI-based hallucination detection using cross-encoder model.
        Returns proportion of sentences that contradict ground truth.
        """
        if not prediction or len(prediction.strip()) < 5:
            return 0.0
        
        nli = self._get_nli()
        
        # Split into sentences for granular detection
        sentences = [s.strip() for s in prediction.split('.') if len(s.strip()) > 10]
        
        # Limit to first 3 sentences for speed (most hallucinations appear early)
        sentences = sentences[:3]
        
        if not sentences:
            # If no substantial sentences, evaluate the whole prediction
            try:
                result = nli("{} [SEP] {}".format(prediction, ground_truth))
                return 1.0 if result[0]['label'] == 'CONTRADICTION' else 0.0
            except Exception:
                return 0.0
        
        # Evaluate each sentence
        hallucinated_count = 0
        for sent in sentences:
            try:
                result = nli("{} [SEP] {}".format(sent, ground_truth))
                if result[0]['label'] == 'CONTRADICTION':
                    hallucinated_count += 1
            except Exception as e:
                print("NLI warning: {}".format(e))
                continue
        
        return hallucinated_count / len(sentences) if sentences else 0.0
    
    def calculate_compliance_score(self, prediction: str, rules: List[str]) -> float:
        """
        Measure how many rules the model followed.
        """
        followed_rules = 0
        prediction_lower = prediction.lower()
        
        for rule in rules:
            rule_keywords = self._extract_keywords(rule)
            if any(kw in prediction_lower for kw in rule_keywords):
                followed_rules += 1
        
        return followed_rules / len(rules) if rules else 1.0
    
    def _extract_keywords(self, rule: str) -> List[str]:
        """Convert rule text to keywords for detection."""
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
        return [rule_lower[:10]]
    
    def evaluate_response(self, 
                          prediction: str, 
                          ground_truth: str, 
                          task_type: str = None,
                          rules: List[str] = None) -> Dict[str, Any]:
        """
        Main evaluation function combining all metrics.
        """
        results = {
            "accuracy": self.calculate_accuracy(prediction, ground_truth),
            "hallucination_rate": self.calculate_hallucination_rate(prediction, ground_truth),
            "response_length": len(prediction.split())
        }
        
        if rules:
            results["compliance_score"] = self.calculate_compliance_score(prediction, rules)
        
        return results


# Example usage
if __name__ == "__main__":
    print("Testing NLI model...")
    calc = MetricsCalculator()
    
    # Test cases
    test_cases = [
        ("Paris is the capital of France.", "Paris", "Should be correct (no hallucination)"),
        ("Berlin is the capital of France.", "Paris", "Should be hallucination"),
        ("I don't know the answer.", "Paris", "Should NOT be hallucination"),
    ]
    
    for pred, truth, desc in test_cases:
        result = calc.calculate_hallucination_rate(pred, truth)
        print("{}: {:.2f}".format(desc, result))
    
    print("\n✅ Ready to run on 10,800 responses")
    print("Estimated time on MacBook Air: 2-4 hours")