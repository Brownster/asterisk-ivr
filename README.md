Dynamic IVR with LLM Integration

Welcome to Dynamic IVR with LLM Integration – a cutting-edge project that marries traditional telephony with modern AI! This repository contains an Interactive Voice Response (IVR) system powered by Asterisk, complete with dynamic call flow state management, natural language understanding through an LLM, and robust monitoring and session management.

Imagine a phone system that greets your callers by name, understands their needs, and intelligently routes calls – all while keeping you in the loop with real-time metrics.
🚀 Features

    IVR Engine:
        Seamlessly integrates with FreePBX/Asterisk using AGI.
        Supports both DTMF (keypad) and speech input.

    Dynamic Call Flow State Management:
        Robust state machine with validated transitions.
        Customizable call flows defined via YAML configuration.

    LLM Integration:
        Leverages OpenAI's API to power conversational interactions.
        Structured LLM responses drive state transitions and tool calls.

    Session & Security Enhancements:
        Redis-backed session management with encryption.
        Input validation and ML-powered anomaly detection.

    Rate Limiting & Circuit Breaker:
        Protects against abuse with Redis-based sliding window rate limiting.
        Circuit breaker pattern ensures resilience against external API failures.

    Monitoring & Metrics:
        Prometheus metrics exposed via an HTTP server.
        Detailed JSON-formatted logging with real-time performance insights.

    Modular STT/TTS Integration:
        Start with Microsoft Azure for both Speech-to-Text and Text-to-Speech.
        Easily swap out providers as your needs evolve.

    Intelligent Call Routing:
        Distinguish between allowed callers, unknown callers, and internal calls.
        Multi-turn conversation flows to clarify caller intent.
        Automatically handle intents such as "speak to Dad", "speak to Browny", "sales call", and "scam call".

🎉 Getting Started
Prerequisites

    Python: 3.8+
    MySQL/MariaDB: (for FreePBX and IVR database)
    Asterisk/FreePBX: (for telephony integration)
    Redis: (for session and rate limiting)
    Azure Speech Resource: (for STT/TTS integration)
    Environment Variables:
        LLM_API_KEY – Your OpenAI API key
        SESSION_KEY – A secret key for session encryption (use Fernet.generate_key() to create one)
        SPEECH_KEY – Your Azure Speech resource key
        SPEECH_REGION – Your Azure Speech resource region
        Optionally, DB SSL variables (DB_SSL_CA, DB_SSL_CERT, DB_SSL_KEY) if needed

Installation

    Clone the Repo:

git clone https://github.com/brownster/asterisk-ivr.git
cd asterisk-ivr

Install Dependencies:

pip install -r requirements.txt

Configure Your Environment:

Create a .env file (or export variables in your shell) with your secrets:

    export LLM_API_KEY="your-openai-api-key"
    export SESSION_KEY="your-generated-fernet-key"
    export SPEECH_KEY="your-azure-speech-key"
    export SPEECH_REGION="your-azure-speech-region"
    export DB_SSL_CA="/path/to/ca.pem"
    export DB_SSL_CERT="/path/to/client-cert.pem"
    export DB_SSL_KEY="/path/to/client-key.pem"
    export LOG_LEVEL="INFO"

    Set Up the Database:
        Create the freepbx_llm database in MySQL.
        Ensure your config/db_config.yml matches your database settings.
        Run Alembic migrations automatically during startup.

    Configure Asterisk:
        Set up your AGI configuration in FreePBX to point to src/ivr/agi_handler.py.
        Ensure your Asterisk environment populates the TRANSCRIBED_TEXT variable for speech-to-text functionality.

🛠 Usage

Start the IVR handler (for testing purposes, you might run it from the command line):

python -m src.ivr.agi_handler

This will spin up the Prometheus HTTP server on port 9100 for metrics, and the AGI handler will be ready to process calls.

![Screenshot_20250215_222213](https://github.com/user-attachments/assets/4c757166-a19e-49e5-891e-2c6bfbca2810)



🤝 Contributing

We welcome contributions from the community! Whether it's fixing bugs, improving documentation, or adding exciting new features, feel free to submit a pull request.

    Fork the repository.
    Create a new branch: git checkout -b feature/your-feature-name
    Commit your changes: git commit -am 'Add new feature'
    Push the branch: git push origin feature/your-feature-name
    Open a pull request.

📝 License

This project is licensed under the MIT License – see the LICENSE file for details.
🌟 Acknowledgments

    Inspired by modern conversational IVR systems.
    Powered by the brilliant teams behind Asterisk, OpenAI, Azure, and Prometheus.
