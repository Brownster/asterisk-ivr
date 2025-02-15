import yaml
from datetime import datetime

def load_greetings(config_path='config/greetings.yml'):
    """Load greeting templates from the YAML configuration file."""
    with open(config_path) as f:
        data = yaml.safe_load(f)
    return data.get('greetings', {})

def select_greeting(caller_type='external'):
    """
    Select the appropriate greeting based on caller type ('internal' or 'external')
    and the current time of day (morning, afternoon, evening).
    """
    greetings = load_greetings()
    now = datetime.now()
    hour = now.hour
    if hour < 12:
        time_of_day = 'morning'
    elif hour < 18:
        time_of_day = 'afternoon'
    else:
        time_of_day = 'evening'
    
    return greetings.get(caller_type, {}).get(time_of_day, "Hello, how can I help you?")

# Example usage in your AGI handler:
caller_id = "..."  # your logic to determine caller ID
my_cli = "+15550000000"  # internal caller

if caller_id == my_cli:
    greeting = select_greeting('internal')
else:
    greeting = select_greeting('external')

# Then use the greeting, e.g. send it to TTS or display it as a prompt:
print(greeting)
