import json
import urllib.request
import urllib.error
from typing import Dict, Any, Optional

class OllamaClient:
    def __init__(self, config_path: str = "config/llm_config.json"):
        with open(config_path, 'r') as f:
            self.config = json.load(f)
            
        self.endpoint = self.config.get("endpoint", "http://localhost:11434/api/generate")
        self.primary_model = self.config.get("primary_model", "qwen3:8b-instruct")
        self.fallback_models = self.config.get("fallback_models", ["mistral:7b-instruct", "llama3.1:8b-instruct"])
        self.options = self.config.get("options", {})
        
    def generate(self, prompt: str, fallback_index: int = -1) -> Optional[Dict[str, Any]]:
        if fallback_index == -1:
            model = self.primary_model
        elif fallback_index < len(self.fallback_models):
            model = self.fallback_models[fallback_index]
        else:
            print("All fallback models exhausted.")
            return None
            
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": self.options.get("temperature", 0.1),
                "top_p": self.options.get("top_p", 0.9),
                "num_predict": self.options.get("max_tokens", 1024)
            },
            "format": "json"
        }
        
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(self.endpoint, data=data, headers={'Content-Type': 'application/json'})
        
        try:
            with urllib.request.urlopen(req) as response:
                result = json.loads(response.read().decode('utf-8'))
                response_text = result.get("response", "{}")
                return json.loads(response_text)
        except urllib.error.URLError as e:
            print(f"Ollama API Error with model {model}: {e}")
            next_fallback = fallback_index + 1
            print(f"Attempting next fallback model...")
            return self.generate(prompt, fallback_index=next_fallback)
        except json.JSONDecodeError as e:
            print(f"JSON Decode Error from LLM response ({model}): {e}")
            return None
