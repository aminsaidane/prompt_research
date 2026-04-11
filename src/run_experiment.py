import json
import yaml
import os
from tqdm import tqdm

from src.api_clients import APIModelClient
from src.ollama_client import OllamaClient


# =========================
# LOAD CONFIG
# =========================

with open("config.yaml", "r") as f:
    CONFIG = yaml.safe_load(f)


# =========================
# LOAD FILE HELPERS
# =========================

def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# =========================
# MODEL FACTORY
# =========================

def get_client(model_cfg):

    if model_cfg["type"] == "api":
        return APIModelClient(model_cfg["name"])

    elif model_cfg["type"] == "local":
        return OllamaClient(model_cfg["name"])

    else:
        raise ValueError(f"Unknown model type: {model_cfg['type']}")


# =========================
# PROMPT BUILDER
# =========================

def build_prompt(template, question):
    return template.replace("{question}", question)


# =========================
# DATASET NORMALIZATION
# =========================

def extract_fields(dataset_name, item):

    """
    Converts all datasets into a unified format:
    returns:
        question, answer (or best equivalent)
    """

    # ================= MMLU =================
    if dataset_name == "mmlu":
        return item["question"], item["answer"]

    # ================= GSM8K =================
    elif dataset_name == "gsm8k":
        return item["question"], item["answer"]

    # ================= TruthfulQA =================
    elif dataset_name == "truthfulqa":
        return item["question"], item["best_answer"]

    # ================= HaluEval =================
    elif dataset_name == "halueval":
        return item["question"], item["right_answer"]

    else:
        raise ValueError(f"Unknown dataset: {dataset_name}")


# =========================
# MAIN EXPERIMENT
# =========================

def run_experiment():

    os.makedirs("outputs/raw_responses", exist_ok=True)

    results = []

    datasets_cfg = CONFIG["datasets"]
    models_cfg = CONFIG["models"]
    prompts_cfg = CONFIG["prompts"]


    # =========================
    # LOOP DATASETS
    # =========================
    for dataset_name, dataset_info in datasets_cfg.items():

        print(f"\n================ DATASET: {dataset_name} ================")

        dataset = load_json(dataset_info["file"])


        # LIMIT SAMPLES (IMPORTANT)
        dataset = dataset[:dataset_info["samples"]]


        # =========================
        # LOOP MODELS
        # =========================
        for model_cfg in models_cfg:

            if not model_cfg["enabled"]:
                continue

            print(f"\n--- MODEL: {model_cfg['name']} ---")

            client = get_client(model_cfg)


            # =========================
            # LOOP PROMPT TYPES
            # =========================
            for prompt_type, prompt_info in prompts_cfg.items():

                prompt_templates = load_json(prompt_info["file"])
                allowed_variants = prompt_info["variants"]

                # filter only selected variants (L1, R1, C1...)
                prompt_templates = [
                    p for p in prompt_templates
                    if p["id"] in allowed_variants
                ]


                print(f"\n>>> PROMPT TYPE: {prompt_type}")


                # =========================
                # LOOP PROMPT VARIANTS
                # =========================
                for prompt in prompt_templates:

                    prompt_id = prompt["id"]
                    template = prompt["template"]

                    print(f"Prompt: {prompt_id}")


                    # =========================
                    # LOOP DATASET ITEMS
                    # =========================
                    for item in tqdm(dataset):

                        question, gold_answer = extract_fields(dataset_name, item)

                        final_prompt = build_prompt(template, question)

                        response = client.generate(final_prompt)


                        results.append({
                            "dataset": dataset_name,
                            "model": model_cfg["name"],
                            "prompt_type": prompt_type,
                            "prompt_id": prompt_id,
                            "question": question,
                            "gold_answer": gold_answer,
                            "response": response
                        })


    # =========================
    # SAVE RESULTS
    # =========================

    output_path = "outputs/raw_responses/results.json"

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)


    print(f"\nDONE ✅ Results saved to: {output_path}")


# =========================
# ENTRY POINT
# =========================

if __name__ == "__main__":
    run_experiment()