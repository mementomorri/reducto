"""
Integration tests for LLM router and model selection.

These tests verify:
1. Model selection based on tier and prefer_local setting
2. Model override functionality
3. Verbose logging of LLM operations
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import logging

from ai_sidecar.llm import LLMRouter
from ai_sidecar.models import ModelTier


class TestLLMRouterModelSelection:
    """Test model selection logic."""

    def test_default_config_has_all_tiers(self):
        router = LLMRouter()
        
        assert "light" in router.config
        assert "medium" in router.config
        assert "heavy" in router.config
        
        for tier in ["light", "medium", "heavy"]:
            assert "local_model" in router.config[tier]
            assert "remote_model" in router.config[tier]

    def test_model_override_bypasses_tier(self):
        router = LLMRouter(model_override="gpt-4o")
        
        model = router.get_model_for_tier(ModelTier.MEDIUM, prefer_local=True)
        assert model == "gpt-4o"
        
        model = router.get_model_for_tier(ModelTier.HEAVY, prefer_local=False)
        assert model == "gpt-4o"

    def test_model_override_in_parameters(self):
        router = LLMRouter()
        
        model = router.get_model_for_tier(
            ModelTier.MEDIUM, 
            prefer_local=True, 
            model_override="claude-3-opus"
        )
        assert model == "claude-3-opus"

    @patch.object(LLMRouter, 'is_local_available', return_value=True)
    def test_prefer_local_uses_local_model(self, mock_available):
        router = LLMRouter()
        
        model = router.get_model_for_tier(ModelTier.MEDIUM, prefer_local=True)
        assert "ollama" in model

    @patch.object(LLMRouter, 'is_local_available', return_value=True)
    def test_prefer_remote_ignores_local(self, mock_available):
        router = LLMRouter()
        
        model = router.get_model_for_tier(ModelTier.MEDIUM, prefer_local=False)
        assert "ollama" not in model
        assert "openai" in model or "anthropic" in model

    @patch.object(LLMRouter, 'is_local_available', return_value=False)
    def test_falls_back_to_remote_when_local_unavailable(self, mock_available):
        router = LLMRouter()
        
        model = router.get_model_for_tier(ModelTier.MEDIUM, prefer_local=True)
        assert "ollama" not in model


class TestLLMRouterComplete:
    """Test LLM completion with model selection."""

    @pytest.mark.asyncio
    async def test_complete_uses_instance_settings(self):
        router = LLMRouter(model_override="test-model", verbose=True)
        
        with patch('ai_sidecar.llm.router.acompletion', new_callable=AsyncMock) as mock_acompletion:
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = "Test response"
            mock_response.usage = MagicMock(prompt_tokens=10, completion_tokens=5)
            mock_acompletion.return_value = mock_response
            
            result = await router.complete("test prompt")
            
            assert result == "Test response"
            call_args = mock_acompletion.call_args
            assert call_args.kwargs["model"] == "test-model"

    @pytest.mark.asyncio
    async def test_complete_parameter_override(self):
        router = LLMRouter(model_override="default-model")
        
        with patch('ai_sidecar.llm.router.acompletion', new_callable=AsyncMock) as mock_acompletion:
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = "Response"
            mock_acompletion.return_value = mock_response
            
            await router.complete("test", model_override="override-model")
            
            call_args = mock_acompletion.call_args
            assert call_args.kwargs["model"] == "override-model"


class TestLLMRouterVerboseLogging:
    """Test verbose logging of LLM operations."""

    def test_verbose_mode_enables_litellm_verbose(self):
        router = LLMRouter(verbose=True)
        assert router.verbose is True

    def test_non_verbose_mode_disables_litellm_verbose(self):
        router = LLMRouter(verbose=False)
        assert router.verbose is False

    @pytest.mark.asyncio
    async def test_complete_logs_model_selection_when_verbose(self, caplog):
        router = LLMRouter(model_override="test-model", verbose=True)
        
        with patch('ai_sidecar.llm.router.acompletion', new_callable=AsyncMock) as mock_acompletion:
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = "Response"
            mock_response.usage = MagicMock(prompt_tokens=10, completion_tokens=5)
            mock_acompletion.return_value = mock_response
            
            with caplog.at_level(logging.INFO):
                await router.complete("test prompt")
            
            assert any("model=test-model" in record.message for record in caplog.records)

    @pytest.mark.asyncio
    async def test_complete_logs_token_usage_when_verbose(self, caplog):
        router = LLMRouter(model_override="test-model", verbose=True)
        
        with patch('ai_sidecar.llm.router.acompletion', new_callable=AsyncMock) as mock_acompletion:
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = "Response"
            mock_response.usage = MagicMock(prompt_tokens=10, completion_tokens=5)
            mock_acompletion.return_value = mock_response
            
            with caplog.at_level(logging.INFO):
                await router.complete("test prompt")
            
            assert any("tokens_prompt=10" in record.message for record in caplog.records)
            assert any("tokens_completion=5" in record.message for record in caplog.records)


class TestLLMRouterOllamaCheck:
    """Test Ollama availability checking."""

    @patch('ai_sidecar.llm.router.httpx.get')
    def test_is_local_available_returns_true_when_ollama_running(self, mock_get):
        mock_get.return_value.status_code = 200
        
        router = LLMRouter()
        result = router.is_local_available()
        
        assert result is True
        mock_get.assert_called_once()
        assert "localhost:11434" in mock_get.call_args.args[0]

    @patch('ai_sidecar.llm.router.httpx.get')
    def test_is_local_available_returns_false_on_connection_error(self, mock_get):
        mock_get.side_effect = Exception("Connection refused")
        
        router = LLMRouter()
        result = router.is_local_available()
        
        assert result is False

    @patch('ai_sidecar.llm.router.httpx.get')
    def test_is_local_available_caches_result(self, mock_get):
        mock_get.return_value.status_code = 200
        
        router = LLMRouter()
        router.is_local_available()
        router.is_local_available()
        
        assert mock_get.call_count == 1


class TestLLMRouterMethods:
    """Test higher-level LLM methods use correct settings."""

    @pytest.mark.asyncio
    async def test_analyze_code_uses_instance_settings(self):
        router = LLMRouter(model_override="analysis-model")
        
        with patch('ai_sidecar.llm.router.acompletion', new_callable=AsyncMock) as mock_acompletion:
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = "Analysis result"
            mock_acompletion.return_value = mock_response
            
            await router.analyze_code("def foo(): pass", "What does this do?")
            
            assert mock_acompletion.called
            call_kwargs = mock_acompletion.call_args.kwargs
            assert call_kwargs.get("model") == "analysis-model"

    @pytest.mark.asyncio
    async def test_suggest_refactor_uses_instance_settings(self):
        router = LLMRouter(model_override="refactor-model")
        
        with patch('ai_sidecar.llm.router.acompletion', new_callable=AsyncMock) as mock_acompletion:
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = "Refactoring suggestion"
            mock_acompletion.return_value = mock_response
            
            await router.suggest_refactor("x = x + 1", "python", "make more idiomatic")
            
            assert mock_acompletion.called
            call_kwargs = mock_acompletion.call_args.kwargs
            assert call_kwargs.get("model") == "refactor-model"
