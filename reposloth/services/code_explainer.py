"""Code explainer service orchestrating prompts, sanitization, and AI inference."""

from __future__ import annotations
from pathlib import Path
from typing import Dict, Any, Optional
from reposloth.services.ollama_client import OllamaClient
from reposloth.services.secret_filter import SecretFilter
from reposloth.services.language_detector import LanguageDetector


class CodeExplainer:
    """Orchestrates AI explanations for repositories, source files, and developer Q&A."""

    def __init__(self, ollama_client: OllamaClient, prompts_dir: Optional[Path] = None):
        self.client = ollama_client
        if prompts_dir is None:
            self.prompts_dir = Path(__file__).parent.parent / "prompts"
        else:
            self.prompts_dir = Path(prompts_dir)

    def _read_prompt(self, filename: str) -> str:
        """Reads a prompt template from the prompts folder."""
        p = self.prompts_dir / filename
        if p.exists():
            return p.read_text(encoding="utf-8")
        return ""

    def explain_repository(self, scan_result: Dict[str, Any], model: str) -> Dict[str, Any]:
        """Generates an overarching AI overview of the scanned repository."""
        repo_path = Path(scan_result["repo_path"])
        repo_name = scan_result.get("repo_name", "Unknown Repo")
        total_files = scan_result.get("total_files", 0)
        total_lines = scan_result.get("total_lines", 0)

        # Language summary string
        lang_parts = []
        for lang, stats in scan_result.get("language_stats", {}).items():
            lang_parts.append(f"- {lang}: {stats['files']} files, {stats['lines']} lines")
        language_summary = "\n".join(lang_parts) if lang_parts else "No source files identified."

        # Manifest summary string
        manifest_parts = []
        for mname, mval in scan_result.get("manifests", {}).items():
            if isinstance(mval, list):
                manifest_parts.append(f"- {mname}: {', '.join(mval)}")
            else:
                manifest_parts.append(f"- {mname}: {mval}")
        manifest_summary = "\n".join(manifest_parts) if manifest_parts else "None detected."

        # Candidate entrypoints
        entrypoints = scan_result.get("entrypoint_candidates", [])
        entrypoint_summary = "\n".join([f"- {ep}" for ep in entrypoints]) if entrypoints else "None clearly identified."

        # Top file list
        files = scan_result.get("file_list", [])[:40]
        file_structure_summary = "\n".join([f"- {f}" for f in files])
        if len(scan_result.get("file_list", [])) > 40:
            file_structure_summary += f"\n... and {len(scan_result.get('file_list', [])) - 40} more files."

        # Read README snippet if available
        readme_snippet = "No README file found."
        for candidate in ["README.md", "README.rst", "README.txt", "readme.md"]:
            rp = repo_path / candidate
            if rp.exists() and rp.is_file():
                try:
                    raw_rm = rp.read_text(encoding="utf-8", errors="ignore")[:2500]
                    readme_snippet, _ = SecretFilter.sanitize_text(raw_rm)
                    break
                except Exception:
                    pass

        sys_prompt = self._read_prompt("system_prompt.txt")
        template = self._read_prompt("repository_summary.txt")

        prompt = template.format(
            repo_name=repo_name,
            total_files=total_files,
            total_lines=total_lines,
            language_summary=language_summary,
            manifest_summary=manifest_summary,
            entrypoint_summary=entrypoint_summary,
            file_structure_summary=file_structure_summary,
            readme_snippet=readme_snippet
        )

        return self.client.generate(model=model, prompt=prompt, system=sys_prompt)

    def explain_file(self, repo_path: Path, rel_file_path: str, model: str) -> Dict[str, Any]:
        """Generates a deep-dive explanation of a specific source file."""
        abs_path = repo_path / rel_file_path
        if not abs_path.is_file():
            return {"response": "", "success": False, "error": f"File not found: {rel_file_path}"}

        try:
            content = abs_path.read_text(encoding="utf-8", errors="ignore")
        except Exception as e:
            return {"response": "", "success": False, "error": f"Could not read file: {str(e)}"}

        sanitized_content, _ = SecretFilter.sanitize_text(content)
        lines = sanitized_content.splitlines()
        line_count = len(lines)
        language = LanguageDetector.detect_language(abs_path)

        # Truncate if file is overly long to fit typical 8k context window
        if len(sanitized_content) > 25000:
            sanitized_content = sanitized_content[:25000] + "\n\n... [Content truncated for AI context window safety] ..."

        sys_prompt = self._read_prompt("system_prompt.txt")
        template = self._read_prompt("file_explanation.txt")

        prompt = template.format(
            repo_name=repo_path.name,
            file_path=rel_file_path,
            language=language,
            line_count=line_count,
            file_content=sanitized_content
        )

        return self.client.generate(model=model, prompt=prompt, system=sys_prompt)

    def answer_question(
        self,
        repo_name: str,
        question: str,
        retrieved_snippets: list[Dict[str, Any]],
        model: str
    ) -> Dict[str, Any]:
        """Answers a user codebase question grounded in retrieved snippets."""
        snippet_blocks = []
        for i, snip in enumerate(retrieved_snippets, 1):
            block = (
                f"--- Snippet #{i} ---\n"
                f"File: {snip['file']} (Lines {snip['start_line']} - {snip['end_line']})\n"
                f"```\n{snip['text']}\n```"
            )
            snippet_blocks.append(block)

        retrieved_str = "\n\n".join(snippet_blocks) if snippet_blocks else "No relevant source snippets could be matched."

        sys_prompt = self._read_prompt("system_prompt.txt")
        template = self._read_prompt("code_qa.txt")

        prompt = template.format(
            repo_name=repo_name,
            user_question=question,
            retrieved_snippets=retrieved_str
        )

        return self.client.generate(model=model, prompt=prompt, system=sys_prompt)

    def generate_documentation(self, repo_path: Path, rel_file_path: str, model: str) -> Dict[str, Any]:
        """Generates draft documentation and docstrings for a source module."""
        abs_path = repo_path / rel_file_path
        if not abs_path.is_file():
            return {"response": "", "success": False, "error": f"File not found: {rel_file_path}"}

        try:
            content = abs_path.read_text(encoding="utf-8", errors="ignore")
        except Exception as e:
            return {"response": "", "success": False, "error": f"Could not read file: {str(e)}"}

        sanitized_content, _ = SecretFilter.sanitize_text(content)
        language = LanguageDetector.detect_language(abs_path)

        prompt = (
            f"Generate professional Markdown documentation for the following {language} file from '{repo_path.name}'.\n"
            f"File: {rel_file_path}\n\n"
            f"Include:\n"
            f"1. Module Overview & Responsibilities\n"
            f"2. Function & Class API Reference (Parameters, Return values, Errors)\n"
            f"3. Realistic Usage Example (Code block)\n"
            f"4. Suggested README section or integration notes\n\n"
            f"Source Code:\n```\n{sanitized_content[:20000]}\n```"
        )
        sys_prompt = self._read_prompt("system_prompt.txt")
        return self.client.generate(model=model, prompt=prompt, system=sys_prompt)
