import os
import time
import yaml
from dotenv import load_dotenv

from openai import OpenAI
from anthropic import Anthropic


# =========================
# LOAD ENV + CONFIG
# =========================

load_dotenv()

with open("config.yaml", "r") as f:
    CONFIG = yaml.safe_load(f)


# =========================
# API CLIENT
# =========================

class APIModelClient:
    """
    Unified client for API-based models (OpenAI + Anthropic)
    """

    def __init__(self, model_type: str):

        self.model_type = model_type

        # from config.yaml
        self.max_retries = int(os.getenv("MAX_RETRIES", 3))
        self.sleep_time = float(os.getenv("API_SLEEP_BETWEEN_CALLS", 0.5))

        # model config
        self.temperature = CONFIG["experiment"]["temperature"]
        self.max_tokens = CONFIG["experiment"]["max_tokens"]

        # =========================
        # MODEL INITIALIZATION
        # =========================

        if model_type == "gpt4o":
            self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            self.model_name = "gpt-4o-2024-05-13"

        elif model_type == "claude3":
            self.client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
            self.model_name = "claude-3-sonnet-20240229"

        else:
            raise ValueError(f"Unsupported API model: {model_type}")


    # =========================
    # GENERATION FUNCTION
    # =========================

    def generate(self, prompt: str) -> str:

        for attempt in range(self.max_retries):

            try:

                # =========================
                # GPT-4o (OpenAI)
                # =========================
                if self.model_type == "gpt4o":

                    response = self.client.chat.completions.create(
                        model=self.model_name,
                        messages=[{"role": "user", "content": prompt}],
                        temperature=self.temperature,
                        max_tokens=self.max_tokens
                    )

                    return response.choices[0].message.content.strip()


                # =========================
                # Claude 3 (Anthropic)
                # =========================
                elif self.model_type == "claude3":

                    response = self.client.messages.create(
                        model=self.model_name,
                        max_tokens=self.max_tokens,
                        temperature=self.temperature,
                        messages=[{"role": "user", "content": prompt}]
                    )

                    return response.content[0].text.strip()


            # =========================
            # ERROR HANDLING
            # =========================
            except Exception as e:

                print(f"[API ERROR] {self.model_type} attempt {attempt + 1}: {e}")

                if attempt < self.max_retries - 1:
                    time.sleep(self.sleep_time)
                else:
                    return "ERROR"

        return "ERROR"