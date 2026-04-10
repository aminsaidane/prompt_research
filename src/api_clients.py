import os
import time
from dotenv import load_dotenv

from openai import OpenAI
from anthropic import Anthropic


load_dotenv()


class APIModelClient:
    """
    Unified client for API-based models (OpenAI + Anthropic)
    """

    def __init__(self, model_type: str):

        self.model_type = model_type
        self.max_retries = int(os.getenv("OPENAI_MAX_RETRIES", 3))
        self.sleep_time = float(os.getenv("API_SLEEP_BETWEEN_CALLS", 0.5))

        if model_type == "gpt4o":
            self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            self.model_name = "gpt-4o-2024-05-13"

        elif model_type == "claude3":
            self.client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
            self.model_name = "claude-3-sonnet-20240229"

        else:
            raise ValueError(f"Unsupported API model: {model_type}")


    def generate(self, prompt: str, max_tokens: int = 512) -> str:
        """
        Generate response from the selected API model
        """

        for attempt in range(self.max_retries):

            try:

                if self.model_type == "gpt4o":

                    response = self.client.chat.completions.create(
                        model=self.model_name,
                        messages=[{"role": "user", "content": prompt}],
                        temperature=0.0,
                        max_tokens=max_tokens
                    )

                    return response.choices[0].message.content.strip()


                elif self.model_type == "claude3":

                    response = self.client.messages.create(
                        model=self.model_name,
                        max_tokens=max_tokens,
                        temperature=0.0,
                        messages=[{"role": "user", "content": prompt}]
                    )

                    return response.content[0].text.strip()


            except Exception as e:

                print(f"[API ERROR] {self.model_type} attempt {attempt+1}: {e}")

                if attempt < self.max_retries - 1:
                    time.sleep(self.sleep_time)
                else:
                    return "ERROR"

        return "ERROR"