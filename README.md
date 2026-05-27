# SAP CPI Assistant

AI-powered web application for SAP Cloud Platform Integration developers.

## Features

| Tool | What it does |
|------|-------------|
| **iFlow Generator** | Generate complete iFlow XML with adapters, routing, error handling |
| **Message Mapping** | Auto-map source ↔ target schemas → Groovy or XSLT output |
| **Groovy Scripts** | Generate, explain, and debug Groovy scripts for CPI |
| **XSLT Generator** | Generate XSLT 2.0 from description or sample XML pairs |
| **AI Assistant** | Ask anything about CPI + code review |

## Prerequisites

- **Python 3.14+** — for the backend
- **Node.js 18+** — for the frontend → download from https://nodejs.org/
- **Anthropic API Key** — get one at https://console.anthropic.com/

## Setup

### 1. Configure API Key

```bash
cd backend
copy .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY
```

### 2. Start the Backend

Double-click `start-backend.bat` **or** run:
```bash
cd backend
python -m pip install -r requirements.txt
python -m uvicorn main:app --reload --port 8000
```

### 3. Start the Frontend

Double-click `start-frontend.bat` **or** run:
```bash
cd frontend
npm install
npm run dev
```

### 4. Open the App

Navigate to **http://localhost:5173** in your browser.

## Project Structure

```
sap-cpi-assistant/
├── backend/
│   ├── main.py                  # FastAPI app entry point
│   ├── services/
│   │   └── claude_service.py    # Claude API integration
│   └── routers/
│       ├── iflow.py             # iFlow generation endpoints
│       ├── mapping.py           # Message mapping endpoints
│       ├── groovy.py            # Groovy script endpoints
│       ├── xslt.py              # XSLT generation endpoints
│       └── chat.py              # AI assistant endpoints
└── frontend/
    └── src/
        ├── pages/               # One page per feature
        ├── components/          # Shared UI components
        └── api/client.ts        # API calls
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/iflow/generate` | Generate iFlow XML |
| POST | `/api/iflow/explain` | Explain existing iFlow |
| POST | `/api/mapping/generate` | Generate message mapping |
| POST | `/api/mapping/automap` | Auto-map fields |
| POST | `/api/groovy/generate` | Generate Groovy script |
| POST | `/api/groovy/explain` | Explain Groovy script |
| POST | `/api/groovy/debug` | Debug failing script |
| POST | `/api/xslt/generate` | Generate XSLT |
| POST | `/api/xslt/from-samples` | XSLT from XML samples |
| POST | `/api/xslt/explain` | Explain XSLT |
| POST | `/api/chat/ask` | Ask AI assistant |
| POST | `/api/chat/review` | Code review |
