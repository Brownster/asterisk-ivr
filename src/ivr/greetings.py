import yaml
from datetime import datetime

def load_greetings(config_path='config/greetings.yml'):
    """Load greeting templates from the YAML configuration file."""
    try:
        with open(config_path) as f:
            data = yaml.safe_load(f)
        return data.get('greetings', {})
    except Exception as e:
        # Log error or raise exception as needed
        print(f"Error loading greetings from {config_path}: {e}")
        return {}

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

if __name__ == "__main__":
    # Example usage in your AGI handler:
    caller_id = "..."  # Your logic to determine caller ID
    my_cli = "+15550000000"  # Internal caller
    if caller_id == my_cli:
        greeting = select_greeting('internal')
    else:
        greeting = select_greeting('external')
    print(greeting)
