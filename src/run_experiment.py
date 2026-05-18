import json
import yaml
import os
from tqdm import tqdm

from api_clients import APIModelClient
from ollama_client import OllamaClient


# =========================
# LOAD CONFIG
# =========================

with open("config.yaml", "r") as f:
    CONFIG = yaml.safe_load(f)


# =========================
# PATHS
# =========================

OUTPUT_FILE = os.path.join(CONFIG["outputs"]["raw_responses"], "results.json")


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

    if dataset_name == "mmlu":
        return item["question"], str(item["answer"])

    elif dataset_name == "gsm8k":
        return item["question"], item["answer"]

    elif dataset_name == "truthfulqa":
        return item["question"], item["best_answer"]

    elif dataset_name == "halueval":
        return item["question"], item["right_answer"]

    else:
        raise ValueError(f"Unknown dataset: {dataset_name}")


# =========================
# UNIQUE KEY (for resume)
# =========================

def make_key(entry):
    return (
        entry["dataset"],
        entry["model"],
        entry["prompt_type"],
        entry["prompt_id"],
        entry["question"]
    )


# =========================
# LOAD EXISTING RESULTS
# =========================

def load_existing_results():
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
            results = json.load(f)
        print(f"Loaded {len(results)} existing results (resume mode)")
        return results
    return []


# =========================
# SAVE RESULTS (incremental)
# =========================

def save_results(results):
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)


# =========================
# MAIN EXPERIMENT
# =========================

def run_experiment():

    os.makedirs(CONFIG["outputs"]["raw_responses"], exist_ok=True)

    results = load_existing_results()
    completed = set(make_key(r) for r in results)

    datasets_cfg = CONFIG["datasets"]
    models_cfg = CONFIG["models"]
    prompts_cfg = CONFIG["prompts"]


    # =========================
    # LOOP DATASETS
    # =========================
    for dataset_name, dataset_info in datasets_cfg.items():

        print(f"\n================ DATASET: {dataset_name} ================")

        dataset = load_json(dataset_info["file"])
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

                        entry = {
                            "dataset": dataset_name,
                            "model": model_cfg["name"],
                            "prompt_type": prompt_type,
                            "prompt_id": prompt_id,
                            "question": question
                        }

                        # 🔥 SKIP if already done
                        if make_key(entry) in completed:
                            continue

                        final_prompt = build_prompt(template, question)

                        response = client.generate(final_prompt)

                        result = {
                            **entry,
                            "gold_answer": gold_answer,
                            "response": response
                        }

                        results.append(result)
                        completed.add(make_key(entry))

                        # 🔥 SAVE AFTER EACH GENERATION
                        save_results(results)


    print(f"\nDONE ✅ Results saved to: {OUTPUT_FILE}")


# =========================
# ENTRY POINT
# =========================

if __name__ == "__main__":
    run_experiment()