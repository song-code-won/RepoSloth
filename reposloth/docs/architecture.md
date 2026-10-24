# RepoSloth Architecture & Security Guide

## 1. Overview
RepoSloth is a 100% local, read-only AI codebase explanation tool. It parses repositories, extracts structural features, filters potential secrets and binary data, and queries locally hosted open-weight models (via Ollama) to assist software engineers in onboarding and understanding unfamiliar codebases.

## 2. Component Diagram

```mermaid
flowchart TD
    subgraph UI ["User Interface (Streamlit)"]
        A[Dashboard & Navigation]
        B[File Tree & Code Preview]
        C[Ask Your Codebase Chat]
        D[Mermaid Architecture Viewer]
    end

    subgraph Security ["Security & Sanitization Layer"]
        S1[Archive Validator: Zip-Slip & Bombs Defense]
        S2[Secret Filter: High-Entropy & Key Redaction]
        S3[Repository Scanner: Binary & Large File Filter]
    end

    subgraph Core ["Analysis & Retrieval Services"]
        R1[Language & Manifest Detector]
        R2[Context Retriever: TF-IDF & Line Indexer]
        R3[Architecture Builder: Import Graph Parser]
        R4[Report Generator: Markdown & Mermaid Exporter]
    end

    subgraph Inference ["Local AI Inference Layer"]
        O1[Ollama HTTP Client: localhost:11434]
        M1[Open-Weight Models: Qwen2.5-Coder / DeepSeek / Llama]
    end

    A --> S1
    A --> S3
    S3 --> S2
    S3 --> Core
    B --> S2
    C --> R2
    R2 --> O1
    O1 --> M1
    M1 --> Core
    Core --> D
    Core --> C
```

## 3. Data Flow
1. **Import:** User provides a local directory or uploads a ZIP file.
2. **Safety Validation:**
   - Archives are checked for traversal attempts (`../`) and decompression limits.
   - Credentials (`.env`, `*.pem`, `id_rsa`) are isolated.
   - Text contents are scanned for high-entropy tokens and redacted.
3. **Indexing:**
   - Manifests (`package.json`, `requirements.txt`, etc.) are parsed.
   - Code is sliced into windowed chunks with preserved line numbers.
4. **Local Prompting:**
   - Prompts enforce inert data rules: model is instructed to treat code as passive data, mitigating prompt injection.
   - Queries are routed to Ollama over localhost.

## 4. Threat Model & Safeguards
- **Arbitrary Code Execution:** RepoSloth strictly inspects files with standard I/O. It never invokes `exec()`, `eval()`, package managers (`pip install`, `npm install`), or shell hooks.
- **Data Exfiltration:** Operates entirely offline. No telemetry, third-party analytics, or external API endpoints.
- **Zip-Slip:** Sanitizes extracted paths using `Path.relative_to(dest_dir)` before file creation.
