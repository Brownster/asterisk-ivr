Dynamic IVR with LLM Integration

Welcome to Dynamic IVR with LLM Integration – a fun project that marries traditional telephony with modern AI! This repository contains a Interactive Voice Response (IVR) system powered by Asterisk, complete with dynamic call flow state management, natural language understanding through an LLM, and robust monitoring and session management.

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
        Structured LLM responses drive state transitions.

    Session & Security Enhancements:
        Redis-backed session management with encryption.
        Input validation and ML-powered anomaly detection.

    Rate Limiting & Circuit Breaker:
        Protects against abuse with Redis-based sliding window rate limiting.
        Circuit breaker pattern ensures resilience against external API failures.

    Monitoring & Metrics:
        Prometheus metrics exposed via an HTTP server.
        Detailed logging using JSON format with real-time performance insights.

🎉 Getting Started
Prerequisites

    Python 3.8+
    MySQL/MariaDB (for FreePBX and IVR database)
    Asterisk/FreePBX (for telephony integration)
    Redis (for session and rate limiting)
    Environment Variables:
        LLM_API_KEY – Your OpenAI API key
        SESSION_KEY – A secret key for session encryption (use Fernet.generate_key() to create one)
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
    export DB_SSL_CA="/path/to/ca.pem"
    export DB_SSL_CERT="/path/to/client-cert.pem"
    export DB_SSL_KEY="/path/to/client-key.pem"
    export LOG_LEVEL="INFO"

    Set Up the Database:
        Create the freepbx_llm database in MySQL.
        Ensure your config/db_config.yml matches your database settings.
        Run Alembic migrations automatically during startup!

    Configure Asterisk:
        Set up your AGI configuration in FreePBX to point to src/ivr/agi_handler.py.
        Ensure that your Asterisk environment populates the TRANSCRIBED_TEXT variable for speech-to-text functionality.

🛠 Usage

Start the IVR handler (for testing purposes, you might run it from the command line):

python -m src.ivr.agi_handler

This will spin up the Prometheus HTTP server on port 9100 for metrics, and the AGI handler will be ready to process calls.
![Screenshot_20250215_200945](https://github.com/user-attachments/assets/fdca8a47-9b2a-49aa-a19e-039e31774a27)



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
    Powered by the brilliant teams behind Asterisk, OpenAI, and Prometheus.
    Special thanks to our contributors and the open-source community for their ongoing support.

Get ready to revolutionize your call flows with AI!
Happy Coding! 🚀
