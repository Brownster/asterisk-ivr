import requests
import yaml
import os
from ratelimit import limits, sleep_and_retry
from redis import Redis
from utils.logger import logger, track_metrics, record_metric

# Define a custom exception for rate limiting
class TooManyRequests(Exception):
    pass

class LLMClient:
    def __init__(self):
        with open('config/llm_config.yml') as f:
            self.config = yaml.safe_load(f)
        
        # Override API key with environment variable if set
        self.config['api_key'] = os.getenv("LLM_API_KEY", self.config.get('api_key'))
        
        self.headers = {
            "Authorization": f"Bearer {self.config['api_key']}",
            "Content-Type": "application/json"
        }
        self.redis = Redis(host='localhost', port=6379, db=0)

    @sleep_and_retry
    @limits(calls=90, period=60)  # Global limit: 90 calls per minute (with buffer)
    @track_metrics
    def get_response(self, prompt):
        # Cluster-aware rate limiting per caller
        caller_key = f"rate_limit:{prompt['caller_id']}"
        current_count = self.redis.incr(caller_key)
        if current_count == 1:
            self.redis.expire(caller_key, 60)
        if current_count > 5:  # 5 calls per minute per caller
            logger.error(f"Rate limit exceeded for caller {prompt['caller_id']}")
            raise TooManyRequests("Caller rate limit exceeded")
        
        try:
            response = requests.post(
                self.config['api_endpoint'],
                headers=self.headers,
                json={
                    "messages": self._format_messages(prompt),
                    "temperature": self.config.get('temperature', 0.7)
                }
            )
            response.raise_for_status()
            return self._parse_response(response.json())
        except requests.exceptions.RequestException as e:
            logger.error(f"LLM API request failed: {e}")
            return {"text": "I'm having trouble connecting. Please try again later."}

    def _format_messages(self, prompt):
        messages = [{"role": "system", "content": "You are a helpful phone assistant."}]
        for entry in prompt['chat_history']:
            messages.append({"role": entry['role'], "content": entry['message']})
        messages.append({"role": "user", "content": prompt['current_input']})
        return messages

    def _parse_response(self, response):
        try:
            return {
                "text": response['choices'][0]['message']['content'],
                "response_type": "llm_response"
            }
        except (KeyError, IndexError) as e:
            logger.error(f"Error parsing LLM response: {e} - Full response: {response}")
            return {"text": "I'm sorry, I could not understand the response."}
