"""RepoSloth services initialization."""

from reposloth.services.archive_validator import ArchiveValidator, ArchiveValidationError
from reposloth.services.language_detector import LanguageDetector
from reposloth.services.secret_filter import SecretFilter
from reposloth.services.repository_scanner import RepositoryScanner
from reposloth.services.ollama_client import OllamaClient, RECOMMENDED_MODELS
from reposloth.services.context_retriever import ContextRetriever
from reposloth.services.code_explainer import CodeExplainer
from reposloth.services.architecture_builder import ArchitectureBuilder
from reposloth.services.report_generator import ReportGenerator

__all__ = [
    "ArchiveValidator",
    "ArchiveValidationError",
    "LanguageDetector",
    "SecretFilter",
    "RepositoryScanner",
    "OllamaClient",
    "RECOMMENDED_MODELS",
    "ContextRetriever",
    "CodeExplainer",
    "ArchitectureBuilder",
    "ReportGenerator",
]
