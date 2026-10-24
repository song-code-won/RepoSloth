"""RepoSloth — Local AI Codebase Explainer
Streamlit Web Application
"""

from __future__ import annotations
import os
import sys
import shutil
import tempfile
from pathlib import Path

# Ensure root of repo is in path
CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR.parent) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR.parent))

import streamlit as st

from reposloth.services.repository_scanner import RepositoryScanner
from reposloth.services.archive_validator import ArchiveValidator
from reposloth.services.ollama_client import OllamaClient, RECOMMENDED_MODELS
from reposloth.services.code_explainer import CodeExplainer
from reposloth.services.context_retriever import ContextRetriever
from reposloth.services.architecture_builder import ArchitectureBuilder
from reposloth.services.report_generator import ReportGenerator
from reposloth.services.language_detector import LanguageDetector
from reposloth.services.secret_filter import SecretFilter

# Page configuration
st.set_page_config(
    page_title="RepoSloth — Local AI Codebase Explainer",
    page_icon="🦥",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom Styling
st.markdown("""
<style>
    .main-title {
        font-size: 2.3rem;
        font-weight: 800;
        color: #1e293b;
        margin-bottom: 0px;
    }
    .sub-title {
        font-size: 1.05rem;
        color: #64748b;
        margin-top: 0px;
        margin-bottom: 20px;
    }
    .status-card {
        background-color: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 16px;
        margin-bottom: 16px;
    }
    .metric-badge {
        display: inline-block;
        padding: 4px 10px;
        border-radius: 12px;
        font-weight: 600;
        font-size: 0.85rem;
    }
</style>
""", unsafe_allow_html=True)


# Session state initialization
if "ollama_host" not in st.session_state:
    st.session_state["ollama_host"] = "http://localhost:11434"
if "scanned_repo" not in st.session_state:
    st.session_state["scanned_repo"] = None
if "ai_overview" not in st.session_state:
    st.session_state["ai_overview"] = ""
if "retriever" not in st.session_state:
    st.session_state["retriever"] = None
if "chat_history" not in st.session_state:
    st.session_state["chat_history"] = []
if "temp_extracted_dir" not in st.session_state:
    st.session_state["temp_extracted_dir"] = None


# Sidebar: Connection & Repository Selection
with st.sidebar:
    st.image("https://api.iconify.design/lucide:shield-check.svg?color=%232563eb", width=42)
    st.markdown("### 🦥 RepoSloth Engine")
    st.caption("**Let AI explore the code while you take it slow.**")

    # Ollama Daemon Connection Section
    st.markdown("#### 1. Local AI Engine")
    host_input = st.text_input("Ollama Host URL", value=st.session_state["ollama_host"])
    ollama_client = OllamaClient(host=host_input)
    conn_info = ollama_client.check_connection()

    if conn_info["connected"]:
        st.success("🟢 Ollama Connected Locally")
        available_models = conn_info["models"]
        if not available_models:
            st.warning("No models found in Ollama. Pull a model via `ollama run qwen2.5-coder:7b`.")
            selected_model = "qwen2.5-coder:7b"
        else:
            selected_model = st.selectbox(
                "Active Open-Weight Model",
                options=available_models,
                index=0
            )
    else:
        st.error("🔴 Ollama Offline / Not Reachable")
        st.caption(conn_info["error"])
        selected_model = "qwen2.5-coder:7b"
        with st.expander("🛠️ Setup & Pull Guide"):
            st.markdown("""
            1. Install [Ollama](https://ollama.com).
            2. Run: `ollama run qwen2.5-coder:7b` (or `1.5b` for low RAM).
            3. Verify: `ollama list`.
            """)

    st.divider()

    # Repository Import Source
    st.markdown("#### 2. Select Repository")
    import_mode = st.radio("Import Method", ["Local Directory", "Upload ZIP Archive"], horizontal=True)

    target_repo_path = None

    if import_mode == "Local Directory":
        dir_input = st.text_input(
            "Repository Path",
            value="",
            placeholder="e.g. C:/Users/.../MyProject or ./sample_repo"
        )
        if st.button("🔍 Scan Local Folder", use_container_width=True):
            if dir_input and Path(dir_input).is_dir():
                target_repo_path = Path(dir_input).resolve()
            else:
                st.error("Please enter a valid, existing directory path.")
    else:
        uploaded_zip = st.file_uploader("Upload .ZIP Archive", type=["zip"])
        if uploaded_zip is not None and st.button("📦 Unpack & Scan ZIP", use_container_width=True):
            # Safe temporary directory extraction
            temp_dir = Path(tempfile.mkdtemp(prefix="reposloth_extracted_"))
            st.session_state["temp_extracted_dir"] = temp_dir
            success, msg, files = ArchiveValidator.validate_and_extract(uploaded_zip, temp_dir)
            if success:
                st.success(msg)
                target_repo_path = temp_dir
            else:
                st.error(msg)

    # Perform scan if path established
    if target_repo_path:
        with st.spinner("Scanning directory, filtering binaries & secrets..."):
            scanner = RepositoryScanner(target_repo_path)
            scan_res = scanner.scan()
            if "error" in scan_res:
                st.error(scan_res["error"])
            else:
                st.session_state["scanned_repo"] = scan_res
                st.session_state["ai_overview"] = ""  # Reset overview
                st.session_state["chat_history"] = []
                # Initialize Context Retriever
                st.session_state["retriever"] = ContextRetriever(
                    scan_res["repo_path"],
                    scan_res["file_list"]
                )
                st.rerun()

    st.divider()
    st.caption("🔒 **Security & Privacy Guarantee**\n- 100% Local Inference (Ollama)\n- No external telemetry\n- Code is treated as inert data")


# Main Page Header
st.markdown('<div class="main-title">🦥 RepoSloth</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Local AI Codebase Explainer — Explore any repository with open-weight intelligence while you take it slow.</div>', unsafe_allow_html=True)

scan_data = st.session_state.get("scanned_repo")

if not scan_data:
    # Empty State Guide
    st.info("👋 **Welcome to RepoSloth!** To get started, select a local folder or upload a ZIP archive in the left sidebar.")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("### 1. 🛡️ Safe & Read-Only")
        st.write("Never executes code, rejects zip-slips, and redacts API keys, secrets, and environment tokens.")
    with col2:
        st.markdown("### 2. 🧠 Open-Weight AI")
        st.write("Grounded in local models like **Qwen 2.5 Coder** via Ollama. 100% offline, zero cloud API fees.")
    with col3:
        st.markdown("### 3. 🎯 Deep Explanations")
        st.write("Explains architecture, candidate entry points, modules, and answers questions with direct line numbers.")

    # Recommended Models Table
    st.markdown("---")
    st.markdown("### Recommended Open-Weight Models for RepoSloth")
    model_rows = []
    for m in RECOMMENDED_MODELS:
        model_rows.append({
            "Model Name": m["name"],
            "Identifier": f"`{m['id']}`",
            "Hardware Required": m["ram_required"],
            "License": m["license"],
            "Best For": m["description"]
        })
    st.table(model_rows)

else:
    # High-level Metrics Row
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Repository", scan_data.get("repo_name", "Unknown"))
    m2.metric("Analyzed Files", scan_data.get("total_files", 0))
    m3.metric("Total Lines", f"{scan_data.get('total_lines', 0):,}")
    m4.metric("Sensitive Skipped", len(scan_data.get("skipped_secret_files", [])))
    m5.metric("Binaries Excluded", scan_data.get("skipped_binary_count", 0))

    # Core Navigation Tabs
    tab_overview, tab_file_explainer, tab_qa, tab_arch, tab_doc, tab_insights, tab_export = st.tabs([
        "📋 Overview",
        "🔍 File & Function Explainer",
        "💬 Ask Your Codebase",
        "🗺️ Architecture Explorer",
        "📝 Documentation Assistant",
        "⚠️ Complexity & Hygiene",
        "💾 Export Reports"
    ])

    explainer = CodeExplainer(ollama_client)

    # TAB 1: OVERVIEW
    with tab_overview:
        st.markdown("### 📋 Repository Overview & AI Synthesis")
        c1, c2 = st.columns([1, 1])

        with c1:
            st.markdown("#### 📊 Grounded Evidence (Observed Directly)")
            st.write(f"**Path:** `{scan_data['repo_path']}`")
            
            # Languages
            st.write("**Language Distribution:**")
            for lang, stats in scan_data.get("language_stats", {}).items():
                st.write(f"- `{lang}`: {stats['files']} files ({stats['lines']:,} lines)")

            # Entry points
            st.write("**Candidate Entrypoints:**")
            eps = scan_data.get("entrypoint_candidates", [])
            if eps:
                for ep in eps:
                    st.write(f"- 🚀 `{ep}`")
            else:
                st.caption("No standard entrypoints found (e.g. main.py, index.js).")

            # Manifests
            st.write("**Detected Manifests & Dependencies:**")
            mans = scan_data.get("manifests", {})
            if mans:
                for mname, mval in mans.items():
                    if isinstance(mval, list):
                        st.write(f"- **{mname}**: {', '.join(mval[:8])}...")
                    else:
                        st.write(f"- **{mname}**: {mval}")
            else:
                st.caption("No standard package manifests detected.")

        with c2:
            st.markdown("#### 🧠 AI-Powered Synthesis")
            if not conn_info["connected"]:
                st.warning("⚠️ Connect Ollama in the sidebar to generate AI synthesis.")
            else:
                if st.button("✨ Generate AI Codebase Overview", key="btn_gen_overview"):
                    with st.spinner(f"Analyzing repository structure using {selected_model}..."):
                        res = explainer.explain_repository(scan_data, model=selected_model)
                        if res["success"]:
                            st.session_state["ai_overview"] = res["response"]
                        else:
                            st.error(res["error"])

            if st.session_state["ai_overview"]:
                st.markdown(st.session_state["ai_overview"])
            else:
                st.info("Click 'Generate AI Codebase Overview' to synthesize purpose, architecture, and run instructions.")

    # TAB 2: FILE & FUNCTION EXPLAINER
    with tab_file_explainer:
        st.markdown("### 🔍 File & Function Explainer")
        files = scan_data.get("file_list", [])
        if not files:
            st.warning("No inspectable files in this repository.")
        else:
            col_sel, col_btn = st.columns([3, 1])
            with col_sel:
                selected_file = st.selectbox("Select file to examine:", options=files)
            with col_btn:
                st.write("")
                st.write("")
                explain_btn = st.button("🔬 Explain File", use_container_width=True)

            f_col1, f_col2 = st.columns([1, 1])

            with f_col1:
                st.markdown(f"#### 📄 Source Preview: `{selected_file}`")
                abs_fpath = Path(scan_data["repo_path"]) / selected_file
                try:
                    raw_content = abs_fpath.read_text(encoding="utf-8", errors="ignore")
                    sanitized_content, red_count = SecretFilter.sanitize_text(raw_content)
                    if red_count > 0:
                        st.caption(f"🔒 {red_count} sensitive tokens redacted from preview.")
                    lang_name = LanguageDetector.detect_language(abs_fpath).lower()
                    st.code(sanitized_content, language=lang_name if "python" in lang_name else "text", line_numbers=True)
                except Exception as e:
                    st.error(f"Could not load file: {e}")

            with f_col2:
                st.markdown("#### 🤖 AI Analysis & Architecture Role")
                if explain_btn:
                    if not conn_info["connected"]:
                        st.error("Ollama is not running. Please start Ollama to enable AI explanation.")
                    else:
                        with st.spinner(f"Explaining {selected_file} with {selected_model}..."):
                            f_res = explainer.explain_file(Path(scan_data["repo_path"]), selected_file, model=selected_model)
                            if f_res["success"]:
                                st.session_state[f"expl_{selected_file}"] = f_res["response"]
                            else:
                                st.error(f_res["error"])

                stored_expl = st.session_state.get(f"expl_{selected_file}")
                if stored_expl:
                    st.markdown(stored_expl)
                    # Single file export
                    st.download_button(
                        label="⬇️ Download Explanation as Markdown",
                        data=ReportGenerator.generate_file_explanation_report(selected_file, stored_expl),
                        file_name=f"RepoSloth_{Path(selected_file).name}_Explanation.md",
                        mime="text/markdown"
                    )
                else:
                    st.caption("Select a file and click 'Explain File' to see its summary, methods, and edge cases.")

    # TAB 3: ASK YOUR CODEBASE (Q&A)
    with tab_qa:
        st.markdown("### 💬 Ask Your Codebase (Grounded Q&A)")
        st.caption("Answers are strictly derived from source files. File paths and line numbers are cited.")

        # Preset Questions
        preset_cols = st.columns(4)
        selected_preset = None
        if preset_cols[0].button("🚀 Where does it start?"):
            selected_preset = "Where does the application execution start and what is the main entry point?"
        if preset_cols[1].button("🔐 How does auth work?"):
            selected_preset = "How does authentication or authorization work in this repository?"
        if preset_cols[2].button("🗄️ Database connections?"):
            selected_preset = "Which file handles database connections or data persistence?"
        if preset_cols[3].button("➕ Where to add API endpoint?"):
            selected_preset = "Where should I add a new API endpoint or route in this codebase?"

        user_query = st.chat_input("Ask a question about this repository...")
        query_to_run = user_query or selected_preset

        # Render chat history
        for msg in st.session_state["chat_history"]:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
                if "snippets" in msg and msg["snippets"]:
                    with st.expander("🔎 View Grounded Source References"):
                        for snip in msg["snippets"]:
                            st.markdown(f"**`{snip['file']}` (Lines {snip['start_line']} - {snip['end_line']})** — Score: `{snip['score']}`")
                            st.code(snip["text"], line_numbers=True)

        if query_to_run:
            # Append user message
            st.session_state["chat_history"].append({"role": "user", "content": query_to_run})
            with st.chat_message("user"):
                st.markdown(query_to_run)

            with st.chat_message("assistant"):
                with st.spinner("Searching repository chunks and reasoning with local model..."):
                    retriever: ContextRetriever = st.session_state["retriever"]
                    snippets = retriever.retrieve(query_to_run, top_k=4) if retriever else []

                    if not conn_info["connected"]:
                        reply = "⚠️ Ollama daemon is offline. Here are the matching code snippets retrieved based on your query:"
                        st.markdown(reply)
                    else:
                        ans_res = explainer.answer_question(
                            repo_name=scan_data["repo_name"],
                            question=query_to_run,
                            retrieved_snippets=snippets,
                            model=selected_model
                        )
                        reply = ans_res["response"] if ans_res["success"] else f"Error: {ans_res['error']}"
                        st.markdown(reply)

                    if snippets:
                        with st.expander("🔎 Grounded Source Snippets"):
                            for snip in snippets:
                                st.markdown(f"**`{snip['file']}` (Lines {snip['start_line']} - {snip['end_line']})**")
                                st.code(snip["text"], line_numbers=True)

                    st.session_state["chat_history"].append({
                        "role": "assistant",
                        "content": reply,
                        "snippets": snippets
                    })

    # TAB 4: ARCHITECTURE EXPLORER
    with tab_arch:
        st.markdown("### 🗺️ Visual Architecture & Module Tree")
        arch_col1, arch_col2 = st.columns([1, 1])

        with arch_col1:
            st.markdown("#### 🌳 Directory Tree Structure")
            tree_text = ArchitectureBuilder.build_tree_text(scan_data.get("file_list", []), max_depth=3)
            st.code(tree_text, language="text")

        with arch_col2:
            st.markdown("#### 📐 Grounded Mermaid Architecture Diagram")
            st.caption("Generated solely from observed entry points and verified module imports.")
            mermaid_code = ArchitectureBuilder.generate_mermaid_diagram(scan_data)
            st.markdown(mermaid_code)
            with st.expander("View Raw Mermaid Code"):
                st.code(mermaid_code, language="mermaid")

    # TAB 5: DOCUMENTATION ASSISTANT
    with tab_doc:
        st.markdown("### 📝 Documentation Assistant")
        st.caption("Draft API reference, docstrings, and README updates without modifying original source files.")
        
        doc_file = st.selectbox("Select module to document:", options=scan_data.get("file_list", []), key="doc_file_sel")
        if st.button("✍️ Generate Module Documentation", key="btn_gen_doc"):
            if not conn_info["connected"]:
                st.error("Ollama is not running. Please start Ollama to generate documentation.")
            else:
                with st.spinner(f"Drafting documentation for {doc_file}..."):
                    d_res = explainer.generate_documentation(
                        Path(scan_data["repo_path"]),
                        doc_file,
                        model=selected_model
                    )
                    if d_res["success"]:
                        st.session_state[f"doc_{doc_file}"] = d_res["response"]
                    else:
                        st.error(d_res["error"])

        saved_doc = st.session_state.get(f"doc_{doc_file}")
        if saved_doc:
            st.markdown(saved_doc)
            st.download_button(
                label="⬇️ Download Generated Markdown",
                data=saved_doc,
                file_name=f"{Path(doc_file).stem}_docs.md",
                mime="text/markdown"
            )

    # TAB 6: COMPLEXITY & HYGIENE
    with tab_insights:
        st.markdown("### ⚠️ Complexity & Code Hygiene Insights")
        st.caption("Heuristic observations to guide code reviews. These are recommendations, not verified defects or audits.")

        ins = scan_data.get("insights", {})
        i1, i2 = st.columns(2)

        with i1:
            st.markdown("#### 📏 High Line-Count Files (>400 lines)")
            large_files = ins.get("large_files", [])
            if large_files:
                for lf in large_files:
                    st.warning(f"📄 `{lf['path']}` — **{lf['lines']} lines** (Potential candidate for modularization)")
            else:
                st.success("✅ No oversized source files detected.")

        with i2:
            st.markdown("#### 🗂️ Deeply Nested Directories (>= 4 levels)")
            deep = ins.get("deeply_nested", [])
            if deep:
                for d in deep:
                    st.info(f"📁 `{d}`")
            else:
                st.success("✅ Clean directory nesting depth.")

        # Skipped secrets note
        sec_skipped = scan_data.get("skipped_secret_files", [])
        if sec_skipped:
            st.markdown("#### 🛡️ Shielded Sensitive Files")
            for sec in sec_skipped:
                st.error(f"🔒 `{sec}` — Excluded from AI prompts to prevent credential exposure.")

    # TAB 7: EXPORT
    with tab_export:
        st.markdown("### 💾 Export Reports & Artifacts")
        st.write("Download formatted reports for your team, documentation wikis, or PR reviews.")

        full_report_md = ReportGenerator.generate_overview_report(
            scan_data,
            st.session_state.get("ai_overview", "")
        )

        st.download_button(
            label="⬇️ Download Full Codebase Analysis (Markdown)",
            data=full_report_md,
            file_name=f"RepoSloth_{scan_data['repo_name']}_Analysis.md",
            mime="text/markdown",
            use_container_width=True
        )

        st.download_button(
            label="⬇️ Download Mermaid Diagram (.mmd)",
            data=ArchitectureBuilder.generate_mermaid_diagram(scan_data),
            file_name=f"{scan_data['repo_name']}_architecture.mmd",
            mime="text/plain",
            use_container_width=True
        )
