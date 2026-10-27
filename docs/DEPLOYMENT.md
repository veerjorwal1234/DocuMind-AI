# DocuMind AI: Deployment, Docker, Security & Testing Guide

> **Module Reference**: Operational Readiness, Containerization, Data Governance & Verification  
> **Source Files**: [`Dockerfile`](file:///c:/Users/Mahan/Downloads/DocuMind_ai-main/DocuMind_ai-main/Dockerfile), [`.dockerignore`](file:///c:/Users/Mahan/Downloads/DocuMind_ai-main/DocuMind_ai-main/.dockerignore), [`requirements.txt`](file:///c:/Users/Mahan/Downloads/DocuMind_ai-main/DocuMind_ai-main/requirements.txt), [`.github/workflows/python-tests.yml`](file:///c:/Users/Mahan/Downloads/DocuMind_ai-main/DocuMind_ai-main/.github/workflows/python-tests.yml), [`tests/`](file:///c:/Users/Mahan/Downloads/DocuMind_ai-main/DocuMind_ai-main/tests)  

---

## 1. Local Environment Setup & Execution

### 1.1 Prerequisites
- **Operating System**: Windows 10/11, macOS, or modern Linux (Ubuntu 20.04+ recommended)
- **Python Runtime**: Python `3.10` or `3.11` (Python 3.11 recommended)
- **Git**: Installed and on system PATH
- **API Credentials**: At least one free API key from [Google AI Studio](https://aistudio.google.com/app/apikey) or [Groq Console](https://console.groq.com/keys) (OpenAI also supported)

### 1.2 Step-by-Step Installation

#### 1. Navigate to Project Directory
```bash
cd DocuMind_ai-main
```

#### 2. Create and Activate Virtual Environment
**On Windows (PowerShell):**
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```
*(If PowerShell restricts script execution, run: `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`)*

**On Linux / macOS:**
```bash
python3 -m venv venv
source venv/bin/activate
```

#### 3. Install Application Dependencies
```bash
# Upgrade package installer
python -m pip install --upgrade pip

# Install core production dependencies
pip install -r requirements.txt

# Install development and testing dependencies (optional)
pip install -r requirements-dev.txt
```

#### 4. Configure Environment Variables
Create a local `.env` file from the provided template:
```bash
# On Linux/macOS:
cp .env.example .env

# On Windows PowerShell:
Copy-Item .env.example .env
```
Open `.env` in a text editor and add your preferred API key (keys can also be provided directly via the UI sidebar at runtime):
```ini
# OpenAI Key (Optional)
OPENAI_API_KEY=your_openai_key_here

# Google Gemini Free Key (Recommended)
GEMINI_API_KEY=your_gemini_key_here

# Groq Free Key (Optional)
GROQ_API_KEY=your_groq_key_here

# OpenRouter Free Key (Optional)
OPENROUTER_API_KEY=your_openrouter_key_here
```

#### 5. Launch the Streamlit Application
```bash
streamlit run app.py
```
The application will automatically start and open in your default browser at:
`http://localhost:8501`

---

## 2. Docker Containerization Architecture

DocuMind AI includes a production-ready, multi-stage, CPU-optimized [`Dockerfile`](file:///c:/Users/Mahan/Downloads/DocuMind_ai-main/DocuMind_ai-main/Dockerfile) designed for minimal image footprint and fast startup times.

### 2.1 Dockerfile Analysis

```dockerfile
# DocuMind AI - Production Dockerfile
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    STREAMLIT_SERVER_PORT=8501 \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0 \
    STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Install PyTorch CPU first to avoid heavy CUDA wheels
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

# Copy requirements and install (stripping out windows-only winocr)
COPY requirements.txt .
RUN grep -v -i "winocr" requirements.txt > requirements.linux.txt && \
    pip install --no-cache-dir -r requirements.linux.txt

# Copy application source code
COPY . .

# Expose Streamlit port
EXPOSE 8501

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

# Launch Streamlit
ENTRYPOINT ["streamlit", "run", "app.py"]
```

### 2.2 Critical Docker Engineering Decisions

1. **Base Image (`python:3.11-slim`)**: Uses Debian slim instead of Alpine to ensure compatibility with compiled C-extensions in FAISS, PyTorch, and SentenceTransformers while maintaining a compact image size.
2. **OpenMP Runtime (`libgomp1`)**: Required by FAISS for multi-threaded CPU parallel vector indexing.
3. **PyTorch CPU Wheel Optimization**: The standard `pip install torch` command downloads CUDA GPU binaries exceeding 2.5 GB. The Dockerfile overrides this with `--index-url https://download.pytorch.org/whl/cpu`, reducing image size by over 70%.
4. **Cross-Platform OCR Filter**: On line 27 of the Dockerfile:
   ```bash
   grep -v -i "winocr" requirements.txt > requirements.linux.txt
   ```
   Because `winocr` depends on Windows Runtime C# bindings, it cannot install on Linux. The Dockerfile filters it out dynamically before installing dependencies. Inside the container, OCR operations fall back to native PDFium extraction or `pytesseract`.
5. **Streamlit Production Flags**: Enforces `STREAMLIT_SERVER_HEADLESS=true`, `STREAMLIT_SERVER_ADDRESS=0.0.0.0`, and disables telemetry (`STREAMLIT_BROWSER_GATHER_USAGE_STATS=false`).
6. **Container Healthcheck**: Uses Streamlit's internal health check endpoint (`/_stcore/health`) to enable container orchestrator monitoring (e.g., Docker Swarm, Kubernetes).

### 2.3 Docker Build & Execution Commands

#### Build the Docker Image
```bash
docker build -t documind-ai:latest .
```

#### Run Container Locally
```bash
docker run -d \
  --name documind-container \
  -p 8501:8501 \
  --env-file .env \
  documind-ai:latest
```

#### Run Container with Direct Environment Variables
```bash
docker run -d \
  --name documind-container \
  -p 8501:8501 \
  -e GEMINI_API_KEY="your-gemini-key-here" \
  documind-ai:latest
```

#### Monitor Container Health and Logs
```bash
# View active container status
docker ps

# Stream application logs
docker logs -f documind-container

# Verify health status
docker inspect --format='{{json .State.Health}}' documind-container
```

#### Stop and Clean Up
```bash
docker stop documind-container
docker rm documind-container
```

### 2.4 Cloud Deployment Considerations
- **Current Container State**: The Docker container packages the Streamlit interface and application logic.
- **Production Requirements for Public Deployment**:
  1. **Reverse Proxy / SSL**: Place Nginx, Traefik, or Cloudflare in front of port `8501` to provide TLS/HTTPS encryption and WebSockets proxying.
  2. **Memory Allocation**: SentenceTransformers model (`all-MiniLM-L6-v2`) and PyTorch require at least 1.5 GB to 2 GB of RAM per container instance under active indexing.
  3. **Process Isolation**: Streamlit is primarily designed for stateful single-node applications; scaling horizontally across multiple container instances requires sticky sessions or migrating vector state to a standalone database.

---

## 3. Security, Privacy & Data Handling Analysis

| Data Vector | Operational Path | Persistence & Protection Mechanism | Risk / Threat Boundary |
| :--- | :--- | :--- | :--- |
| **Uploaded Documents** | Client $\rightarrow$ Streamlit memory buffer $\rightarrow$ `tempfile.NamedTemporaryFile` | Saved to local temp directory during parsing, then deleted immediately via `os.unlink(tmp_path)` in a `finally:` block. | If the host process is forcefully terminated (`SIGKILL`) during parsing, temp files could remain until OS cleanup. |
| **Raw File Previews** | Document bytes stored in `st.session_state.raw_docs` | Stored exclusively in volatile server RAM for the active session. Destroyed when the browser tab is closed or "Reset Knowledge Base" is clicked. | Memory consumption scales with uploaded document size (~50–100 MB per large PDF). |
| **Indexed Vector Embeddings** | Converted by `all-MiniLM-L6-v2` $\rightarrow$ stored in `faiss.IndexFlatL2` | Retained only in host RAM within `st.session_state.vector_store`. Never persisted to disk. | Vector representations cannot be queried across different user sessions or server restarts. |
| **API Keys & Secrets** | Loaded via `.env` or pasted into password-masked Streamlit text input | Excluded from git via `.gitignore` and `.dockerignore`. Keys are never logged or exposed in the UI. | Keys in `.env` exist as plaintext on the host filesystem and must be protected with appropriate file permissions. |
| **External LLM Traffic** | Assembled prompt sent via HTTPS to Google Gemini / Groq / OpenRouter / OpenAI | TLS 1.3 encrypted REST transmission. Prompts include only retrieved excerpts, never the full document. | Third-party LLM providers process the retrieved excerpts according to their respective data privacy and retention policies. |

---

## 4. Error Handling & System Resilience

DocuMind AI implements structured exception handling across its core pipelines:

1. **Corrupted or Malformed PDFs**: In [`document_processor.py:L160-L182`](file:///c:/Users/Mahan/Downloads/DocuMind_ai-main/DocuMind_ai-main/document_processor.py#L160-L182), if `pypdf.PyPDFLoader` encounters malformed syntax, the loader catches the exception and falls back to `pypdfium2.PdfDocument` to extract readable pages.
2. **Scanned / Low-Contrast Pages**: When a page contains fewer than 30 alphanumeric characters or is dominated by font glyph errors (`(cid:xxx)`), the system automatically renders the page at 2.0x scale and applies OCR.
3. **Missing OCR Engines**: If neither `winocr` nor `pytesseract` is available, the pipeline avoids crashing; it tags the page as `"(No readable text detected on this page)"` with method `"native_unclear"`.
4. **Transient LLM Failures (HTTP 503 / 429 / 404)**: In [`rag.py:L215-L225`](file:///c:/Users/Mahan/Downloads/DocuMind_ai-main/DocuMind_ai-main/rag.py#L215-L225), when an upstream provider experiences peak traffic or rate limits, the system catches the error and cascades across alternate candidate models (e.g., `gemini-2.0-flash` $\rightarrow$ `gemini-2.5-flash-lite`).
5. **Quota Exhaustion**: If an account has no remaining credits, the system catches the error and provides instructions to switch to free providers:
   > *"⚠️ Quota Exceeded: Your account has no remaining credits. Switch to 'Google Gemini (Free)' or 'Groq (Free)' in the sidebar for completely free usage without paying!"*
6. **Empty Retrieval State**: If a user queries the system before uploading documents or with an empty index, the system returns a clear prompt:
   > *"No relevant information found. Please try a different question or upload documents."*

---

## 5. Testing & Code Quality Assurance

### 5.1 Verified Automated Test Suite
The repository includes a comprehensive unit and integration test suite located in [`tests/`](file:///c:/Users/Mahan/Downloads/DocuMind_ai-main/DocuMind_ai-main/tests), utilizing `pytest`, `pytest-mock`, and custom fixtures in [`conftest.py`](file:///c:/Users/Mahan/Downloads/DocuMind_ai-main/DocuMind_ai-main/conftest.py).

#### Test Verification Summary (19 / 19 Tests Passing)
```text
tests/test_app.py:
  ✓ test_process_document           - Verifies temp file creation, chunking, state update, and disk cleanup
  ✓ test_clear_documents            - Verifies session state reset and vector store reinitialization

tests/test_document_processor.py:
  ✓ test_init                       - Verifies initialization parameters and text splitter setup
  ✓ test_load_pdf                   - Verifies PyPDFLoader integration and metadata enrichment
  ✓ test_load_pdf_file_not_found    - Verifies FileNotFoundError handling
  ✓ test_chunk_documents            - Verifies recursive character chunking and metadata preservation
  ✓ test_process_document           - Verifies end-to-end ingestion and chunking pipeline

tests/test_rag.py:
  ✓ test_init                       - Verifies vector store attachment and ChatOpenAI initialization
  ✓ test_generate_answer_no_docs    - Verifies fallback response when similarity search returns empty
  ✓ test_generate_answer            - Verifies prompt construction, context formatting, and LLM invocation
  ✓ test_dotenv_loaded              - Verifies environment configuration loading

tests/test_vector_store.py:
  ✓ test_init                       - Verifies SentenceTransformer model loading and 384-d FAISS index
  ✓ test_add_documents_empty        - Verifies no-op handling for empty document lists
  ✓ test_add_documents              - Verifies vector encoding, index population, and float32 casting
  ✓ test_similarity_search_empty    - Verifies empty list return on unindexed search
  ✓ test_similarity_search          - Verifies query encoding, top-k ranking, and document retrieval
  ✓ test_save_index                 - Verifies FAISS binary index serialization (faiss.write_index)
  ✓ test_load_index                 - Verifies FAISS binary index deserialization (faiss.read_index)
  ✓ test_load_index_not_exists      - Verifies index preservation when loading non-existent path
```

### 5.2 Running Tests Locally
```bash
# Execute full test suite
pytest

# Execute with verbose output and test names
pytest -v

# Run with test coverage analysis
pytest --cov=. --cov-report=term-missing
```

### 5.3 Continuous Integration (GitHub Actions)
The repository contains a continuous integration workflow configured in [`.github/workflows/python-tests.yml`](file:///c:/Users/Mahan/Downloads/DocuMind_ai-main/DocuMind_ai-main/.github/workflows/python-tests.yml):
- Executes on every `push` and `pull_request` targeting the `main` branch.
- Runs on Ubuntu (`ubuntu-latest`) with Python 3.9/3.11.
- Performs syntax linting with `flake8`.
- Executes static type analysis with `mypy --ignore-missing-imports .`.
- Runs `pytest --cov=.` and uploads coverage reports to Codecov.

---

*Continue to detailed technical guides:*
- [Comprehensive Project Description](file:///c:/Users/Mahan/Downloads/DocuMind_ai-main/DocuMind_ai-main/docs/PROJECT_DESCRIPTION.md)
- [System Architecture & Component Interactions](file:///c:/Users/Mahan/Downloads/DocuMind_ai-main/DocuMind_ai-main/docs/ARCHITECTURE.md)
- [Technical Workflow & RAG Internals](file:///c:/Users/Mahan/Downloads/DocuMind_ai-main/DocuMind_ai-main/docs/TECHNICAL_WORKFLOW.md)
- [Interview & Viva Voce Preparation Guide](file:///c:/Users/Mahan/Downloads/DocuMind_ai-main/DocuMind_ai-main/docs/INTERVIEW_PREPARATION.md)
