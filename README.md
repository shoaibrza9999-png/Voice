# WhatsApp Voice & Text Finance Tracker

A lightweight SaaS microservice serving as a backend for a WhatsApp AI financial agent. It processes incoming text and voice notes, transcribes them, classifies intents (Add, Edit, Remove, Find, Filter) using Groq API, and stores data in a PostgreSQL or SQLite database.

## Features
- **FastAPI Backend:** Fully asynchronous REST API documented via Swagger.
- **WhatsApp Cloud API Integration:** Handles incoming webhooks, media downloading, and sending text/interactive button responses.
- **Audio Transcription:** Utilizes Groq Whisper API for blazing-fast voice note transcription.
- **LLM Function Calling:** Uses Groq (`llama3-70b-8192` or equivalent) to strictly extract categorized entities and map transactions.
- **Human-in-the-loop:** Confirms data entry with WhatsApp Interactive Buttons.
- **Automated Scheduler:** Sends out daily summaries and weekly categorized reports.

## Prerequisites
- Python 3.11+
- Meta Developer Account (for WhatsApp Business Cloud API Token, Phone ID, Webhook Token)
- Groq API Key

## Setup Variables
Create a `.env` file in the root directory:
```env
# Database Configuration
DATABASE_URL=sqlite:///./finance_tracker.db # or postgresql://user:pass@host/db

# WhatsApp Configuration
WHATSAPP_VERIFY_TOKEN=your_secure_verify_token
WHATSAPP_API_TOKEN=your_permanent_or_temporary_token
WHATSAPP_PHONE_NUMBER_ID=your_phone_number_id

# LLM Configuration
GROQ_API_KEY=your_groq_key
```

## Running Locally

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Start the FastAPI server:
   ```bash
   uvicorn app.main:app --reload
   ```

## Running via Docker
Deploy the entire stack with PostgreSQL:
```bash
docker-compose up --build
```

## Webhook Endpoint
Set your Meta App Webhook URL to: `https://<your-domain>/webhook` with your specific `WHATSAPP_VERIFY_TOKEN`.
Subscribe the webhook to the `messages` event.
