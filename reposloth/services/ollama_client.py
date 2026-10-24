"""Ollama client service managing model availability, inference, timeouts, and fallbacks."""

from __future__ import annotations
import json
import urllib.request
import urllib.error
from typing import Dict, Any, List, Optional, Generator

# Recommended open-weight code models
RECOMMENDED_MODELS = [
    {
        "id": "qwen2.5-coder:7b",
        "name": "Qwen 2.5 Coder (7B)",
        "license": "Apache 2.0",
        "description": "State-of-the-art open-weight code model by Alibaba Qwen team. Excellent for reasoning, explanation, and architectural understanding.",
        "ram_required": "~8 GB RAM / VRAM"
    },
    {
        "id": "qwen2.5-coder:1.5b",
        "name": "Qwen 2.5 Coder (1.5B)",
        "license": "Apache 2.0",
        "description": "Ultra-lightweight fast code model, fits in low-spec laptops and runs smoothly without dedicated GPU.",
        "ram_required": "~3 GB RAM"
    },
    {
        "id": "deepseek-coder-v2:16b",
        "name": "DeepSeek Coder V2 (16B Lite)",
        "license": "DeepSeek Open Model License",
        "description": "High capability MoE code model with broad multilingual support and deep reasoning.",
        "ram_required": "~12 GB RAM / VRAM"
    },
    {
        "id": "codellama:7b",
        "name": "Code Llama (7B)",
        "license": "Llama 2 Community License",
        "description": "Meta's specialized code synthesis and understanding model.",
        "ram_required": "~8 GB RAM"
    },
    {
        "id": "llama3.2:3b",
        "name": "Llama 3.2 (3B)",
        "license": "Llama 3.2 Community License",
        "description": "Compact general-purpose model with strong instruction following and code reading abilities.",
        "ram_required": "~4 GB RAM"
    }
]


class OllamaClient:
    """Client for local Ollama HTTP REST API with robust error handling."""

    def __init__(self, host: str = "http://localhost:11434"):
        self.host = host.rstrip("/")

    def check_connection(self) -> Dict[str, Any]:
        """
        Tests if Ollama is running and accessible at host.
        Returns {'connected': bool, 'models': list[str], 'error': str|None}
        """
        url = f"{self.host}/api/tags"
        try:
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=3) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    models = [m.get("name") for m in data.get("models", [])]
                    return {
                        "connected": True,
                        "models": models,
                        "error": None
                    }
                else:
                    return {
                        "connected": False,
                        "models": [],
                        "error": f"Ollama HTTP returned status {resp.status}"
                    }
        except urllib.error.URLError as e:
            return {
                "connected": False,
                "models": [],
                "error": f"Cannot connect to Ollama at {self.host}. Is Ollama installed and running? ({e.reason})"
            }
        except Exception as e:
            return {
                "connected": False,
                "models": [],
                "error": f"Connection check failed: {str(e)}"
            }

    def generate(
        self,
        model: str,
        prompt: str,
        system: Optional[str] = None,
        temperature: float = 0.2,
        timeout: int = 120
    ) -> Dict[str, Any]:
        """
        Sends a single generation request to /api/generate.
        Returns {'response': str, 'success': bool, 'error': str|None}
        """
        url = f"{self.host}/api/generate"
        payload: Dict[str, Any] = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
            }
        }
        if system:
            payload["system"] = system

        try:
            req_data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                url,
                data=req_data,
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                if resp.status == 200:
                    res_body = json.loads(resp.read().decode("utf-8"))
                    return {
                        "response": res_body.get("response", ""),
                        "success": True,
                        "error": None
                    }
                else:
                    return {
                        "response": "",
                        "success": False,
                        "error": f"Ollama returned HTTP {resp.status}"
                    }
        except urllib.error.HTTPError as e:
            try:
                err_detail = e.read().decode("utf-8")
            except Exception:
                err_detail = str(e)
            return {
                "response": "",
                "success": False,
                "error": f"Ollama HTTP Error ({e.code}): {err_detail}"
            }
        except urllib.error.URLError as e:
            return {
                "response": "",
                "success": False,
                "error": f"Connection lost to Ollama daemon ({e.reason}). Make sure 'ollama serve' is active."
            }
        except Exception as e:
            return {
                "response": "",
                "success": False,
                "error": f"Inference failed: {str(e)}"
            }
