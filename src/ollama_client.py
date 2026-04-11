import requests
import yaml


# =========================
# LOAD CONFIG
# =========================

with open("config.yaml", "r") as f:
    CONFIG = yaml.safe_load(f)


class OllamaClient:
    """
    Client for local Ollama models (Llama, Mistral, Qwen, etc.)
    """

    def __init__(self, model_name: str):

        self.model = model_name
        self.url = "http://localhost:11434/api/generate"

        # from config.yaml
        self.temperature = CONFIG["experiment"]["temperature"]
        self.max_tokens = CONFIG["experiment"]["max_tokens"]


    def generate(self, prompt: str) -> str:

        payload = {
            "model": self.model,
            "prompt": prompt,
            "options": {
                "temperature": self.temperature,
                "num_predict": self.max_tokens
            },
            "stream": False
        }

        try:
            response = requests.post(
                self.url,
                json=payload,
                timeout=120  # important for long generations
            )

            response.raise_for_status()

            return response.json().get("response", "").strip()


        except requests.exceptions.RequestException as e:
            print(f"[OLLAMA ERROR] {self.model}: {e}")
            return "ERROR"

        except Exception as e:
            print(f"[OLLAMA UNKNOWN ERROR] {self.model}: {e}")
            return "ERROR"