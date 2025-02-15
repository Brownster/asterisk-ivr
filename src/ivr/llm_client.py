import requests
import os
import json

class LLMClient:
    def __init__(self):
        self.api_endpoint = os.getenv("LLM_API_ENDPOINT", "https://api.openai.com/v1/chat/completions")
        self.api_key = os.getenv("LLM_API_KEY")
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    def _build_prompt(self, prompt_data):
        messages = [
            {
                "role": "system",
                "content": (
                    "You are a helpful phone assistant. When responding, please format your answer as a JSON object with the following keys: "
                    '{"intent": "your_intent", "message": "Your response message", "next_state": "optional_next_state", "tool_call": "optional_tool_call"}.'
                )
            }
        ]
        for entry in prompt_data.get("chat_history", []):
            messages.append({"role": entry["role"], "content": entry["content"]})
        messages.append({"role": "user", "content": prompt_data.get("current_input", "")})
        return messages

    def get_response(self, prompt_data):
        prompt = self._build_prompt(prompt_data)
        payload = {
            "model": "gpt-4",  # or another model of your choice
            "messages": prompt,
            "temperature": 0.7
        }
        response = requests.post(self.api_endpoint, headers=self.headers, json=payload)
        response.raise_for_status()
        return response.json()  # you'll then parse this JSON in your handler


if __name__ == "__main__":
    client = LLMClient()
    prompt_data = {
        "chat_history": [
            {"role": "user", "content": "I want to speak to my dad."}
        ],
        "current_input": ""
    }
    resp = client.get_response(prompt_data)
    print(json.dumps(resp, indent=2))
