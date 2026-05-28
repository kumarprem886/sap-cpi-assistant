# SAP CPI Assistant

An AI-powered assistant for SAP Cloud Platform Integration (CPI) development. Generate iFlow configurations, message mappings, Groovy scripts, XSLT transformations, and integration documents — all from a browser-based UI backed by a Python/FastAPI server. Connect live to your SAP Integration Suite tenant for package management, deployment, security management, and message monitoring.

**Live demo (UI only — no backend):** https://kumarprem886.github.io/sap-cpi-assistant/

---

## Table of Contents

- [Features](#features)
- [Tech Stack](#tech-stack)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [AI Provider Configuration](#ai-provider-configuration)
- [Environment Variables Reference](#environment-variables-reference)
- [CPI Connect — Live Tenant](#cpi-connect--live-tenant)
- [Message Mapping — Sheet Format](#message-mapping--sheet-format)
- [API Reference](#api-reference)
- [MCP Server (Claude Code)](#mcp-server-claude-code)
- [Project Structure](#project-structure)
- [GitHub Pages Deployment](#github-pages-deployment)

---

## Features

| Page | Feature | Description |
|------|---------|-------------|
| **Dashboard** | Overview | Quick links and status of AI provider and CPI connection |
| **iFlow Generator** | AI iFlow XML | Describe your integration in plain English — get a complete, CPI-importable iFlow XML bundle (ZIP). Supports FD image upload to auto-detect flow from a diagram |
| **Message Mapping** | `.mmap` Generator | Upload source + target XSD schemas plus an Excel/CSV mapping sheet → generates a `.mmap` file ready to import into CPI. Also supports manual field selection and AI-assisted automapping |
| **Groovy Scripts** | AI Groovy | Generate, explain, and debug Groovy scripts for CPI message processing |
| **XSLT Generator** | AI XSLT | Generate XSLT 1.0 transformations, or derive them from sample input/output XML pairs |
| **Doc Generator** | Integration Docs | Auto-generate integration design documents in `.docx` format |
| **AI Assistant** | Chat | Conversational AI for SAP CPI questions, code review, and troubleshooting |
| **CPI Connect** | Live Tenant | Full live view of your SAP Integration Suite — browse, deploy, monitor, manage security, data stores, and more |

---

## Tech Stack

**Frontend**
- React 18 + TypeScript
- Vite 5
- Tailwind CSS
- React Router v6
- Lucide React (icons)

**Backend**
- Python 3.10+
- FastAPI + Uvicorn
- httpx (CPI OData API calls)
- openpyxl (Excel parsing)
- lxml (XSD/XML processing)
- python-docx (Word document generation)
- python-dotenv (env management + hot-reload)

**AI Providers (pick one)**
- **Groq** — free cloud inference (default, recommended for getting started)
- **Anthropic Claude** — highest quality (requires paid API key)
- **Ollama** — fully local, no key needed (requires local GPU/CPU)

---

## Prerequisites

| Tool | Version | Link |
|------|---------|------|
| Python | 3.10+ | [python.org](https://www.python.org/downloads/) |
| Node.js | 20+ | [nodejs.org](https://nodejs.org/) |
| **One of:** Groq API Key _or_ Anthropic API Key _or_ Ollama | — | See [AI Provider Configuration](#ai-provider-configuration) |
| SAP BTP Account _(for CPI Connect)_ | — | [hanatrial.ondemand.com](https://account.hanatrial.ondemand.com) |

> **Windows tip:** If `python` is not recognised in your terminal, use `py` instead — it invokes the Python Launcher which finds your installation automatically.

---

## Quick Start

### Option A — One-click (Windows)

Double-click **`start.bat`** in the project root. It will:
1. Open a terminal window running the FastAPI backend on port 8000
2. Open a second terminal window running the Vite frontend on port 5173
3. Launch your browser at http://localhost:5173/sap-cpi-assistant/

### Option B — Manual (any OS)

**Terminal 1 — Backend**
```bash
cd backend
pip install -r requirements.txt     # first time only
py -m uvicorn main:app --reload --port 8000
```
- API base: **http://localhost:8000**
- Interactive API docs (Swagger UI): **http://localhost:8000/docs**

**Terminal 2 — Frontend**
```bash
cd frontend
npm install                          # first time only
npm run dev
```
- App: **http://localhost:5173**

---

## AI Provider Configuration

The AI provider can be set **two ways**:

### 1. Via the Settings UI (recommended — no restart needed)

Click the **AI provider chip** in the bottom-left of the sidebar (shows the current provider name and model). This opens the **AI Provider Settings** modal where you can:

- Switch between **Anthropic**, **Groq**, and **Ollama**
- Enter / update your API key
- Select the model
- Click **Save & Apply** — changes take effect immediately, no backend restart

### 2. Via `backend/.env`

Create (or edit) `backend/.env` and set one of the following blocks:

#### Option A — Groq (free cloud, recommended for getting started)
```env
AI_PROVIDER=groq
GROQ_API_KEY=gsk_...
GROQ_MODEL=llama-3.3-70b-versatile
```
Get a free key at [console.groq.com](https://console.groq.com/).

Available Groq models:
- `llama-3.3-70b-versatile` ← default, best balance
- `llama-3.1-70b-versatile`
- `llama-3.1-8b-instant`
- `llama3-8b-8192`
- `llama3-70b-8192`
- `mixtral-8x7b-32768`
- `gemma2-9b-it`

#### Option B — Anthropic Claude (best quality)
```env
AI_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_MODEL=claude-opus-4-5
```
Get a key at [console.anthropic.com](https://console.anthropic.com/).

Available Claude models:
- `claude-opus-4-5`
- `claude-sonnet-4-5`
- `claude-3-5-sonnet-20241022`
- `claude-3-5-haiku-20241022`
- `claude-3-opus-20240229`

#### Option C — Ollama (fully local, no key needed)
```env
AI_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5-coder:14b
OLLAMA_VISION_MODEL=llava:7b
```
Install Ollama from [ollama.ai](https://ollama.ai/), then pull models:
```bash
ollama pull qwen2.5-coder:14b    # for text/code generation
ollama pull llava:7b             # for FD image analysis (optional)
ollama serve                     # start the Ollama server
```

> **Provider auto-detection:** If `AI_PROVIDER` is not set, the app detects by key presence: `ANTHROPIC_API_KEY` → Claude; `GROQ_API_KEY` → Groq; neither → Ollama.

---

## Environment Variables Reference

Full `backend/.env` reference:

```env
# ── AI Provider ────────────────────────────────────────────────────────────────
AI_PROVIDER=groq                        # "anthropic" | "groq" | "ollama"

# Anthropic (if AI_PROVIDER=anthropic)
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_MODEL=claude-opus-4-5
ANTHROPIC_VISION_MODEL=claude-opus-4-5  # used for iFlow FD image analysis

# Groq (if AI_PROVIDER=groq)
GROQ_API_KEY=gsk_...
GROQ_MODEL=llama-3.3-70b-versatile

# Ollama (if AI_PROVIDER=ollama)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5-coder:14b
OLLAMA_VISION_MODEL=llava:7b

# ── SAP CPI Tenant (for CPI Connect) ─────────────────────────────────────────
CPI_AUTH_TYPE=oauth                     # "oauth" | "basic"
CPI_API_BASE_URL=https://<tenant>.it-cpi018.cfapps.<region>.hana.ondemand.com/api/v1
CPI_BASE_URL=https://<tenant>.it-cpi018-rt.cfapps.<region>.hana.ondemand.com

# OAuth2 (recommended):
CPI_CLIENT_ID=sb-xxxxxxxx...
CPI_CLIENT_SECRET=xxxxxxxx...
CPI_TOKEN_URL=https://<subaccount>.authentication.<region>.hana.ondemand.com/oauth/token

# Basic auth (alternative):
# CPI_AUTH_TYPE=basic
# CPI_USER=S0012345
# CPI_PASS=yourpassword
```

> **Security note:** `backend/.env` is listed in `.gitignore` and will never be committed to the repository. All secrets stay on your machine.

---

## CPI Connect — Live Tenant

The **CPI Connect** page gives you a complete live view of your SAP Integration Suite tenant directly from the app — no BTP Cockpit needed for day-to-day operations.

### Connection Settings

Click **"Connect / Settings"** (gear icon in the CPI Connect header) to open the connection settings modal. You can:
- Switch between OAuth2 and Basic auth
- Update the API Base URL, Token URL, Client ID/Secret (or User/Password)
- Click **Save & Connect** to persist and immediately test the connection
- Click **Test Connection** to verify without saving

This writes to `backend/.env` and hot-reloads — no restart needed.

### Tabs

#### Packages & iFlows
- Browse all integration packages on your tenant
- Expand a package to see its iFlows and all artifact types
- **Deploy** a single iFlow to runtime (shows task ID and polls status)
- **Deploy All** iFlows in a package at once
- **Export** iFlow as ZIP
- **Delete** an iFlow or an entire package
- **Copy** an iFlow from one package to another (with optional rename)
- **Import** a local iFlow ZIP into a package
- **Externalized Parameters** — view and inline-edit iFlow configurations

#### Message Monitor
- Last 50 message processing logs (configurable)
- Filter by status: COMPLETED / FAILED / PROCESSING / RETRY / CANCELLED
- Expand any row to see:
  - Full message details and error text (for FAILED)
  - Processing steps / runs
  - Attachments list
  - Message adapter attributes
- **Retry** failed messages
- **Runtime Status** panel — all currently deployed iFlows with their status (STARTED / ERROR / STOPPING)
- **Undeploy** any running iFlow directly

#### Security
Manage security artifacts with full CRUD:

| Section | Operations |
|---------|-----------|
| **User Credentials** | List, Add (name + user + password), Update, Delete |
| **Secure Parameters** | List, Add (name + value), Update, Delete |
| **OAuth Client Credentials** | List, Add (name + client ID/secret + token URL), Delete |
| **Number Ranges** | List, Add (name + min/max/current), Update, Delete |
| **Access Policies** | List, Add (role name), Delete, View references |
| **Keystores** | List all keystore entries |
| **Certificate Mappings** | List all certificate-to-user mappings |
| **Log Files** | List and download application log archives |

#### Data
Manage runtime data artifacts:

| Section | Operations |
|---------|-----------|
| **Variables (String Parameters)** | List all iFlow runtime variables (set by Write Variable step), Delete |
| **Tenant Configurations** | List global tenant-level key-value settings, Inline edit values |
| **Data Stores** | List all data stores, expand to see entries, download entry payload, delete entry |
| **Message Store Entries** | Browse message store entries, download payload, view attachments |
| **JMS Brokers** | List JMS broker queue details |
| **ID Mapper** | List and delete ID mapping entries, filter by agency/scheme |

### Authentication Flow

**OAuth2 (recommended):**
```
1. POST {CPI_TOKEN_URL}
   Body:  grant_type=client_credentials
   Auth:  Basic({CPI_CLIENT_ID}, {CPI_CLIENT_SECRET})
   →  { "access_token": "eyJ...", "expires_in": 3600 }

2. All CPI API calls:
   GET {CPI_API_BASE_URL}/IntegrationPackages
   Header: Authorization: Bearer eyJ...
```
The token is cached in memory and refreshed automatically 30 seconds before expiry.

**Basic auth:**
```
All CPI API calls:
Authorization: Basic base64({CPI_USER}:{CPI_PASS})
```

### Getting BTP OAuth Credentials

1. Go to **BTP Cockpit → your subaccount → Instances & Subscriptions**
2. Find your **Process Integration** service instance (or create one with plan `api`)
3. Create a **Service Key** — the downloaded JSON contains:
   - `clientid` → `CPI_CLIENT_ID`
   - `clientsecret` → `CPI_CLIENT_SECRET`
   - `tokenurl` → `CPI_TOKEN_URL`
   - `url` → base for `CPI_API_BASE_URL` (append `/api/v1`)

### Recommended Service Instance Roles

When creating the service instance, include these roles in the parameters JSON:

```json
{
  "roles": [
    "WorkspacePackagesMetaData.Read",
    "WorkspacePackagesMetaData.Write",
    "WorkspacePackagesTransport.Read",
    "WorkspacePackagesTransport.Write",
    "IntegrationFlowConfigurationsMetaData.Read",
    "IntegrationFlowConfigurationsMetaData.Write",
    "MessageProcessingLogs.Read",
    "MessagePayload.Read",
    "MonitoringDataRead",
    "UserCredentials.Read",
    "UserCredentials.Write",
    "KeystoreEntries.Read",
    "SecurityMaterial.Read",
    "SecurityMaterial.Write"
  ]
}
```

> **Trial shortcut:** Assign the `PI_Integration_Developer` role collection — it covers all of the above.

---

## Message Mapping — Sheet Format

The **Message Mapping** tab accepts an Excel (`.xlsx`) or CSV mapping sheet alongside source and target XSD schemas.

### Required Columns (auto-detected by header keyword)

| Column keyword | Required | Description |
|---------------|----------|-------------|
| `Source Field` or `Source` | Yes | Source XML element path or field name |
| `Target Field` or `Target` | Yes | Target XML element path or field name |
| `Mapping Rule`, `Rule`, `Formula`, or `Function` | No | Transformation rule (blank = direct copy) |

Extra columns (Description, Entity Set, Comments, Status, etc.) are ignored automatically.

### Mapping Rule Syntax

**Direct copy** — leave the Rule column blank.

**String concatenation shorthand:**
```
(/msg/header/date)+T+(/msg/header/time)
```

**SAP CPI node functions:**
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

**Syntax rules:**
- Source fields: `(/path/to/field)` — resolved against the uploaded source XSD
- Constants: bare text (no quotes needed)
- Empty string constant: leave blank after the last comma — e.g. `replaceAll(..., pattern, )`

---

## API Reference

With the backend running, open **http://localhost:8000/docs** for the full interactive Swagger UI.

### AI Generation Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/iflow/generate` | Generate iFlow XML from description |
| `POST` | `/api/iflow/explain` | Explain an existing iFlow XML |
| `POST` | `/api/iflow/download-zip` | Download iFlow as importable ZIP |
| `POST` | `/api/iflow/fd-to-iflow` | Upload a flow diagram image → generate iFlow |
| `POST` | `/api/iflow/extract-xml` | Extract XML from an uploaded iFlow ZIP |
| `POST` | `/api/mapping/generate` | Generate `.mmap` from field descriptions |
| `POST` | `/api/mapping/automap` | AI automap between two XSDs |
| `POST` | `/api/mapping/generate-mmap` | Generate `.mmap` binary |
| `POST` | `/api/mapping/from-sheet` | Generate `.mmap` from XSDs + mapping sheet |
| `GET`  | `/api/mapping/catalog` | List prebuilt mapping pairs |
| `POST` | `/api/groovy/generate` | Generate Groovy script |
| `POST` | `/api/groovy/explain` | Explain an existing Groovy script |
| `POST` | `/api/groovy/debug` | Debug a Groovy script with error message |
| `POST` | `/api/xslt/generate` | Generate XSLT from description |
| `POST` | `/api/xslt/explain` | Explain an XSLT stylesheet |
| `POST` | `/api/xslt/from-samples` | Derive XSLT from input/output XML samples |
| `POST` | `/api/chat/ask` | Chat with the AI assistant |
| `POST` | `/api/chat/review` | AI review of CPI artifacts |

### Settings Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET`  | `/api/settings/ai` | Get current AI provider settings (keys masked) |
| `PUT`  | `/api/settings/ai` | Save AI provider / key / model — hot-reloads immediately |

### CPI Connect Endpoints

#### Connection
| Method | Path | Description |
|--------|------|-------------|
| `GET`  | `/api/cpi/ping` | Test connectivity to the configured CPI tenant |
| `GET`  | `/api/cpi/settings` | Get current CPI connection settings (credentials masked) |
| `PUT`  | `/api/cpi/settings` | Save CPI connection settings + test connection |

#### Packages & Artifacts
| Method | Path | Description |
|--------|------|-------------|
| `GET`  | `/api/cpi/packages` | List all integration packages |
| `POST` | `/api/cpi/packages` | Create a new package |
| `PUT`  | `/api/cpi/packages/{id}` | Update package name/description |
| `DELETE` | `/api/cpi/packages/{id}` | Delete a package |
| `GET`  | `/api/cpi/packages/{id}/iflows` | List iFlows in a package |
| `GET`  | `/api/cpi/packages/{id}/all-artifacts` | List all artifact types in a package |
| `GET`  | `/api/cpi/packages/{id}/iflows/{iflowId}/export` | Export iFlow as ZIP |
| `DELETE` | `/api/cpi/packages/{id}/iflows/{iflowId}` | Delete an iFlow |
| `POST` | `/api/cpi/copy-iflow` | Copy iFlow between packages |
| `POST` | `/api/cpi/import-iflow` | Import iFlow from JSON descriptor |
| `POST` | `/api/cpi/import-zip` | Import iFlow from local ZIP file |

#### Configurations (Externalized Parameters)
| Method | Path | Description |
|--------|------|-------------|
| `GET`  | `/api/cpi/iflows/{id}/configurations` | Get externalized parameters for an iFlow |
| `PUT`  | `/api/cpi/iflows/{id}/configurations/{key}` | Update an externalized parameter value |

#### Deploy & Runtime
| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/cpi/packages/{id}/iflows/{iflowId}/deploy` | Deploy iFlow to runtime |
| `POST` | `/api/cpi/packages/{id}/deploy-all` | Deploy all iFlows in a package |
| `GET`  | `/api/cpi/deploy-status/{taskId}` | Poll deployment task status |
| `GET`  | `/api/cpi/runtime` | List all deployed iFlows and their status |
| `GET`  | `/api/cpi/runtime/{id}/status` | Get runtime status of a specific iFlow |
| `DELETE` | `/api/cpi/runtime/{id}` | Undeploy an iFlow from runtime |

#### Message Monitor
| Method | Path | Description |
|--------|------|-------------|
| `GET`  | `/api/cpi/messages` | Message processing logs (`?top=N&status=FAILED`) |
| `GET`  | `/api/cpi/messages/{guid}/error` | Error details for a failed message |
| `GET`  | `/api/cpi/messages/{guid}/runs` | Processing runs for a message |
| `GET`  | `/api/cpi/messages/{guid}/attachments` | Attachments for a message |
| `GET`  | `/api/cpi/messages/{guid}/adapter-attributes` | Adapter attributes for a message |

#### Message Store
| Method | Path | Description |
|--------|------|-------------|
| `GET`  | `/api/cpi/message-store-entries` | List message store entries |
| `GET`  | `/api/cpi/message-store-entries/{id}/payload` | Download MSE payload |
| `GET`  | `/api/cpi/message-store-entries/{id}/attachments` | List MSE attachments |
| `GET`  | `/api/cpi/message-store-entries/{id}/attachments/{aid}/payload` | Download attachment payload |

#### Security
| Method | Path | Description |
|--------|------|-------------|
| `GET`  | `/api/cpi/security/credentials` | List User Credentials |
| `POST` | `/api/cpi/security/credentials` | Create User Credential |
| `PUT`  | `/api/cpi/security/credentials/{name}` | Update User Credential |
| `DELETE` | `/api/cpi/security/credentials/{name}` | Delete User Credential |
| `GET`  | `/api/cpi/security/keystores` | List Keystore Entries |
| `GET`  | `/api/cpi/security/secure-parameters` | List Secure Parameters |
| `POST` | `/api/cpi/security/secure-parameters` | Create Secure Parameter |
| `PUT`  | `/api/cpi/security/secure-parameters/{name}` | Update Secure Parameter |
| `DELETE` | `/api/cpi/security/secure-parameters/{name}` | Delete Secure Parameter |
| `GET`  | `/api/cpi/security/oauth-credentials` | List OAuth Client Credentials |
| `POST` | `/api/cpi/security/oauth-credentials` | Create OAuth Client Credential |
| `DELETE` | `/api/cpi/security/oauth-credentials/{name}` | Delete OAuth Client Credential |
| `GET`  | `/api/cpi/security/certificate-mappings` | List Certificate Mappings |
| `GET`  | `/api/cpi/number-ranges` | List Number Ranges |
| `POST` | `/api/cpi/security/number-ranges` | Create Number Range |
| `PUT`  | `/api/cpi/security/number-ranges/{name}` | Update Number Range |
| `DELETE` | `/api/cpi/security/number-ranges/{name}` | Delete Number Range |
| `GET`  | `/api/cpi/access-policies` | List Access Policies |
| `POST` | `/api/cpi/access-policies` | Create Access Policy |
| `DELETE` | `/api/cpi/access-policies/{id}` | Delete Access Policy |
| `GET`  | `/api/cpi/access-policies/{id}/references` | List Access Policy references |
| `GET`  | `/api/cpi/log-files` | List log file archives |
| `GET`  | `/api/cpi/log-files/{app}/download` | Download log file archive |

#### Data Stores & Variables
| Method | Path | Description |
|--------|------|-------------|
| `GET`  | `/api/cpi/datastores` | List all data stores |
| `GET`  | `/api/cpi/datastores/{name}/entries` | List entries in a data store |
| `GET`  | `/api/cpi/datastores/{name}/entries/{id}/payload` | Download data store entry payload |
| `DELETE` | `/api/cpi/datastores/{name}/entries/{id}` | Delete a data store entry |
| `GET`  | `/api/cpi/variables` | List all iFlow runtime variables (String Parameters) |
| `DELETE` | `/api/cpi/variables/{iflowId}/{name}` | Delete a runtime variable |
| `GET`  | `/api/cpi/tenant-configurations` | List global tenant configurations |
| `PUT`  | `/api/cpi/tenant-configurations/{key}` | Update a tenant configuration value |

#### Other
| Method | Path | Description |
|--------|------|-------------|
| `GET`  | `/api/cpi/jms-brokers` | List JMS broker details |
| `GET`  | `/api/cpi/id-maps` | List ID mapping entries (`?agency=X&scheme=Y`) |
| `DELETE` | `/api/cpi/id-maps/{id}` | Delete an ID mapping entry |
| `GET`  | `/health` | Backend health check |

---

## MCP Server (Claude Code)

The project includes an MCP (Model Context Protocol) server that gives **Claude Code** direct conversational access to your CPI tenant — no clicking through the BTP UI.

### What you can do with MCP + Claude Code

| You say | Claude does |
|---------|-------------|
| "List my integration packages" | Calls CPI API, returns the list |
| "Deploy iFlow X from package Y" | Triggers deployment to runtime |
| "Show me failed messages from today" | Pulls message monitoring logs |
| "Create an empty package called Test" | Creates it on your tenant |
| "Get the iFlow XML for X" | Downloads and shows the content |
| "Update the credentials for Y" | Updates the security artifact |

### Setup

**1. Configure credentials** — edit `mcp-integration-suite/.env`:
```env
API_OAUTH_CLIENT_ID=sb-xxxxxxxx...
API_OAUTH_CLIENT_SECRET=xxxxxxxx...
API_OAUTH_TOKEN_URL=https://<subaccount>.authentication.<region>.hana.ondemand.com/oauth/token
API_BASE_URL=https://<tenant>.it-cpitrial05.cfapps.<region>.hana.ondemand.com/api/v1
CPI_BASE_URL=https://<tenant>.it-cpitrial05-rt.cfapps.<region>.hana.ondemand.com
```

**2. Claude Code config** — add to `~/.claude/mcp.json`:
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

**3. Restart Claude Code** — MCP servers load at startup.

### Web App vs MCP

| | Web App (CPI Connect page) | MCP (Claude Code) |
|-|----------------------------|-------------------|
| Who uses it | Any user via browser | Developers using Claude Code |
| Interface | Browser UI | Conversation with Claude |
| Best for | Monitoring, quick deploy, security management | Complex multi-step tasks, AI-assisted development |

---

## Project Structure

```
sap-cpi-assistant/
├── start.bat                          # Double-click to start everything (Windows)
├── start-backend.bat                  # Start backend only
├── start-frontend.bat                 # Start frontend only
├── README.md
│
├── backend/
│   ├── main.py                        # FastAPI app — registers all routers
│   ├── requirements.txt
│   ├── .env                           # Your secrets (never committed)
│   ├── routers/
│   │   ├── iflow.py                   # /api/iflow/* — iFlow generation & packaging
│   │   ├── mapping.py                 # /api/mapping/* — .mmap generation
│   │   ├── groovy.py                  # /api/groovy/* — Groovy script generation
│   │   ├── xslt.py                    # /api/xslt/* — XSLT generation
│   │   ├── chat.py                    # /api/chat/* — AI chat assistant
│   │   ├── documents.py               # /api/documents/* — doc generation
│   │   ├── cpi_connect.py             # /api/cpi/* — live CPI tenant (40+ endpoints)
│   │   └── settings.py                # /api/settings/* — AI provider settings
│   └── services/
│       ├── claude_service.py          # AI provider abstraction (Anthropic/Groq/Ollama)
│       ├── sheet_mapper.py            # Excel/CSV mapping sheet parser
│       ├── mmap_builder.py            # .mmap XML + ZIP builder
│       ├── xsd_parser.py              # XSD path extractor
│       └── iflow_packager.py          # iFlow ZIP packaging
│
├── frontend/
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       ├── api/
│       │   └── client.ts              # Axios API client (all API calls)
│       ├── components/
│       │   ├── Layout.tsx
│       │   └── Sidebar.tsx            # Nav + AI provider chip + AI settings modal
│       └── pages/
│           ├── Dashboard.tsx
│           ├── IFlowGenerator.tsx
│           ├── MessageMapping.tsx
│           ├── GroovyGenerator.tsx
│           ├── XSLTGenerator.tsx
│           ├── DocumentGenerator.tsx
│           ├── ChatAssistant.tsx
│           └── CPIConnect.tsx         # Live CPI tenant UI (all tabs)
│
├── resources/
│   └── schemas/                       # Prebuilt XSD schemas for common SAP messages
│
└── .github/
    └── workflows/
        └── deploy.yml                 # GitHub Pages auto-deploy on push to main
```

---

## GitHub Pages Deployment

The frontend is automatically deployed to GitHub Pages on every push to `main`.

**Important:** GitHub Pages serves static files only. All features that require the Python backend (AI generation, CPI Connect, message mapping) show a warning banner on the GitHub Pages demo. To use the full app, run both servers locally.

To deploy manually:
```bash
cd frontend
npm run build
# GitHub Actions then picks up dist/ and deploys it
```

---

## Troubleshooting

### Backend won't start
- Ensure Python 3.10+ is installed: `py --version`
- Install dependencies: `cd backend && pip install -r requirements.txt`
- Check port 8000 is free: no other process using it

### Frontend won't start
- Ensure Node.js 20+ is installed: `node --version`
- Install dependencies: `cd frontend && npm install`
- Check port 5173 is free

### AI generation returns errors
- **Groq rate limit (429):** You've exceeded the free tier. Wait a few seconds and retry, or switch to a smaller model
- **Claude rate limit (429/529):** Anthropic API limit hit. Wait and retry
- **Ollama not running (503):** Run `ollama serve` in a separate terminal
- **Ollama model not found (503):** Run `ollama pull <model-name>` first

### CPI Connect shows "Not configured"
- Open Connection Settings and enter your CPI tenant credentials
- Click **Save & Connect** to test and persist

### CPI Connect shows "Connection failed"
- Verify `CPI_API_BASE_URL` ends with `/api/v1`
- Verify the OAuth2 credentials are from a current service key (not expired)
- Ensure your service instance has the required roles (see [above](#recommended-service-instance-roles))
- For basic auth: verify the user has `PI_Integration_Developer` role

### Changing AI provider mid-session
Click the AI provider chip in the bottom-left sidebar, make your change, and click **Save & Apply**. The backend hot-reloads immediately — no restart needed.
