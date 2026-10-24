"""Language detector service mapping file extensions, filenames, and manifests to languages and frameworks."""

from __future__ import annotations
from pathlib import Path
from typing import Dict, Any, List, Optional

# Extension mappings to programming and markup languages
EXTENSION_MAP: Dict[str, str] = {
    ".py": "Python",
    ".pyw": "Python",
    ".js": "JavaScript",
    ".jsx": "JavaScript (React)",
    ".ts": "TypeScript",
    ".tsx": "TypeScript (React)",
    ".java": "Java",
    ".c": "C",
    ".h": "C/C++ Header",
    ".cpp": "C++",
    ".hpp": "C++ Header",
    ".cc": "C++",
    ".cxx": "C++",
    ".cs": "C#",
    ".go": "Go",
    ".rs": "Rust",
    ".php": "PHP",
    ".rb": "Ruby",
    ".swift": "Swift",
    ".kt": "Kotlin",
    ".kts": "Kotlin Script",
    ".scala": "Scala",
    ".m": "Objective-C",
    ".sh": "Shell Script",
    ".bash": "Shell Script",
    ".zsh": "Shell Script",
    ".ps1": "PowerShell",
    ".bat": "Batch",
    ".cmd": "Batch",
    ".html": "HTML",
    ".htm": "HTML",
    ".css": "CSS",
    ".scss": "SCSS",
    ".sass": "Sass",
    ".less": "Less",
    ".sql": "SQL",
    ".graphql": "GraphQL",
    ".gql": "GraphQL",
    ".lua": "Lua",
    ".r": "R",
    ".dart": "Dart",
    ".ex": "Elixir",
    ".exs": "Elixir",
    ".erl": "Erlang",
    ".clj": "Clojure",
    ".zig": "Zig",
    ".json": "JSON",
    ".yaml": "YAML",
    ".yml": "YAML",
    ".toml": "TOML",
    ".xml": "XML",
    ".md": "Markdown",
    ".rst": "reStructuredText",
    ".dockerfile": "Dockerfile",
}

# Special filenames mapping
FILENAME_MAP: Dict[str, str] = {
    "dockerfile": "Dockerfile",
    "docker-compose.yml": "Docker Compose",
    "docker-compose.yaml": "Docker Compose",
    "makefile": "Makefile",
    "gemfile": "Ruby Gemfile",
    "rakefile": "Ruby Rakefile",
    "cmakelists.txt": "CMake",
    "jenkinsfile": "Jenkins Pipeline",
    "vagrantfile": "Vagrant",
}

# Framework / Manifest detection patterns
FRAMEWORK_SIGNATURES: Dict[str, Dict[str, Any]] = {
    "FastAPI": {"files": ["main.py", "app.py"], "keywords": ["FastAPI", "fastapi"]},
    "Flask": {"files": ["app.py", "main.py", "wsgi.py"], "keywords": ["Flask", "flask"]},
    "Django": {"files": ["manage.py", "settings.py", "wsgi.py"], "keywords": ["django"]},
    "Streamlit": {"files": ["app.py", "streamlit_app.py"], "keywords": ["import streamlit", "st."]},
    "React": {"files": ["package.json"], "keywords": ["react", "react-dom"]},
    "Next.js": {"files": ["next.config.js", "next.config.mjs", "next.config.ts"], "keywords": ["next"]},
    "Vue.js": {"files": ["vue.config.js", "vite.config.js"], "keywords": ["vue"]},
    "Angular": {"files": ["angular.json"], "keywords": ["@angular/core"]},
    "Express.js": {"files": ["package.json"], "keywords": ["express"]},
    "Spring Boot": {"files": ["pom.xml", "build.gradle"], "keywords": ["spring-boot"]},
    "PyTorch": {"keywords": ["torch", "pytorch"]},
    "TensorFlow": {"keywords": ["tensorflow", "keras"]},
    "Tailwind CSS": {"files": ["tailwind.config.js", "tailwind.config.ts"], "keywords": ["tailwindcss"]},
}


class LanguageDetector:
    """Detects languages, frameworks, entrypoints, and manifest data."""

    @staticmethod
    def detect_language(path: Path) -> str:
        """Determines language based on file extension and name."""
        name_lower = path.name.lower()
        if name_lower in FILENAME_MAP:
            return FILENAME_MAP[name_lower]
        
        ext = path.suffix.lower()
        return EXTENSION_MAP.get(ext, "Unknown / Other")

    @staticmethod
    def detect_manifests(repo_root: Path) -> Dict[str, Any]:
        """Scans for manifest files like requirements.txt, package.json, Cargo.toml, pyproject.toml."""
        manifests = {}
        
        # Python requirements.txt
        req_txt = repo_root / "requirements.txt"
        if req_txt.exists() and req_txt.is_file():
            try:
                content = req_txt.read_text(encoding="utf-8", errors="ignore")
                deps = [line.strip() for line in content.splitlines() if line.strip() and not line.startswith("#")]
                manifests["requirements.txt"] = deps[:25]
            except Exception:
                pass

        # pyproject.toml
        pyproj = repo_root / "pyproject.toml"
        if pyproj.exists() and pyproj.is_file():
            try:
                manifests["pyproject.toml"] = "Present (Standard Python build manifest)"
            except Exception:
                pass

        # package.json
        pkg_json = repo_root / "package.json"
        if pkg_json.exists() and pkg_json.is_file():
            try:
                import json
                data = json.loads(pkg_json.read_text(encoding="utf-8", errors="ignore"))
                deps = list(data.get("dependencies", {}).keys()) + list(data.get("devDependencies", {}).keys())
                manifests["package.json"] = deps[:25]
            except Exception:
                pass

        # Cargo.toml (Rust)
        cargo = repo_root / "Cargo.toml"
        if cargo.exists() and cargo.is_file():
            manifests["Cargo.toml"] = "Present (Rust project manifest)"

        # pom.xml / build.gradle (Java)
        if (repo_root / "pom.xml").exists():
            manifests["pom.xml"] = "Present (Maven build descriptor)"
        if (repo_root / "build.gradle").exists():
            manifests["build.gradle"] = "Present (Gradle build file)"

        # go.mod (Go)
        if (repo_root / "go.mod").exists():
            manifests["go.mod"] = "Present (Go modules manifest)"

        return manifests

    @staticmethod
    def identify_entrypoints(repo_root: Path, file_list: List[Path]) -> List[str]:
        """Detects standard candidate application entry points."""
        candidates = []
        entrypoint_names = [
            "main.py", "app.py", "index.py", "cli.py", "__main__.py", "server.py", "run.py",
            "index.js", "app.js", "server.js", "main.js",
            "index.ts", "app.ts", "server.ts", "main.ts",
            "main.go", "main.rs", "App.java", "Main.java", "Program.cs"
        ]

        for p in file_list:
            if p.name.lower() in entrypoint_names:
                try:
                    rel_path = str(p.relative_to(repo_root)).replace("\\", "/")
                    candidates.append(rel_path)
                except ValueError:
                    candidates.append(p.name)

        # Sort so root-level or short-depth entry points appear first
        candidates.sort(key=lambda x: (x.count("/"), len(x)))
        return candidates[:10]
