"""LLM router for model selection and completion."""

import logging
import os
from typing import Any, Dict, List, Optional

import httpx
from litellm import acompletion
import litellm

from ai_sidecar.models import ModelTier

logger = logging.getLogger(__name__)


class LLMRouter:
    """Routes LLM requests to appropriate models based on tier."""

    def __init__(self, config: Optional[Dict[str, Dict[str, Any]]] = None):
        self.config = config or self._default_config()
        self._local_available: Optional[bool] = None
        self._setup_litellm()

    def _default_config(self) -> Dict[str, Dict[str, Any]]:
        return {
            "light": {
                "local_model": "ollama/gemma3:270m",
                "remote_model": "openai/gpt-4o-mini",
            },
            "medium": {
                "local_model": "ollama/qwen2.5-coder:1.5b",
                "remote_model": "anthropic/claude-3-haiku-20240307",
            },
            "heavy": {
                "local_model": "ollama/deepseek-coder:6.7b",
                "remote_model": "anthropic/claude-3-5-sonnet-20241022",
            },
        }

    def _setup_litellm(self):
        """Configure LiteLLM with API keys and settings."""
        litellm.set_verbose = False
        litellm.drop_params = True

    def is_local_available(self) -> bool:
        """Check if Ollama is running locally."""
        if self._local_available is not None:
            return self._local_available

        try:
            response = httpx.get("http://localhost:11434/api/tags", timeout=2.0)
            self._local_available = response.status_code == 200
            logger.debug(f"Ollama available: {self._local_available}")
        except Exception:
            self._local_available = False
            logger.debug("Ollama not available")

        return self._local_available

    def get_model_for_tier(self, tier: ModelTier, prefer_local: bool = True) -> str:
        """Get the appropriate model name for a tier."""
        cfg = self.config.get(tier.value, {})

        if prefer_local and self.is_local_available():
            model = cfg.get("local_model", cfg.get("remote_model", ""))
        else:
            model = cfg.get("remote_model", cfg.get("local_model", ""))

        if not model:
            raise ValueError(f"No model configured for tier {tier}")

        return model

    async def complete(
        self,
        prompt: str,
        tier: ModelTier = ModelTier.MEDIUM,
        system_prompt: Optional[str] = None,
        prefer_local: bool = True,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        **kwargs,
    ) -> str:
        """Generate completion using appropriate model."""
        model = self.get_model_for_tier(tier, prefer_local)

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        logger.debug(f"Calling LLM: model={model}, tier={tier}")

        try:
            response = await acompletion(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs,
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            raise

    async def complete_with_context(
        self,
        prompt: str,
        context: List[str],
        tier: ModelTier = ModelTier.MEDIUM,
        **kwargs,
    ) -> str:
        """Generate completion with code context."""
        system_prompt = """You are an expert code analyst. Analyze the provided code 
and provide clear, actionable recommendations. Focus on:
- Code quality and maintainability
- Design patterns and idiomatic code
- Potential bugs or issues
- Performance considerations"""

        full_prompt = "Context:\n" + "\n---\n".join(context) + "\n\n" + prompt
        return await self.complete(full_prompt, tier=tier, system_prompt=system_prompt, **kwargs)

    async def analyze_code(
        self,
        code: str,
        question: str,
        tier: ModelTier = ModelTier.MEDIUM,
    ) -> str:
        """Analyze code and answer a question about it."""
        prompt = f"""Code:
```
{code}
```

Question: {question}

Provide a detailed analysis."""
        return await self.complete(prompt, tier=tier, prefer_local=False)

    async def suggest_refactor(
        self,
        code: str,
        language: str,
        goal: str,
        tier: ModelTier = ModelTier.MEDIUM,
    ) -> str:
        """Suggest refactoring for a code block."""
        system_prompt = f"""You are an expert {language} developer. 
Provide refactoring suggestions that:
- Follow idiomatic {language} patterns
- Improve code readability
- Reduce complexity
- Maintain functional equivalence"""

        prompt = f"""Code to refactor:
```
{code}
```

Refactoring goal: {goal}

Provide:
1. A brief explanation of what should be changed
2. The refactored code
3. Why this is an improvement"""

        return await self.complete(prompt, tier=tier, system_prompt=system_prompt, prefer_local=False)

    def update_config(self, tier: str, config: Dict[str, Any]) -> None:
        """Update configuration for a specific tier."""
        if tier not in [t.value for t in ModelTier]:
            raise ValueError(f"Invalid tier: {tier}")
        self.config[tier] = config
        self._local_available = None

    def set_api_key(self, provider: str, api_key: str) -> None:
        """Set API key for a provider."""
        if provider == "openai":
            os.environ["OPENAI_API_KEY"] = api_key
        elif provider == "anthropic":
            os.environ["ANTHROPIC_API_KEY"] = api_key
        elif provider == "openrouter":
            os.environ["OPENROUTER_API_KEY"] = api_key
        else:
            logger.warning(f"Unknown provider: {provider}")
