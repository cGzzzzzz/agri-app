from unittest.mock import MagicMock, patch

from app.llm.provider import NullLLMProvider, get_llm_provider


class TestLLMProvider:
    def test_null_provider_not_available(self):
        provider = NullLLMProvider()
        assert not provider.is_available
        assert provider.provider_name == "none"

    def test_null_provider_complete(self):
        provider = NullLLMProvider()
        result = provider.complete("system", "user")
        assert result == ""

    def test_null_provider_complete_structured(self):
        provider = NullLLMProvider()
        result = provider.complete_structured("system", "user", {})
        assert result == {}

    def test_get_provider_fallback_to_null(self):
        with patch("app.llm.provider.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                llm_provider="none",
                openai_api_key="",
                groq_api_key="",
                gemini_api_key="",
                nvidia_api_key="",
                deepseek_api_key="",
            )
            get_llm_provider.cache_clear()
            provider = get_llm_provider()
            assert isinstance(provider, NullLLMProvider)

    def test_groq_provider_init(self):
        from app.llm.groq_provider import GroqProvider

        provider = GroqProvider(api_key="test-key", model="test-model")
        assert provider.provider_name == "groq"
        assert provider.is_available is True

    def test_groq_provider_no_key_not_available(self):
        from app.llm.groq_provider import GroqProvider

        provider = GroqProvider(api_key="", model="test-model")
        assert provider.is_available is False

    def test_gemini_provider_not_available_without_key(self):
        from app.llm.gemini_provider import GeminiProvider

        provider = GeminiProvider(api_key="", model="test")
        assert not provider.is_available
