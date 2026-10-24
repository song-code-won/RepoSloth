# RepoSloth Demo Script & Final Submission Checklist

## 1. Demo Walkthrough Script (3-Minute Presentation)

### Step 1: Launch & Local Connection Check
- **Action**: Open terminal, run `streamlit run reposloth/app.py`.
- **Narrative**: *"Welcome to RepoSloth, built for Hacktoberfest Week 3 'Slow and Steady'. In the sidebar, we immediately see our connection to the local Ollama daemon. No cloud APIs, no external fees, 100% private."*

### Step 2: Safe Ingestion & Secret Redaction
- **Action**: Point the scanner to `./sample_repo` or upload a repository ZIP.
- **Narrative**: *"RepoSloth instantly scans the repository. Notice how it filters out node_modules, build artifacts, and dangerous credentials. It performs zip-slip validation on uploaded archives and treats all code as inert data."*

### Step 3: Grounded Repository Overview
- **Action**: Open the **Overview** tab and click **Generate AI Codebase Overview**.
- **Narrative**: *"Our open-weight model (Qwen 2.5 Coder) synthesizes the application's purpose, detects frameworks like FastAPI from requirements.txt, identifies candidate entry points, and extracts setup instructions."*

### Step 4: File & Function Deep-Dive
- **Action**: Switch to **File & Function Explainer**, select `auth.py`, and click **Explain File**.
- **Narrative**: *"RepoSloth breaks down functions, parameters, return types, and flags security notes or edge cases. Users can export this directly to Markdown."*

### Step 5: Grounded Codebase Q&A
- **Action**: Click on **Ask Your Codebase**, press the preset **'🔐 How does auth work?'**.
- **Narrative**: *"RepoSloth uses local windowed chunking and TF-IDF relevance scoring to retrieve the exact lines from auth.py (Lines 1-17), providing a grounded answer with precise line citations."*

### Step 6: Architecture & Export
- **Action**: Switch to **Architecture Explorer** to show the directory tree and Mermaid diagram, then open **Export Reports** to download the analysis report.
- **Narrative**: *"Developers can download full Markdown reports or Mermaid architecture graphs to share with their team."*

---

## 2. Final Submission Checklist

- [x] **Complete Working Code**: Full modular application in `reposloth/` with UI in `app.py`.
- [x] **Open-Weight AI Integration**: Local inference via Ollama supporting Qwen 2.5 Coder, DeepSeek Coder, CodeLlama.
- [x] **Security Safeguards**:
  - [x] Zip-slip directory traversal defense.
  - [x] File size and decompression limits.
  - [x] Secret & credential redaction (`.env`, tokens, private keys).
  - [x] Prompt injection prevention (inert data framing).
  - [x] Zero-execution policy (never runs repository code).
- [x] **Automated Test Suite**: 14 passing pytest unit tests across all services (`reposloth/tests`).
- [x] **Mermaid Diagrams**: Dynamic architecture generation and documentation diagrams.
- [x] **Documentation**: GitHub-ready `README.md`, `LICENSE` (MIT), and `architecture.md`.
- [x] **DEV Community Article**: Comprehensive submission draft in `docs/dev_article_draft.md`.
- [x] **Demo Repository**: Included sample project in `sample_repo/` for instant evaluation.
