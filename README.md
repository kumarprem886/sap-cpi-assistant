# SAP CPI Assistant

An AI-powered assistant for SAP Cloud Platform Integration (CPI) development. Generate iFlow configurations, message mappings with all 51 official SAP CPI functions, Groovy scripts, XSLT transformations, and integration documents — all from a browser-based UI backed by a Python/FastAPI server. Connect live to your SAP Integration Suite tenant for package management, deployment, monitoring, and security management.

**Live demo (UI only — no backend):** https://kumarprem886.github.io/sap-cpi-assistant/

---

## Table of Contents

- [What Uses Script vs AI](#what-uses-script-vs-ai)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Default Login](#default-login)
- [AI Provider Configuration](#ai-provider-configuration)
- [Environment Variables Reference](#environment-variables-reference)
- [Message Mapping — Full Guide](#message-mapping--full-guide)
- [CPI Connect — Live Tenant](#cpi-connect--live-tenant)
- [User Management](#user-management)
- [API Reference](#api-reference)
- [Project Structure](#project-structure)
- [Troubleshooting](#troubleshooting)

---

## What Uses Script vs AI

Understanding which parts of the app are deterministic Python code vs live AI calls helps you know what to expect and trust.

### Pure Python Script (deterministic — no AI, no API cost)

| Feature | File | Details |
|---|---|---|
| `.mmap` XML builder | `mmap_builder.py` | Converts mapping rules → exact SAP CPI XML format. Handles all 51 official functions with correct brick/arg/binding structure |
| Rule parser | `sheet_mapper.py` | Parses Excel/CSV sheets, resolves field names or XPaths, splits function args (quote-aware) |
| XSD parser | `xsd_parser.py` | Reads XSD files, extracts all element paths, handles complex/simple types and unbounded sequences |
| ZIP assembler | `mmap_builder.py` | Packages `.mmap` + XSD files into CPI-importable ZIP (correct `wsdl/` and `mapping/` structure) |
| Auto-parent injection | `mmap_builder.py` | Detects and auto-adds missing container/parent elements so CPI imports cleanly |
| CPI API calls | `cpi_connect.py` | All 40+ REST calls to your SAP Integration Suite tenant |
| Auth / JWT | `auth_service.py` | Login, token generation, bcrypt password hashing |
| Excel template | `mapping.py` | Generates downloadable mapping sheet template |
| Standard XSD catalog | `mapping.py` | Serves 50+ pre-loaded OData and IDoc XSDs from the dropdown |
| Prebuilt mapping load | `prebuilt_mapper.py` | Stores and serves pre-generated standard mapping pairs |

### AI — LLM API Call (costs tokens / requires key)

| Feature | Trigger | What the AI decides |
|---|---|---|
| Smart Mapping from Idea | `/generate-from-idea` | Reads your text description → picks source/target XSD from catalog → generates field mappings + function rules |
| Smart Mapping from XSDs | `/generate-from-source` | Given source + target XSDs with no sheet → AI decides what maps to what and which function to use |
| Functional rule derivation | `/derive-rules` | Given direct field mappings from a sheet → AI suggests appropriate functions (e.g. `formatDate`, `sum`, `notEquals`) |
| Field intelligence pre-step | inside idea generation | AI analyses field names to understand business meaning before suggesting mappings |
| iFlow generation | `/api/iflow/generate` | Generates complete iFlow XML from plain-English description |
| Flow diagram → iFlow | `/api/iflow/fd-to-iflow` | Reads uploaded image, identifies integration pattern, produces iFlow XML |
| Groovy script generation | `/api/groovy/generate` | Generates production-ready Groovy for CPI message processing |
| XSLT generation | `/api/xslt/generate` | Generates XSLT 1.0 from description or sample XML pairs |
| Document generation | `/api/documents/*` | Generates integration design documents in `.docx` format |
| AI Chat assistant | `/api/chat/ask` | Conversational SAP CPI help, code review, troubleshooting |
| Prebuilt mapping generation | `/prebuilt/generate/{id}` | AI generates mapping rules for each standard pair (runs once, result is saved) |

> **Key principle:** AI decides *what* to map and *which function to use*. Python always does the *actual XML generation* — because the `.mmap` XML structure must be byte-perfect for CPI to accept it.

---

## Features

| Page | Feature | Powered by |
|------|---------|------------|
| **Dashboard** | App overview, AI provider status, CPI connection status | — |
| **iFlow Generator** | Generate CPI-importable iFlow ZIP from plain English. Supports flow diagram (FD) image upload | AI |
| **Message Mapping** | Full `.mmap` generator with 51 SAP CPI functions, 3 generation modes, standard XSD catalog, direct CPI import | Script + AI |
| **Groovy Scripts** | Generate, explain, and debug Groovy scripts for CPI message processing | AI |
| **XSLT Generator** | Generate XSLT 1.0, or derive from sample input/output XML pairs | AI |
| **Doc Generator** | Auto-generate integration design documents in `.docx` | AI |
| **AI Assistant** | Conversational AI for SAP CPI questions, code review, troubleshooting | AI |
| **CPI Connect** | Live SAP Integration Suite — browse, deploy, monitor, manage security and data stores | Script |
| **User Management** | Admin panel to create, update, reset passwords, and delete app users | Script |

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
- SQLite + SQLAlchemy (user database)
- python-jose + bcrypt (JWT auth)
- httpx (CPI OData API calls)
- openpyxl / xlrd (Excel parsing)
- lxml (XSD/XML processing)
- python-docx (Word document generation)
- python-dotenv (env management + hot-reload)

**AI Providers — choose any one or more**
- Anthropic Claude, OpenAI GPT, Google Gemini, Groq, OpenRouter, Mistral AI, NVIDIA NIM, Ollama (local)

---

## Prerequisites

Install these before cloning:

| Tool | Version | Notes | Link |
|------|---------|-------|------|
| **Python** | 3.10+ | Tick **"Add Python to PATH"** during install | [python.org](https://www.python.org/downloads/) |
| **Node.js** | 20+ | LTS version recommended | [nodejs.org](https://nodejs.org/) |
| **Git** | any | To clone the repository | [git-scm.com](https://git-scm.com/) |
| **AI provider key** | — | Or use Ollama (free, local) | See [AI Provider Configuration](#ai-provider-configuration) |
| **SAP BTP account** | — | Only needed for CPI Connect | [hanatrial.ondemand.com](https://account.hanatrial.ondemand.com) |

> **Windows:** If `python` is not recognised, use `py` — the Python Launcher finds your installation automatically.

---

## Quick Start

### Step 1 — Clone the repository

```bash
git clone https://github.com/kumarprem886/sap-cpi-assistant.git
cd sap-cpi-assistant
```

### Step 2 — Configure AI provider

```bash
# Copy the example config
cp backend/.env.example backend/.env      # Mac/Linux
copy backend\.env.example backend\.env    # Windows
```

Open `backend/.env` and uncomment the AI provider block you want to use.  
**Fastest start:** Groq (free, no install) or Ollama (free, local, no key).  
See [AI Provider Configuration](#ai-provider-configuration) for all 8 options.

### Step 3 — Start the app

**Option A — One-click (Windows)**

Double-click **`start.bat`**. It automatically:
- Detects your Python and Node.js installations
- Installs all dependencies on first run
- Creates `backend/.env` from `.env.example` if it doesn't exist
- Starts backend on port 8000 and frontend on port 5173
- Opens your browser at **http://localhost:5173**

**Option B — Manual (Windows / Mac / Linux)**

Open two terminals:

```bash
# Terminal 1 — Backend
cd backend
pip install -r requirements.txt      # first time only
py -m uvicorn main:app --reload --port 8000
# Mac/Linux: python -m uvicorn main:app --reload --port 8000
```

```bash
# Terminal 2 — Frontend
cd frontend
npm install                           # first time only
npm run dev
```

| URL | What |
|-----|------|
| **http://localhost:5173** | The app |
| **http://localhost:8000/docs** | Swagger API docs |

### What happens on first run

- `backend/data/app.db` is created automatically (SQLite database)
- Default admin account is created (see below)
- No manual database setup needed

---

## Default Login

The app requires login. The database and default admin account are created **automatically** on first backend startup — no setup needed.

| Field | Value |
|-------|-------|
| Email | `admin@cpi.local` |
| Password | `admin123` |

> **Change this immediately** after first login via the profile menu or User Management page.

---

## AI Provider Configuration

The app supports **8 AI providers**. The provider can be set two ways:

### 1. Via the Settings UI (recommended — no restart needed)

Click the **AI provider chip** in the bottom-left sidebar. This opens the AI Provider Settings modal where you can switch provider, enter/update your API key and model, and click **Save & Apply** — changes take effect immediately.

### 2. Via `backend/.env`

Create (or edit) `backend/.env`. Set one block:

```env
# ── Anthropic Claude (best quality) ──────────────────────────────────────
AI_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_MODEL=claude-opus-4-5

# ── Groq / Llama (free cloud, fast) ──────────────────────────────────────
AI_PROVIDER=groq
GROQ_API_KEY=gsk_...
GROQ_MODEL=llama-3.3-70b-versatile

# ── OpenAI GPT ────────────────────────────────────────────────────────────
AI_PROVIDER=openai
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o

# ── Google Gemini (has free tier) ─────────────────────────────────────────
AI_PROVIDER=gemini
GOOGLE_API_KEY=AIza...
GEMINI_MODEL=gemini-2.0-flash

# ── OpenRouter (many models, some free) ───────────────────────────────────
AI_PROVIDER=openrouter
OPENROUTER_API_KEY=sk-or-...
OPENROUTER_MODEL=meta-llama/llama-3.3-70b-instruct

# ── Mistral AI ────────────────────────────────────────────────────────────
AI_PROVIDER=mistral
MISTRAL_API_KEY=...
MISTRAL_MODEL=mistral-large-latest

# ── NVIDIA NIM ────────────────────────────────────────────────────────────
AI_PROVIDER=nvidia
NVIDIA_API_KEY=nvapi-...
NVIDIA_MODEL=meta/llama-3.3-70b-instruct

# ── Ollama (fully local, no key needed) ───────────────────────────────────
AI_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5-coder:14b
OLLAMA_VISION_MODEL=llava:7b
```

> **Auto-detection:** If `AI_PROVIDER` is not set, the app detects by key presence: `ANTHROPIC_API_KEY` → Claude; `GROQ_API_KEY` → Groq; `OPENAI_API_KEY` → OpenAI; `GOOGLE_API_KEY` → Gemini; none found → Ollama.

**Ollama setup:**
```bash
# Install from https://ollama.ai, then:
ollama pull qwen2.5-coder:14b    # text/code generation
ollama pull llava:7b             # image analysis (optional, for iFlow FD)
ollama serve                     # start the server
```

---

## Environment Variables Reference

Full `backend/.env` reference:

```env
# ── AI Provider ────────────────────────────────────────────────────────────────
AI_PROVIDER=groq                        # anthropic | groq | openai | gemini |
                                        # openrouter | mistral | nvidia | ollama

ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_MODEL=claude-opus-4-5
ANTHROPIC_VISION_MODEL=claude-opus-4-5

GROQ_API_KEY=gsk_...
GROQ_MODEL=llama-3.3-70b-versatile

OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o

GOOGLE_API_KEY=AIza...
GEMINI_MODEL=gemini-2.0-flash

OPENROUTER_API_KEY=sk-or-...
OPENROUTER_MODEL=meta-llama/llama-3.3-70b-instruct

MISTRAL_API_KEY=...
MISTRAL_MODEL=mistral-large-latest

NVIDIA_API_KEY=nvapi-...
NVIDIA_MODEL=meta/llama-3.3-70b-instruct

OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5-coder:14b
OLLAMA_VISION_MODEL=llava:7b

# ── SAP CPI Tenant (for CPI Connect) ─────────────────────────────────────────
CPI_AUTH_TYPE=oauth                     # oauth | basic

# OAuth2 (recommended)
CPI_API_BASE_URL=https://<tenant>.it-cpi018.cfapps.<region>.hana.ondemand.com/api/v1
CPI_BASE_URL=https://<tenant>.it-cpi018-rt.cfapps.<region>.hana.ondemand.com
CPI_CLIENT_ID=sb-xxxxxxxx...
CPI_CLIENT_SECRET=xxxxxxxx...
CPI_TOKEN_URL=https://<subaccount>.authentication.<region>.hana.ondemand.com/oauth/token

# Basic auth (alternative)
# CPI_AUTH_TYPE=basic
# CPI_USER=S0012345
# CPI_PASS=yourpassword

# ── App Settings ──────────────────────────────────────────────────────────────
JWT_SECRET=your-random-secret-here     # change this in production
```

> `backend/.env` is in `.gitignore` — secrets are never committed to the repository.

---

## Message Mapping — Full Guide

The Message Mapping page is the most powerful feature of the app. It generates SAP CPI Graphical Message Mapping (`.mmap`) files that can be directly imported into your CPI tenant.

### Generation Modes

| Mode | Inputs | What AI does | What Script does |
|------|--------|-------------|-----------------|
| **Idea only** | Plain text description | Picks source + target XSD from catalog, generates all field mappings and function rules | Builds the `.mmap` XML from AI's rule output |
| **Source XSD only** | Source XSD + description | AI generates a suitable target XSD and mapping rules | Builds both XSDs + `.mmap` ZIP |
| **Full sheet** | Source XSD + Target XSD + Excel/CSV mapping sheet | (Optional) AI derives function rules for direct-mapped fields | Script resolves field names → XPaths, builds `.mmap` |

### Standard XSD Catalog

50+ SAP standard schemas are built into the app and available from the source/target dropdowns:

**OData (S/4HANA API):**  
`A_SalesOrder`, `A_PurchaseOrder`, `A_Product`, `A_BusinessPartner`, `A_Supplier`, `A_SupplierInvoice`, `A_OutboundDelivery`, `A_MaterialDocument`, `A_ProductionOrder`, `A_CostCenter`, and more.

**IDoc:**  
`MATMAS05` (Material Master), `ORDERS05` (Purchase Order), `DEBMAS06` (Customer), `CREMAS05` (Vendor), `HRMD_A` (HR Master), `INVOIC02` (Invoice), `DESADV01` (Delivery Advice), and more.

In **Idea mode**, the app automatically detects which catalog XSD you mean from natural language:
- "sales order" → `A_SalesOrder.xsd`
- "material" / "product" / "MATMAS" → `A_Product.xsd`
- "purchase order" / "PO" → `A_PurchaseOrder.xsd`
- "business partner" / "customer" → `A_BusinessPartner.xsd`

### Prebuilt Mapping Catalog

Pre-generated mapping pairs for the most common SAP integration scenarios are available as a dropdown. Selecting a pair:
- Auto-fills the source and target XSD fields
- Pre-populates the mapping sheet with standard field mappings
- Can be customised before generating the `.mmap`

### Mapping Sheet Format (Excel / CSV)

The sheet parser accepts `.xlsx`, `.xls`, or `.csv` files. Column headers are detected automatically by keyword matching.

**Required columns:**

| Column keyword | Required | Description |
|---------------|----------|-------------|
| `Source Field` or `Source` | Yes | Source XML element — either full XPath (`/Order/Header/Date`) or short name (`Date`) |
| `Target Field` or `Target` | Yes | Target XML element — same formats accepted |
| `Mapping Rule`, `Rule`, `Formula`, or `Function` | No | Transformation rule (blank = direct copy) |
| `Functional Rule`, `Func Rule` | No | Alternative rule column |
| `Technical Rule`, `Tech Rule` | No | Alternative rule column |

All other columns (Description, Entity Set, Status, Comments, etc.) are ignored.

**Source/target fields accept:**
- Full XPath: `/FinancialDoc/Header/Currency`
- Partial XPath: `Header/Currency`
- Short field name: `Currency`
- Standard OData field: `RequestedQuantity` *(resolved to longest matching path in XSD)*

### Mapping Rule Syntax

**Direct copy** — leave the rule blank. The script maps source to target 1-to-1.

**Concat shorthand:**
```
(/msg/header/date)+T+(/msg/header/time)
(/Address/Street)+", "+(/Address/City)+", "+(/Address/Country)
```

**Function call syntax — `funcName(arg1, arg2, ...)`:**
- Source fields: `(/path/to/field)` — resolved against the uploaded source XSD
- Constants: bare text — `EUR`, `yyyyMMdd`, `DEFAULT`
- Quoted constants for special chars: `","` for a comma delimiter
- Empty string constant: leave blank after the last comma — `replaceAll(..., pattern, )`

### All 51 Supported SAP CPI Functions

Every official SAP CPI graphical mapping function is implemented. The script generates the **exact XML brick format** that CPI accepts.

#### Arithmetic (18 functions)
```
add((/field1), (/field2))              — field1 + field2
subtract((/field1), (/field2))         — field1 - field2
multiply((/field1), (/field2))         — field1 * field2
divide((/field1), (/field2))           — field1 / field2
power((/base), (/exponent))            — base ^ exponent
max((/field1), (/field2))              — larger of the two
min((/field1), (/field2))              — smaller of the two
abs((/field))                          — absolute value
neg((/field))                          — negate (×−1)
inv((/field))                          — inverse (1/x)
sqrt((/field))                         — square root
sqr((/field))                          — square (x²)
sign((/field))                         — +1, 0, or −1
ceil((/field))                         — ceiling (round up)
floor((/field))                        — floor (round down)
round((/field))                        — round to nearest integer
FormatNum((/field), 0.00)              — format number with pattern
equalsA((/field1), (/field2))          — numeric equality check
```

#### Boolean (6 functions)
```
Equals((/field), OPEN)                 — string equality → true/false
notEquals((/field), EUR)               — string inequality → true/false
And((/bool1), (/bool2))                — logical AND of two boolean fields
Or((/bool1), (/bool2))                 — logical OR of two boolean fields
Not((/boolField))                      — logical NOT
if((/condition), trueValue, falseValue) — conditional output
```
> Constants in comparison functions become `constant` function bricks connected to the input queue — not bindings. This is the correct SAP CPI format.

#### Constant (3 functions)
```
constant(SAP_SYSTEM)                   — emit a fixed literal value (no source field)
copyValue((/field))                    — copy value as-is
currentDate()                          — insert today's date (no arguments)
```

#### Conversion (2 functions)
```
fixValues((/field))                    — lookup table (configure table in CPI UI after import)
valuemap((/field))                     — value mapping reference (configure in CPI Value Mapping tool)
```

#### Date (5 functions)
```
formatDate((/dateField), yyyyMMdd, yyyy-MM-dd)   — reformat date (alias: TransformDate)
CompareDates((/date1), (/date2))                 — compare two date fields
DateBefore((/date1), (/date2))                   — date1 is before date2
DateAfter((/date1), (/date2))                    — date1 is after date2
currentDate()                                     — today's date (counted in Constant)
```

#### Node (11 functions)
```
exists((/field))                       — true if field has a value
isNil((/field))                        — true if field is xsi:nil
getHeader(SAP_SENDER)                  — read a CPI message header by name
getProperty(system.id)                 — read an iFlow integration property
mapWithDefault((/field), DEFAULT)      — use DEFAULT if field is missing
collapseContexts((/repeatingField))    — merge N repeating values into 1 string (N→1)
SplitByValue((/field), ",")            — split one value into N by delimiter (1→N)
useOneAsMany((/value), (/ctxParent), (/ctxField)) — repeat 1 value for each context occurrence (1→N)
counter(1, 1)                          — sequential counter (start, increment)
sort((/field), ascending)              — sort values
sortByKey((/field), ascending)         — sort by key
```

#### Statistics (4 functions — the only 4 that exist in SAP CPI)
```
sum((/field))                          — sum of all values in context (N→1)
average((/field))                      — average of all values (N→1)
count((/field))                        — count of occurrences (N→1)
index((/field))                        — 0-based sequential index of current occurrence
```
> `first()` and `last()` do **not** exist in SAP CPI standard functions.

#### Text (16 functions)
```
substring((/field), 0, 6)              — extract substring (from position, length)
concat((/field1), (/field2), -)        — join fields with a separator
length((/field))                       — string length
replaceString((/field), -, )           — replace/delete pattern (search, replace)
toUpperCase((/field))                  — UPPER CASE
toLowerCase((/field))                  — lower case
trim((/field))                         — remove leading/trailing whitespace
equalsS((/field1), (/field2))          — string equality (both as queue inputs)
compare((/field1), (/field2))          — lexicographic comparison
indexOf((/field), search)              — position of search string
lastIndexOf((/field), search)          — last position of search string
endsWith((/field), suffix)             — true if field ends with suffix
startsWith((/field), prefix)           — true if field starts with prefix
contains((/field), search)             — true if field contains search string
formatByExample((/field), example)     — format by example string
```

### Context Rules

Context determines how many times a mapping executes and at what XML hierarchy level.

| Pattern | Description | Function to use |
|---------|-------------|-----------------|
| **1→1** (same level) | Map one field to one field | Direct copy or any transform |
| **N→1** (aggregate) | Many source values → one target value | `sum()`, `average()`, `count()`, `collapseContexts()` |
| **1→N** (expand) | One header value repeated for each child | `useOneAsMany()` |
| **N→N** (same repeating level) | Each item maps to each item | Direct copy or transform |

`useOneAsMany` requires 3 arguments:
```
useOneAsMany((/Header/OrderDate), (/Items/Item), (/Items/Item/LineNum))
             ─────── value ──────  ─ context parent ─  ─ context field ─
```

### Exporting and Importing

After generation the UI shows:
- **Download Mapping ZIP** — saves the CPI-importable `.zip` to your machine
- **Import to CPI** — sends the ZIP directly to your connected CPI tenant via the REST API (shows the URL and JSON payload before sending, then prompts for confirmation)

The ZIP structure matches the CPI internal format exactly:
```
MM_<name>.zip
├── wsdl/
│   ├── source.xsd
│   └── target.xsd
└── mapping/
    └── MM_<name>.mmap
```

### XML Paste / Upload

In addition to XSD file upload, you can:
- **Paste raw XML** directly into the source/target field
- **Upload an XML document** — the app derives an XSD from its structure automatically

---

## CPI Connect — Live Tenant

The CPI Connect page gives you a complete live view of your SAP Integration Suite tenant.

### Connection Settings

Click the gear icon in the CPI Connect header. You can switch between OAuth2 and Basic auth, update credentials, and click **Save & Connect** to persist and test immediately. Changes write to `backend/.env` and hot-reload — no restart needed.

### Authentication

**OAuth2 (recommended):**
The app exchanges your `client_id` / `client_secret` for a bearer token and caches it, refreshing automatically 30 seconds before expiry.

**Getting BTP OAuth credentials:**
1. BTP Cockpit → your subaccount → **Instances & Subscriptions**
2. Find your **Process Integration** service instance → create a **Service Key**
3. The downloaded JSON contains: `clientid`, `clientsecret`, `tokenurl`, `url`

**Recommended roles for the service instance:**
```json
{
  "roles": [
    "WorkspacePackagesMetaData.Read", "WorkspacePackagesMetaData.Write",
    "WorkspacePackagesTransport.Read", "WorkspacePackagesTransport.Write",
    "IntegrationFlowConfigurationsMetaData.Read",
    "IntegrationFlowConfigurationsMetaData.Write",
    "MessageProcessingLogs.Read", "MessagePayload.Read", "MonitoringDataRead",
    "UserCredentials.Read", "UserCredentials.Write",
    "KeystoreEntries.Read", "SecurityMaterial.Read", "SecurityMaterial.Write"
  ]
}
```
> **Trial shortcut:** Assign the `PI_Integration_Developer` role collection.

### Packages & iFlows Tab

- Browse all integration packages
- Expand a package to see iFlows and all artifact types
- **Deploy** a single iFlow to runtime (polls task status)
- **Deploy All** iFlows in a package at once
- **Export** iFlow as ZIP
- **Delete** an iFlow or an entire package
- **Copy** an iFlow between packages (with optional rename)
- **Import** a local iFlow ZIP into a package
- **Externalized Parameters** — view and inline-edit iFlow configuration values

### Message Monitor Tab

- Last 50 message processing logs (configurable count)
- Filter by status: COMPLETED / FAILED / PROCESSING / RETRY / CANCELLED
- Expand any log row to see: full error text, processing steps, attachments, adapter attributes
- **Retry** failed messages
- **Runtime Status** panel — all deployed iFlows with STARTED / ERROR / STOPPING status
- **Undeploy** any running iFlow

### Security Tab

| Section | Operations |
|---------|-----------|
| User Credentials | List, Add, Update, Delete |
| Secure Parameters | List, Add, Update, Delete |
| OAuth Client Credentials | List, Add, Delete |
| Number Ranges | List, Add, Update, Delete |
| Access Policies | List, Add, Delete, View references |
| Keystores | List all keystore entries |
| Certificate Mappings | List all certificate-to-user mappings |
| Log Files | List and download application log archives |

### Data Tab

| Section | Operations |
|---------|-----------|
| Variables (String Parameters) | List all iFlow runtime variables, Delete |
| Tenant Configurations | List global settings, Inline-edit values |
| Data Stores | List stores, expand entries, download payload, delete entry |
| Message Store Entries | Browse entries, download payload, view attachments |
| JMS Brokers | List JMS broker queue details |
| ID Mapper | List and delete ID mapping entries, filter by agency/scheme |

---

## User Management

The app has a built-in user system with role-based access.

### Roles

| Role | Permissions |
|------|-------------|
| `admin` | Full access — all features + User Management page |
| `user` | All features except User Management |

### Admin Panel (User Management page)

Accessible only to admin users:
- View all registered users
- Create new users (name, email, password, role)
- Update user name, email, role
- Reset any user's password
- Delete users

### Self-service (Profile menu)

Any logged-in user can:
- Update their own name and email (`PUT /api/auth/me`)
- Change their own password (`POST /api/auth/change-password`)

### Default Admin Account

| Email | Password |
|-------|----------|
| `admin@cpi.local` | `admin123` |

Change the password immediately after first login.

---

## API Reference

With the backend running, open **http://localhost:8000/docs** for the full interactive Swagger UI.

### Auth Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/auth/login` | Login — returns JWT access token |
| `POST` | `/api/auth/register` | Register a new account |
| `GET`  | `/api/auth/me` | Get current user profile |
| `PUT`  | `/api/auth/me` | Update name / email |
| `POST` | `/api/auth/change-password` | Change password |

### User Management Endpoints (admin only)

| Method | Path | Description |
|--------|------|-------------|
| `GET`  | `/api/users` | List all users |
| `POST` | `/api/users` | Create a user |
| `PUT`  | `/api/users/{id}` | Update user |
| `POST` | `/api/users/{id}/reset-password` | Reset user password |
| `DELETE` | `/api/users/{id}` | Delete user |

### AI Generation Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/iflow/generate` | Generate iFlow XML from description |
| `POST` | `/api/iflow/explain` | Explain an existing iFlow XML |
| `POST` | `/api/iflow/download-zip` | Download iFlow as importable ZIP |
| `POST` | `/api/iflow/fd-to-iflow` | Upload flow diagram image → generate iFlow |
| `POST` | `/api/iflow/extract-xml` | Extract XML from uploaded iFlow ZIP |
| `POST` | `/api/groovy/generate` | Generate Groovy script |
| `POST` | `/api/groovy/explain` | Explain a Groovy script |
| `POST` | `/api/groovy/debug` | Debug a Groovy script with error message |
| `POST` | `/api/xslt/generate` | Generate XSLT from description |
| `POST` | `/api/xslt/explain` | Explain an XSLT stylesheet |
| `POST` | `/api/xslt/from-samples` | Derive XSLT from input/output XML samples |
| `POST` | `/api/chat/ask` | Chat with the AI assistant |
| `POST` | `/api/chat/review` | AI review of CPI artifacts |

### Mapping Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET`  | `/api/mapping/catalog` | List all bundled XSD schemas + prebuilt status |
| `GET`  | `/api/mapping/schema/{filename}` | Download a catalog XSD file |
| `GET`  | `/api/mapping/prebuilt/status` | Prebuilt generation status for all catalog pairs |
| `POST` | `/api/mapping/prebuilt/generate/{pair_id}` | Trigger AI generation for one catalog pair |
| `POST` | `/api/mapping/prebuilt/generate-all` | Trigger generation for all catalog pairs |
| `GET`  | `/api/mapping/prebuilt/download/{pair_id}` | Download generated prebuilt mapping ZIP |
| `GET`  | `/api/mapping/prebuilt/preview/{pair_id}` | Preview prebuilt mapping rules |
| `GET`  | `/api/mapping/template` | Download the blank mapping sheet Excel template |
| `POST` | `/api/mapping/preview-sheet` | Parse uploaded sheet → preview field table |
| `POST` | `/api/mapping/derive-rules` | AI derives function rules for direct mappings |
| `POST` | `/api/mapping/from-sheet-preview` | Parse sheet + XSDs → preview resolved mappings |
| `POST` | `/api/mapping/from-sheet` | Full pipeline: sheet + XSDs → `.mmap` ZIP |
| `POST` | `/api/mapping/automap` | AI automap between two XSDs (no sheet) |
| `POST` | `/api/mapping/generate-mmap-auto` | Generate `.mmap` ZIP from automapped rules |
| `POST` | `/api/mapping/generate-from-source` | Smart mapping from source XSD + description |
| `POST` | `/api/mapping/generate-from-idea` | Smart mapping from plain-text idea only |
| `POST` | `/api/mapping/generate` | Generate `.mmap` from JSON mapping rules |
| `POST` | `/api/mapping/generate-mmap` | Generate `.mmap` binary from structured input |

### Settings Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET`  | `/api/settings/ai` | Get current AI provider settings (keys masked) |
| `PUT`  | `/api/settings/ai` | Save AI provider / key / model — hot-reloads immediately |

### CPI Connect Endpoints (40+)

#### Connection
| Method | Path | Description |
|--------|------|-------------|
| `GET`  | `/api/cpi/ping` | Test connectivity to configured CPI tenant |
| `GET`  | `/api/cpi/settings` | Get CPI connection settings (credentials masked) |
| `PUT`  | `/api/cpi/settings` | Save CPI settings + test connection |

#### Packages & Artifacts
| Method | Path | Description |
|--------|------|-------------|
| `GET`  | `/api/cpi/packages` | List all integration packages |
| `POST` | `/api/cpi/packages` | Create a new package |
| `PUT`  | `/api/cpi/packages/{id}` | Update package |
| `DELETE` | `/api/cpi/packages/{id}` | Delete a package |
| `GET`  | `/api/cpi/packages/{id}/iflows` | List iFlows in a package |
| `GET`  | `/api/cpi/packages/{id}/all-artifacts` | List all artifact types |
| `GET`  | `/api/cpi/packages/{id}/iflows/{iflowId}/export` | Export iFlow as ZIP |
| `DELETE` | `/api/cpi/packages/{id}/iflows/{iflowId}` | Delete an iFlow |
| `POST` | `/api/cpi/copy-iflow` | Copy iFlow between packages |
| `POST` | `/api/cpi/import-zip` | Import iFlow from local ZIP |

#### Deploy & Runtime
| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/cpi/packages/{id}/iflows/{iflowId}/deploy` | Deploy iFlow to runtime |
| `POST` | `/api/cpi/packages/{id}/deploy-all` | Deploy all iFlows in a package |
| `GET`  | `/api/cpi/deploy-status/{taskId}` | Poll deployment task status |
| `GET`  | `/api/cpi/runtime` | List all deployed iFlows + status |
| `DELETE` | `/api/cpi/runtime/{id}` | Undeploy an iFlow |

#### Message Monitor & Store
| Method | Path | Description |
|--------|------|-------------|
| `GET`  | `/api/cpi/messages` | Message processing logs (`?top=N&status=FAILED`) |
| `GET`  | `/api/cpi/messages/{guid}/error` | Error details for a failed message |
| `GET`  | `/api/cpi/messages/{guid}/runs` | Processing runs |
| `GET`  | `/api/cpi/messages/{guid}/attachments` | Message attachments |
| `GET`  | `/api/cpi/message-store-entries` | List message store entries |
| `GET`  | `/api/cpi/message-store-entries/{id}/payload` | Download entry payload |

#### Security
| Method | Path | Description |
|--------|------|-------------|
| `GET/POST/PUT/DELETE` | `/api/cpi/security/credentials` | User Credentials CRUD |
| `GET/POST/PUT/DELETE` | `/api/cpi/security/secure-parameters` | Secure Parameters CRUD |
| `GET/POST/DELETE` | `/api/cpi/security/oauth-credentials` | OAuth Client Credentials |
| `GET/POST/PUT/DELETE` | `/api/cpi/security/number-ranges` | Number Ranges |
| `GET/POST/DELETE` | `/api/cpi/access-policies` | Access Policies |
| `GET` | `/api/cpi/security/keystores` | Keystore entries |
| `GET` | `/api/cpi/log-files` | Log file archives |

#### Data Stores & Variables
| Method | Path | Description |
|--------|------|-------------|
| `GET`  | `/api/cpi/datastores` | List data stores |
| `GET`  | `/api/cpi/datastores/{name}/entries` | List data store entries |
| `DELETE` | `/api/cpi/datastores/{name}/entries/{id}` | Delete an entry |
| `GET`  | `/api/cpi/variables` | List iFlow runtime variables |
| `DELETE` | `/api/cpi/variables/{iflowId}/{name}` | Delete a variable |
| `GET`  | `/api/cpi/tenant-configurations` | Global tenant configurations |
| `PUT`  | `/api/cpi/tenant-configurations/{key}` | Update a tenant config |
| `GET`  | `/api/cpi/jms-brokers` | JMS broker details |
| `GET`  | `/api/cpi/id-maps` | ID mapping entries |

---

## Project Structure

```
sap-cpi-assistant/
├── start.bat                          # Double-click to start everything (Windows)
├── start-backend.bat
├── start-frontend.bat
├── README.md
│
├── backend/
│   ├── main.py                        # FastAPI app — registers all routers, JWT middleware
│   ├── database.py                    # SQLite engine + session factory
│   ├── requirements.txt
│   ├── .env                           # Your secrets (never committed)
│   ├── .env.example                   # Template with all supported variables
│   │
│   ├── data/
│   │   └── app.db                     # SQLite user database (auto-created)
│   │
│   ├── models/
│   │   └── user.py                    # SQLAlchemy User model
│   │
│   ├── routers/
│   │   ├── auth.py                    # /api/auth/* — login, register, profile
│   │   ├── users.py                   # /api/users/* — admin user CRUD
│   │   ├── iflow.py                   # /api/iflow/* — iFlow generation & packaging
│   │   ├── mapping.py                 # /api/mapping/* — .mmap generation (18 endpoints)
│   │   ├── groovy.py                  # /api/groovy/* — Groovy script generation
│   │   ├── xslt.py                    # /api/xslt/* — XSLT generation
│   │   ├── chat.py                    # /api/chat/* — AI assistant
│   │   ├── documents.py               # /api/documents/* — doc generation
│   │   ├── cpi_connect.py             # /api/cpi/* — live CPI tenant (40+ endpoints)
│   │   └── settings.py                # /api/settings/* — AI provider hot-reload
│   │
│   ├── services/
│   │   ├── auth_service.py            # JWT encode/decode, bcrypt hashing
│   │   ├── claude_service.py          # AI provider abstraction (8 providers)
│   │   ├── mmap_builder.py            # .mmap XML builder — all 51 SAP CPI functions
│   │   ├── sheet_mapper.py            # Excel/CSV parser, rule parser, XPath resolver
│   │   ├── xsd_parser.py              # XSD field path extractor
│   │   ├── prebuilt_mapper.py         # Prebuilt mapping catalog management
│   │   ├── iflow_packager.py          # iFlow ZIP packaging
│   │   ├── doc_builder.py             # Word document builder
│   │   ├── doc_parser.py              # Document parser
│   │   ├── flowchart_builder.py       # Flow diagram builder
│   │   └── template_service.py        # Excel template generator
│   │
│   └── resources/
│       ├── cpi_mapping_cheatsheet.md  # AI reference: all 51 functions, context rules, ZIP format
│       ├── iflow_cheatsheet.md        # AI reference: iFlow patterns and adapter config
│       └── *.xsd                      # 50+ standard SAP OData and IDoc XSD schemas
│
├── frontend/
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       ├── api/
│       │   └── client.ts              # Axios API client — all API calls with JWT headers
│       ├── contexts/                  # React contexts (auth, etc.)
│       ├── components/
│       │   ├── Layout.tsx             # App shell with sidebar
│       │   ├── Sidebar.tsx            # Nav + AI provider chip + settings modal
│       │   ├── ProtectedRoute.tsx     # Redirects unauthenticated users to login
│       │   ├── MarkdownResult.tsx     # Renders AI markdown output
│       │   └── ResultPanel.tsx        # Generic result display panel
│       └── pages/
│           ├── Login.tsx              # JWT login form
│           ├── Dashboard.tsx          # Overview + status
│           ├── IFlowGenerator.tsx     # iFlow generation
│           ├── MessageMapping.tsx     # .mmap generation — all 3 modes
│           ├── GroovyGenerator.tsx    # Groovy scripts
│           ├── XSLTGenerator.tsx      # XSLT generation
│           ├── DocumentGenerator.tsx  # Integration docs
│           ├── ChatAssistant.tsx      # AI chat
│           ├── CPIConnect.tsx         # Live CPI tenant (all 4 tabs)
│           └── UserManagement.tsx     # Admin user CRUD
│
└── .github/
    └── workflows/
        └── deploy.yml                 # GitHub Pages auto-deploy on push to main
```

---

## Troubleshooting

### Fresh clone — app won't start at all
1. Verify Python is installed and in PATH: `py --version` (Windows) or `python3 --version`
2. Verify Node.js is installed and in PATH: `node --version` and `npm --version`
3. Make sure `backend/.env` exists — copy from `backend/.env.example` if not
4. Run `pip install -r backend/requirements.txt` manually to see any install errors
5. Run `npm install` inside the `frontend/` folder to see any install errors

### Cannot log in
- Default credentials: `admin@cpi.local` / `admin123`
- If the login page does not appear, the frontend is not running — check Terminal 2
- If login fails with "server error", the backend is not running — check Terminal 1 (port 8000)
- If you changed the password and forgot it: delete `backend/data/app.db` — recreated with default admin on next backend start

### Backend won't start
- Verify Python: `py --version` — must be 3.10 or higher
- Install dependencies: `cd backend && py -m pip install -r requirements.txt`
- Check `backend/.env` exists (copy from `.env.example` if missing)
- Check port 8000 is not in use by another process

### Frontend won't start
- Verify Node.js: `node --version` — must be 20 or higher
- Install dependencies: `cd frontend && npm install`
- Check port 5173 is not in use
- If you see `vite: not found` run `npm install` again inside `frontend/`

### AI generation returns errors
- **Groq 429:** Free tier rate limit hit. Wait a few seconds and retry, or switch to a smaller model
- **Anthropic 429/529:** API limit. Wait and retry
- **Ollama 503 — not running:** Run `ollama serve` in a separate terminal
- **Ollama 503 — model not found:** Run `ollama pull <model-name>` first

### Message Mapping — comma delimiter in SplitByValue
Wrap the comma in double quotes so it isn't treated as an argument separator:
```
SplitByValue((/msg/tags), ",")      ← correct
SplitByValue((/msg/tags), ,)        ← wrong — delimiter becomes empty
```

### CPI Connect shows "Not configured"
Open Connection Settings and enter your CPI tenant credentials, then click **Save & Connect**.

### CPI Connect shows "Connection failed"
- Verify `CPI_API_BASE_URL` ends with `/api/v1`
- Verify OAuth2 credentials are from a current, non-expired service key
- Ensure the service instance has the required roles (see above)
- For basic auth: verify the user has `PI_Integration_Developer` role

### Generated .mmap imports but some functions show red in CPI
- Ensure both source and target XSD field paths in the mapping rules exist in the uploaded XSDs
- For `fixValues` and `valuemap`: the function brick imports correctly but the key/value table must be configured in the CPI UI after import — this is by design (CPI stores the table separately from the mmap XML)
- For `useOneAsMany`: all 3 arguments are required (value, context parent, context field)

### Changing AI provider mid-session
Click the AI provider chip in the bottom-left sidebar → make your change → **Save & Apply**. The backend hot-reloads immediately — no restart needed.
