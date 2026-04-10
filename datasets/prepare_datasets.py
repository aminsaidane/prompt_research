# prepare_datasets.py
import random
import json
from datasets import load_dataset
import os
# Set seed for reproducibility
SEED = 42
random.seed(SEED)
HF_TOKEN = os.getenv("HF_TOKEN")
def save_subset(subset, filename):
    """Helper to save subset as JSON"""
    with open(f"datasets/{filename}", "w") as f:
        json.dump(subset, f, indent=2)
    print(f"{filename} created: {len(subset)} samples")

def prepare_mmlu_subset(n=600):
    """Load MMLU and take balanced subset across subjects"""
    dataset = load_dataset("cais/mmlu", "all", split="test")
    
    # Group by subject
    subjects = {}
    for item in dataset:
        subject = item['subject']
        if subject not in subjects:
            subjects[subject] = []
        subjects[subject].append(item)
    
    # Take roughly equal samples per subject
    samples_per_subject = max(1, n // len(subjects))
    subset = []
    for subject, items in subjects.items():
        subset.extend(random.sample(items, min(samples_per_subject, len(items))))
    
    # Trim to exactly n
    subset = subset[:n]
    
    save_subset(subset, "mmlu_subset.json")

def prepare_gsm8k_subset(n=500):
    """Load GSM8K and take random subset"""
    dataset = load_dataset("openai/gsm8k", "main", split="test")
    subset = random.sample(list(dataset), n)
    save_subset(subset, "gsm8k_subset.json")

def prepare_truthfulqa_subset(n=500):
    """Load TruthfulQA generation validation split and take random subset"""
    dataset = load_dataset("truthful_qa", "generation", split="validation")
    subset = random.sample(list(dataset), n)
    save_subset(subset, "truthfulqa_subset.json")

def prepare_halueval_subset(n=500):
    """Load HaluEval QA split and take random subset"""
    dataset = load_dataset("pminervini/HaluEval", "qa", split="data")
    subset = random.sample(list(dataset), n)
    save_subset(subset, "halueval_subset.json")

if __name__ == "__main__":
    prepare_mmlu_subset()
    prepare_gsm8k_subset()
    prepare_truthfulqa_subset()
    prepare_halueval_subset()