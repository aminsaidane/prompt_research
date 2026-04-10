import requests

class OllamaClient:
    
    def __init__(self, model_name: str):
        self.model = model_name
        self.url = "http://localhost:11434/api/generate"

    def generate(self, prompt: str, max_tokens: int = 512):

        payload = {
            "model": self.model,
            "prompt": prompt,
            "options": {
                "temperature": 0.0,
                "num_predict": max_tokens
            },
            "stream": False
        }

        response = requests.post(self.url, json=payload)

        return response.json()["response"]