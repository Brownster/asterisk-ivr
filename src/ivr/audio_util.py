def record_audio(agi, output_file: str, max_duration: int = 5000) -> str:
    """
    Record audio from the caller using the AGI command.
    Adjust parameters (e.g., silence, timeout) as needed.
    """
    agi.verbose(f"Recording audio to {output_file}...", 3)
    # The parameters below may be adjusted based on your environment.
    agi.record_file(output_file, "wav", max_duration, "#", 3)
    return output_file
