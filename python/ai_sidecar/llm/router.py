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

    def __init__(
        self, 
        config: Optional[Dict[str, Dict[str, Any]]] = None, 
        verbose: bool = False,
        model_override: Optional[str] = None,
        prefer_local: bool = True
    ):
        self.config = config or self._default_config()
        self._local_available: Optional[bool] = None
        self.verbose = verbose
        self.model_override = model_override
        self.prefer_local = prefer_local
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
        litellm.set_verbose = self.verbose
        litellm.drop_params = True

    def is_local_available(self) -> bool:
        """Check if Ollama is running locally."""
        if self._local_available is not None:
            return self._local_available

        try:
            response = httpx.get("http://localhost:11434/api/tags", timeout=2.0)
            self._local_available = response.status_code == 200
            if self.verbose:
                logger.info(f"Ollama availability check: {self._local_available}")
        except Exception as e:
            self._local_available = False
            if self.verbose:
                logger.info(f"Ollama not available: {e}")

        return self._local_available

    def get_model_for_tier(
        self, 
        tier: ModelTier, 
        prefer_local: Optional[bool] = None,
        model_override: Optional[str] = None
    ) -> str:
        """Get the appropriate model name for a tier.
        
        Args:
            tier: The model tier (light, medium, heavy)
            prefer_local: Whether to prefer local Ollama models (default: use instance setting)
            model_override: If set, use this model directly bypassing tier selection (default: use instance setting)
            
        Returns:
            The model identifier string
        """
        actual_model_override = model_override or self.model_override
        actual_prefer_local = prefer_local if prefer_local is not None else self.prefer_local
        
        if actual_model_override:
            if self.verbose:
                logger.info(f"Using model override: {actual_model_override}")
            return actual_model_override
            
        cfg = self.config.get(tier.value, {})

        if actual_prefer_local and self.is_local_available():
            model = cfg.get("local_model", cfg.get("remote_model", ""))
            source = "local"
        else:
            model = cfg.get("remote_model", cfg.get("local_model", ""))
            source = "remote"

        if not model:
            raise ValueError(f"No model configured for tier {tier}")

        if self.verbose:
            logger.info(f"Model selection: tier={tier.value}, prefer_local={prefer_local}, source={source}, model={model}")
            
        return model

    async def complete(
        self,
        prompt: str,
        tier: ModelTier = ModelTier.MEDIUM,
        system_prompt: Optional[str] = None,
        prefer_local: Optional[bool] = None,
        model_override: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        **kwargs,
    ) -> str:
        """Generate completion using appropriate model.
        
        Args:
            prompt: The user prompt
            tier: Model tier (light/medium/heavy)
            system_prompt: Optional system prompt
            prefer_local: Override for prefer_local (default: use instance setting)
            model_override: Override for model (default: use instance setting)
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
        """
        actual_prefer_local = prefer_local if prefer_local is not None else self.prefer_local
        actual_model_override = model_override or self.model_override
        model = self.get_model_for_tier(tier, actual_prefer_local, actual_model_override)

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        if self.verbose:
            logger.info(f"LLM request: model={model}, tier={tier.value}")
            logger.info(f"  System prompt: {system_prompt[:100] if system_prompt else 'None'}...")
            logger.info(f"  User prompt: {prompt[:200]}...")

        try:
            response = await acompletion(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs,
            )
            content = response.choices[0].message.content
            
            if self.verbose:
                usage = getattr(response, 'usage', None)
                if usage:
                    logger.info(f"LLM response: tokens_prompt={usage.prompt_tokens}, tokens_completion={usage.completion_tokens}")
                logger.info(f"  Response: {content[:200]}...")
                
            return content
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            raise

    async def complete_with_context(
        self,
        prompt: str,
        context: List[str],
        tier: ModelTier = ModelTier.MEDIUM,
        model_override: Optional[str] = None,
        prefer_local: Optional[bool] = None,
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
        return await self.complete(full_prompt, tier=tier, system_prompt=system_prompt, model_override=model_override, prefer_local=prefer_local, **kwargs)

    async def analyze_code(
        self,
        code: str,
        question: str,
        tier: ModelTier = ModelTier.MEDIUM,
        model_override: Optional[str] = None,
        prefer_local: Optional[bool] = None,
    ) -> str:
        """Analyze code and answer a question about it."""
        prompt = f"""Code:
```
{code}
```

Question: {question}

Provide a detailed analysis."""
        return await self.complete(prompt, tier=tier, prefer_local=prefer_local, model_override=model_override)

    async def suggest_refactor(
        self,
        code: str,
        language: str,
        goal: str,
        tier: ModelTier = ModelTier.MEDIUM,
        model_override: Optional[str] = None,
        prefer_local: Optional[bool] = None,
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

        return await self.complete(prompt, tier=tier, system_prompt=system_prompt, prefer_local=prefer_local, model_override=model_override)

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
