import yaml

def load_intents(caller_type):
    """
    Load intents from the corresponding YAML file based on caller type.
    """
    config_file = f"config/{caller_type}_caller_intents.yml"
    try:
        with open(config_file) as f:
            data = yaml.safe_load(f)
        return data.get("intents", {})
    except Exception as e:
        print(f"Error loading intents from {config_file}: {e}")
        return {}
        
if __name__ == "__main__":
    # Example usage:
    intents = load_intents("known")
    print(intents)
