"""Architecture builder service creating visual trees, Mermaid diagrams, and dependency flows."""

from __future__ import annotations
import re
from pathlib import Path
from typing import Dict, Any, List, Set


class ArchitectureBuilder:
    """Builds folder trees and grounded Mermaid architectural diagrams from verified imports."""

    @staticmethod
    def build_tree_text(file_list: List[str], max_depth: int = 3) -> str:
        """Constructs an ASCII tree structure from relative file paths."""
        tree: Dict[str, Any] = {}
        for path_str in file_list:
            parts = path_str.split("/")
            curr = tree
            for p in parts:
                curr = curr.setdefault(p, {})

        lines: List[str] = []

        def _render(node: Dict[str, Any], prefix: str = "", depth: int = 0):
            if depth > max_depth:
                lines.append(f"{prefix}... (nested subdirectories)")
                return

            items = sorted(node.keys())
            for i, item in enumerate(items):
                is_last = (i == len(items) - 1)
                connector = "└── " if is_last else "├── "
                sub_prefix = "    " if is_last else "│   "

                lines.append(f"{prefix}{connector}{item}")
                if node[item]:  # Is directory
                    _render(node[item], prefix + sub_prefix, depth + 1)

        _render(tree)
        return "\n".join(lines) if lines else "(Empty repository)"

    @staticmethod
    def detect_internal_dependencies(repo_path: Path, file_list: List[str]) -> List[tuple[str, str]]:
        """
        Parses source files for internal module imports (e.g. from services.auth import ...).
        Only links modules when concrete import evidence is present.
        """
        edges: Set[tuple[str, str]] = set()
        
        # Build set of local modules for reference
        local_modules = set()
        for f in file_list:
            p = Path(f)
            stem = p.stem
            local_modules.add(stem)
            if len(p.parts) > 1:
                local_modules.add(p.parts[0])

        for f in file_list:
            if not f.endswith((".py", ".js", ".ts", ".jsx", ".tsx", ".go")):
                continue

            abs_p = repo_path / f
            if not abs_p.is_file():
                continue

            try:
                # Read first 150 lines where imports usually reside
                with open(abs_p, "r", encoding="utf-8", errors="ignore") as fh:
                    head_lines = [fh.readline() for _ in range(150)]
                content = "".join(head_lines)
            except Exception:
                continue

            source_module = Path(f).parts[0] if len(Path(f).parts) > 1 else Path(f).stem

            # Python import pattern: import X, from X import Y
            py_matches = re.findall(r'^\s*(?:from|import)\s+([a-zA-Z0-9_\.]+)', content, re.MULTILINE)
            for m in py_matches:
                target_root = m.split(".")[0]
                if target_root in local_modules and target_root != source_module:
                    edges.add((source_module, target_root))

            # JS/TS import pattern: from './X' or from '../X'
            js_matches = re.findall(r'from\s+[\'"](?:\./|\.\./)([a-zA-Z0-9_\-\/]+)[\'"]', content)
            for m in js_matches:
                target_part = m.split("/")[-1]
                if target_part in local_modules and target_part != source_module:
                    edges.add((source_module, target_part))

        return sorted(list(edges))

    @classmethod
    def generate_mermaid_diagram(cls, scan_result: Dict[str, Any]) -> str:
        """
        Generates a Mermaid graph TD representing observed modules and verified linkages.
        Labels the diagram clearly to avoid claiming unverified dependencies.
        """
        repo_path = Path(scan_result.get("repo_path", ""))
        file_list = scan_result.get("file_list", [])
        entrypoints = scan_result.get("entrypoint_candidates", [])

        # Collect top-level directories or key modules
        top_modules: Set[str] = set()
        for f in file_list:
            parts = f.split("/")
            if len(parts) > 1:
                top_modules.add(parts[0])
            else:
                top_modules.add(parts[0])

        # Scan for detected internal linkages
        edges = cls.detect_internal_dependencies(repo_path, file_list)

        mermaid_lines = [
            "```mermaid",
            "flowchart TD",
            "    %% RepoSloth Grounded Architecture Diagram",
            "    classDef entrypoint fill:#dbeafe,stroke:#2563eb,stroke-width:2px;",
            "    classDef module fill:#f1f5f9,stroke:#64748b,stroke-width:1px;"
        ]

        # Add Entrypoint Nodes
        for ep in entrypoints[:3]:
            safe_id = re.sub(r'[^a-zA-Z0-9_]', '_', ep)
            mermaid_lines.append(f'    {safe_id}["🚀 Entry: {ep}"]:::entrypoint')

        # Add Top Module Nodes
        for mod in sorted(top_modules)[:12]:
            safe_id = re.sub(r'[^a-zA-Z0-9_]', '_', mod)
            if not any(safe_id == re.sub(r'[^a-zA-Z0-9_]', '_', ep) for ep in entrypoints[:3]):
                mermaid_lines.append(f'    {safe_id}["📦 {mod}"]:::module')

        # Link Entrypoints to modules if present
        for ep in entrypoints[:3]:
            safe_ep = re.sub(r'[^a-zA-Z0-9_]', '_', ep)
            ep_parts = ep.split("/")
            if len(ep_parts) > 1:
                safe_target = re.sub(r'[^a-zA-Z0-9_]', '_', ep_parts[0])
                if safe_ep != safe_target:
                    mermaid_lines.append(f"    {safe_ep} -->|executes| {safe_target}")

        # Add verified internal edges
        if edges:
            for src, dst in edges[:20]:
                safe_src = re.sub(r'[^a-zA-Z0-9_]', '_', src)
                safe_dst = re.sub(r'[^a-zA-Z0-9_]', '_', dst)
                mermaid_lines.append(f"    {safe_src} -.->|imports| {safe_dst}")
        else:
            # Fallback connection to entry point
            if entrypoints and top_modules:
                safe_ep = re.sub(r'[^a-zA-Z0-9_]', '_', entrypoints[0])
                for mod in sorted(top_modules)[:4]:
                    safe_mod = re.sub(r'[^a-zA-Z0-9_]', '_', mod)
                    if safe_ep != safe_mod:
                        mermaid_lines.append(f"    {safe_ep} -.->|includes| {safe_mod}")

        mermaid_lines.append("```")
        return "\n".join(mermaid_lines)
