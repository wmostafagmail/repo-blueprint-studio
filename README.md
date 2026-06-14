# Repo Blueprint Studio 📁✨

**Repo Blueprint Studio** is a full-stack local web application designed to reverse-engineer GitHub repositories into clean-room, self-contained rebuild specifications. The generated blueprints can be handed directly to other AI coding agents to recreate functionally similar software products from scratch without exposing any original source code, proprietary assets, or credentials.

---

## Key Features

- **Multi-Provider LLM Integration**: Abstraction interface supporting OpenAI/GPT, Google Gemini, Ollama Local, LM Studio Local, and generic OpenAI-compatible gateways.
- **Mock Provider Mode**: Execute and test the entire analysis pipeline instantly without any LLM API keys.
- **Robust Local Extraction**: Integrates the `universal-repo-rebuild-blueprint-extractor` repository inventory engine.
- **Credential Protection**: Redacts private keys, SSH keys, passwords, database credentials, and GitHub personal tokens from codebase inputs before sending to any LLM.
- **Real-Time Progress & Log Streaming**: Terminal console logging and live percentage tracking for cloning, scanning, chunking, and merging phases.
- **Markdown previewer**: View and audit compiled specifications inside the UI before downloading them.

---

## Repository Structure

```text
repo-blueprint-studio/
├── README.md                 # Project Documentation
├── backend/                  # FastAPI & SQLAlchemy SQLite Service
│   ├── requirements.txt      # Python libraries
│   ├── app/                  # Main backend codebase
│   └── tests/                # Automated pytest suite
├── macos-app/                # Electron shell that reuses the shared frontend/backend
└── frontend/                 # React & Vite SPA
    ├── package.json          # Node dependencies
    ├── index.html            # Core template shell
    └── src/                  # React source files
```

---

## Installation & Setup

### Prerequisites
- Git installed on your system.
- Node.js (version 18+) & npm.
- Python (version 3.11+).

---

### 1. Setting up the Backend

1. Navigate to the backend directory:
   ```bash
   cd backend
   ```
2. Initialize and activate a Python virtual environment:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Start the FastAPI development server:
   ```bash
   uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
   ```
   The API will be available at `http://127.0.0.1:8000`. Swagger docs are at `http://127.0.0.1:8000/docs`.

---

### 2. Setting up the Frontend

1. Navigate to the frontend directory:
   ```bash
   cd ../frontend
   ```
2. Install Node packages:
   ```bash
   npm install
   ```
3. Run the Vite React development server:
   ```bash
   npm run dev
   ```
   The web UI will be accessible at `http://localhost:3000`.

---

### 3. macOS Desktop Shell

The macOS app is a wrapper around the same `frontend/` and `backend/` code, so future changes should continue to be made in those shared folders and will automatically apply to both the web app and the macOS app.

1. Navigate to the macOS package:
   ```bash
   cd ../macos-app
   ```
2. Install Electron dependencies:
   ```bash
   npm install
   ```
3. In development, run the shared backend, shared frontend, and then start the macOS shell:
   ```bash
   npm run dev
   ```
4. To package the macOS app:
   ```bash
   npm run package
   ```

---

## Running Tests

To run automated checks for URL validation safety, name sanitization, secret redaction, and database API interactions, run:
```bash
# In the project root folder
PYTHONPATH=. backend/.venv/bin/pytest backend/tests/
```

---

## Configuring LLM Providers

Open the **Settings** panel in the Web UI to configure your selected provider:

### 1. Mock LLM Provider (Default)
- **Settings**: No keys or parameters required.
- **Best For**: Rapid local testing and validating UI/UX flows.

### 2. OpenAI / GPT
- **Provider**: `openai`
- **Model**: `gpt-4o` or similar.
- **API Key**: `sk-proj-...`
- **Base URL**: `https://api.openai.com/v1` (Optional)

### 3. Google Gemini
- **Provider**: `gemini`
- **Model**: `gemini-1.5-flash` or `gemini-1.5-pro`
- **API Key**: Google AI Studio key.

### 4. Ollama Local (Offline)
- **Provider**: `ollama`
- **Model**: `llama3`, `mistral`, or any local model tag.
- **Base URL**: `http://localhost:11434` (Ollama daemon endpoint).

### 5. LM Studio Local (Offline)
- **Provider**: `lmstudio`
- **Model**: The model currently loaded in your LM Studio instance.
- **Base URL**: `http://localhost:1234/v1`
- **API Key**: `lm-studio` (Optional)

---

## Step-by-Step Usage

### Analyzing a Public Repository
1. Open the UI at `http://localhost:3000`.
2. Enter a public GitHub URL in the input field: `https://github.com/django/django`.
3. Click **Start Repository Analysis**.
4. Monitor cloning and generation steps in the **Log Console**.
5. Once completed, review the blueprint with **Preview Blueprint** or click **Download Blueprint** to save the markdown.

### Analyzing a Private Repository
1. Generate a **Personal Access Token** (classic or fine-grained) in your GitHub Account.
2. In the Home Screen, enter the private repository URL.
3. Paste the token into the **Personal Access Token** field (or save it in Settings).
4. Click **Start Repository Analysis**. The token is encrypted/masked inside logs and SQLite storage.

---

## Security & Clean-Room Boundaries

1. **No Code Execution**: Cloned code repositories are never compiled, run, or evaluated. Setup is 100% static analysis.
2. **Automatic Deletion**: Cloned files are cleaned from the workspace directory immediately after generation (unless `Keep cloned workspace repositories` is explicitly checked in Settings).
3. **Secret Scrubbing**: Source code modules are run through regex filters to replace credentials, JWT tokens, AWS keys, and connection strings with `[REDACTED_SECRET]` before passing them to LLM APIs.
4. **Local Sovereignty**: Sensitive or proprietary software blueprints should always be generated using **Ollama** or **LM Studio** local endpoints to ensure code is never sent to third-party cloud APIs.
