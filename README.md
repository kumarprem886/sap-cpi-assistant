# SAP CPI Assistant

An AI-powered assistant for SAP Cloud Platform Integration (CPI) development. Generates iFlow configurations, message mappings (.mmap), Groovy scripts, XSLT transformations, and documentation — all from a browser-based UI backed by a Python/FastAPI server. Also connects live to your SAP Integration Suite tenant for package management, deployment, and message monitoring.

**Live demo (UI only):** https://kumarprem886.github.io/sap-cpi-assistant/

---

## Features

| Feature | Description |
|---|---|
| **iFlow Generator** | Generate SAP CPI iFlow XML bundles from a natural-language description |
| **Message Mapping** | Upload XSDs + a mapping sheet to auto-generate a `.mmap` file importable into CPI |
| **Groovy Generator** | AI-assisted Groovy script generation for CPI message handlers |
| **XSLT Generator** | Generate XSLT transformation stylesheets |
| **Chat Assistant** | Conversational AI helper for SAP CPI questions |
| **Document Generator** | Generate integration design documents |
| **CPI Connect** | Live connection to your SAP Integration Suite tenant — browse packages, deploy iFlows, monitor messages, view security artifacts |

---

## Tech Stack

**Frontend**
- React 18 + TypeScript
- Vite 5
- Tailwind CSS
- React Router v6

**Backend**
- Python 3.10+
- FastAPI + Uvicorn
- Groq API (LLM)
- httpx (CPI API calls)
- openpyxl (Excel parsing)
- lxml (XSD/XML processing)
- python-docx (Word document generation)

**MCP Integration (Claude Code)**
- `mcp-integration-suite` — MCP server that gives Claude Code direct access to the CPI OData API

---

## Prerequisites

| Tool | Version | Notes |
|---|---|---|
| Python | 3.10+ | [python.org](https://www.python.org/downloads/) |
| Node.js | 20+ | [nodejs.org](https://nodejs.org/) |
| Groq API Key | — | Free at [console.groq.com](https://console.groq.com/) |
| SAP BTP Account | — | Trial at [account.hanatrial.ondemand.com](https://account.hanatrial.ondemand.com) |

---

## Quick Start

Double-click **`start.bat`** in the project root — it opens both servers and launches the browser automatically.

Or start manually:

### Terminal 1 — Backend (FastAPI)

```bash
cd backend
pip install -r requirements.txt      # first time only
py -m uvicorn main:app --reload --port 8000
```

Backend: **http://localhost:8000** | API docs: **http://localhost:8000/docs**

### Terminal 2 — Frontend (React/Vite)

```bash
cd frontend
npm install        # first time only
npm run dev
```

Frontend: **http://localhost:5173**

> On Windows use `py` instead of `python` if `python` is not in PATH.

---

## Environment Variables

Create `backend/.env`:

```env
# ── AI (required for generation features) ─────────────────────────────────────
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=llama-3.3-70b-versatile

# ── SAP CPI Live Tenant (required for CPI Connect feature) ────────────────────
CPI_AUTH_TYPE=oauth
CPI_API_BASE_URL=https://<tenant>.it-cpi018.cfapps.<region>.hana.ondemand.com/api/v1
CPI_BASE_URL=https://<tenant>.it-cpi018-rt.cfapps.<region>.hana.ondemand.com

# OAuth2 (recommended):
CPI_CLIENT_ID=sb-xxxxxxxx...
CPI_CLIENT_SECRET=xxxxxxxx...
CPI_TOKEN_URL=https://<subaccount>.authentication.<region>.hana.ondemand.com/oauth/token

# Basic auth (alternative — use S-User credentials):
# CPI_AUTH_TYPE=basic
# CPI_USER=S0012345
# CPI_PASS=yourpassword
```

---

## CPI Connect

The **CPI Connect** page gives you a live view of your SAP Integration Suite tenant directly from the app.

### What it shows

| Tab | Content |
|---|---|
| **Packages & iFlows** | All integration packages, expandable to show iFlows with a Deploy button |
| **Message Monitor** | Last 50 message processing logs, filterable by status (COMPLETED / FAILED / PROCESSING / RETRY / CANCELLED) |
| **Security** | User Credentials and Keystore Entries (read-only metadata) |

### Authentication — how it works

The app uses **OAuth2 Client Credentials Grant**:

```
1. POST <tokenurl>
   Body:  grant_type=client_credentials
   Auth:  Basic(<clientid>, <clientsecret>)
   →  Returns: { access_token: "eyJ...", expires_in: 3600 }

2. Every CPI API call:
   GET/POST <api_base_url>/IntegrationPackages
   Header: Authorization: Bearer eyJ...
```

The token is **cached for 1 hour** in memory — the backend only fetches a new token when the current one is within 30 seconds of expiry.

### Getting credentials from BTP

1. Go to **BTP Cockpit → your subaccount → Instances & Subscriptions**
2. Find your **process_integration** service instance (or create one with plan `api`)
3. Create a **Service Key** — download the JSON, it contains:
   - `clientid` → `CPI_CLIENT_ID`
   - `clientsecret` → `CPI_CLIENT_SECRET`
   - `tokenurl` → `CPI_TOKEN_URL`
   - `url` → base for `CPI_API_BASE_URL` (append `/api/v1`)

### Required API instance roles

When creating the service instance, set these roles in the parameters JSON:

```json
{
  "roles": [
    "WorkspacePackagesMetaData.Read",
    "WorkspacePackagesMetaData.Write",
    "WorkspacePackagesTransport.Read",
    "WorkspacePackagesTransport.Write",
    "IntegrationFlowConfigurationsMetaData.Read",
    "IntegrationFlowConfigurationsMetaData.Write",
    "IntegrationFlowConfigurationsTransport.Read",
    "IntegrationFlowConfigurationsTransport.Write",
    "MessageProcessingLogs.Read",
    "MessagePayload.Read",
    "MonitoringDataRead",
    "UserCredentials.Read",
    "KeystoreEntries.Read"
  ]
}
```

> **Trial shortcut:** Assign the `PI_Integration_Developer` role collection to your service instance — it covers all of the above.

---

## MCP Server (Claude Code Integration)

The project includes an MCP (Model Context Protocol) server that gives **Claude Code** direct access to your CPI tenant. This means you can manage CPI by talking to Claude Code — no clicking through the BTP UI.

### What is MCP?

MCP is Anthropic's open standard for connecting AI assistants to external tools. With the CPI MCP server connected, Claude Code can:

| You say | Claude does |
|---|---|
| "List my integration packages" | Calls CPI API, returns the list |
| "Deploy iFlow X from package Y" | Triggers deployment to runtime |
| "Show me failed messages from today" | Pulls message monitoring logs |
| "Create an empty package called Test" | Creates it on your tenant |
| "Get the iFlow XML for X" | Downloads and shows the content |
| "Update iFlow X with this configuration" | Uploads modified iFlow content |

### Setup

The MCP server (`mcp-integration-suite`) is located at `C:\Users\<you>\mcp-integration-suite\`.

**1. Fill in credentials** — edit `mcp-integration-suite/.env`:

```env
# OAuth2 credentials from your BTP service key
API_OAUTH_CLIENT_ID=sb-xxxxxxxx...
API_OAUTH_CLIENT_SECRET=xxxxxxxx...
API_OAUTH_TOKEN_URL=https://<subaccount>.authentication.<region>.hana.ondemand.com/oauth/token

# CPI API base URL
API_BASE_URL=https://<tenant>.it-cpitrial05.cfapps.<region>.hana.ondemand.com/api/v1

# Runtime URL (for sending test messages)
CPI_BASE_URL=https://<tenant>.it-cpitrial05-rt.cfapps.<region>.hana.ondemand.com
CPI_OAUTH_CLIENT_ID=sb-xxxxxxxx...
CPI_OAUTH_CLIENT_SECRET=xxxxxxxx...
CPI_OAUTH_TOKEN_URL=https://<subaccount>.authentication.<region>.hana.ondemand.com/oauth/token
```

**2. Claude Code config** — the MCP server is already configured in `~/.claude/mcp.json`:

```json
{
  "mcpServers": {
    "mcp-integration-suite": {
      "command": "C:\\nodejs\\node.exe",
      "args": ["C:\\Users\\<you>\\mcp-integration-suite\\dist\\index.js"],
      "env": {
        "DOTENV_CONFIG_PATH": "C:\\Users\\<you>\\mcp-integration-suite\\.env"
      }
    }
  }
}
```

**3. Restart Claude Code** — MCP servers load at startup. After restarting, Claude Code has direct CPI access.

### MCP vs Web App — what's the difference?

| | Web App (CPI Connect page) | MCP (Claude Code) |
|---|---|---|
| Who uses it | Any user of the web app | Developers using Claude Code |
| Interface | Browser UI | Conversation with Claude |
| Best for | Monitoring, quick deploy | Complex multi-step tasks, AI-assisted development |
| Auth | Same OAuth2 credentials | Same OAuth2 credentials |

---

## Message Mapping — Sheet Format

The **Message Mapping** tab accepts an Excel (`.xlsx`) or CSV file alongside source and target XSD schemas.

### Required columns (auto-detected by header keywords)

| Column header | Required | Description |
|---|---|---|
| `Source Field` or `Source` | Yes | Source XML field name |
| `Target Field` or `Target` | Yes | Target XML field name |
| `Mapping Rule`, `Rule`, `Formula`, `Function` | No | Optional transformation rule |

Extra columns (Description, Entity Set, Comments, etc.) are ignored automatically.

### Mapping Rule syntax

**Simple copy** — leave the Rule cell blank for direct field-to-field copies.

**Concat shorthand:**
```
(/msg/header/date)+T+(/msg/header/time)
```

**Any SAP CPI node function:**
```
toUpperCase((/msg/header/sender))
toLowerCase((/msg/header/sender))
trim((/msg/header/sender))
substring((/msg/header/time), 0, 6)
formatDate((/msg/header/date), yyyyMMdd, yyyy-MM-dd)
replaceAll((/msg/header/sender), [^A-Z], )
mapWithDefault((/msg/body/item/code), A, Alpha, B, Beta)
if(equals((/msg/header/type), PO), Purchase, Sales)
concat((/msg/header/date), T, (/msg/header/time))
splitByValue((/msg/header/sender), -)
UseOneAsMany((/msg/header/date))
```

- Source fields: `(/path/to/field)` — resolved against your source XSD
- Constants: bare text (no quotes needed)
- Empty string constant: leave blank after comma — e.g. `replaceAll(..., pattern, )`

---

## Project Structure

```
sap-cpi-assistant/
├── start.bat                        # Double-click to start everything
├── backend/
│   ├── main.py                      # FastAPI app entry point
│   ├── requirements.txt
│   ├── .env                         # API keys (not committed)
│   ├── routers/
│   │   ├── mapping.py               # /api/mapping/* endpoints
│   │   ├── cpi_connect.py           # /api/cpi/* endpoints (live tenant)
│   │   ├── iflow.py
│   │   ├── groovy.py
│   │   ├── xslt.py
│   │   ├── chat.py
│   │   └── documents.py
│   └── services/
│       ├── sheet_mapper.py          # Excel/CSV mapping sheet parser
│       ├── mmap_builder.py          # .mmap XML + ZIP builder
│       ├── xsd_parser.py            # XSD path extractor
│       ├── claude_service.py        # LLM integration
│       └── iflow_packager.py
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   │   ├── CPIConnect.tsx       # Live tenant UI
│   │   │   ├── MessageMapping.tsx
│   │   │   ├── IFlowGenerator.tsx
│   │   │   ├── GroovyGenerator.tsx
│   │   │   ├── XSLTGenerator.tsx
│   │   │   ├── ChatAssistant.tsx
│   │   │   └── DocumentGenerator.tsx
│   │   ├── api/client.ts            # Axios API client (incl. cpiAPI)
│   │   └── components/
│   │       ├── Layout.tsx
│   │       └── Sidebar.tsx
│   ├── vite.config.ts
│   └── package.json
├── mcp-integration-suite/           # MCP server for Claude Code
│   ├── dist/index.js                # Built MCP server entry
│   └── .env                        # CPI credentials for MCP
└── .github/
    └── workflows/deploy.yml         # GitHub Pages auto-deploy
```

---

## API Reference

With the backend running, visit **http://localhost:8000/docs** for the full interactive Swagger UI.

### AI Generation

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/mapping/from-sheet` | Generate `.mmap` from XSDs + mapping sheet (Excel/CSV) |
| `POST` | `/api/mapping/generate` | Generate `.mmap` from schema descriptions |
| `POST` | `/api/iflow/generate` | Generate iFlow XML bundle |
| `POST` | `/api/groovy/generate` | Generate Groovy script |
| `POST` | `/api/xslt/generate` | Generate XSLT stylesheet |
| `POST` | `/api/chat/ask` | Chat with the AI assistant |

### CPI Live Tenant

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/cpi/ping` | Test connectivity to CPI tenant |
| `GET` | `/api/cpi/packages` | List all integration packages |
| `GET` | `/api/cpi/packages/{id}/iflows` | List iFlows in a package |
| `POST` | `/api/cpi/packages/{id}/iflows/{iflowId}/deploy` | Deploy an iFlow to runtime |
| `GET` | `/api/cpi/messages` | Message processing logs (supports `?top=N&status=FAILED`) |
| `GET` | `/api/cpi/security/credentials` | List User Credentials |
| `GET` | `/api/cpi/security/keystores` | List Keystore Entries |
| `GET` | `/health` | Backend health check |

---

## Deployment (GitHub Pages)

The frontend is automatically deployed to GitHub Pages on every push to `main` via `.github/workflows/deploy.yml`.

> **Note:** GitHub Pages only serves static files. All backend-dependent features (AI generation, CPI Connect, message mapping) require the Python backend running locally. The app shows a warning banner when accessed from GitHub Pages.
