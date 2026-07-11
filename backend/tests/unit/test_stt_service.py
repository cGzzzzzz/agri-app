from unittest.mock import MagicMock, patch

import pytest

from app.stt.service import SttService, _filter_hallucinations


class TestFilterHallucinations:
    def test_removes_thank_you_for_watching(self):
        result = _filter_hallucinations("Thank you for watching!")
        assert "thank you" not in result.lower()
        assert "watching" not in result.lower()

    def test_removes_thanks_for_watching(self):
        result = _filter_hallucinations("Thanks for watching this video")
        assert "thanks" not in result.lower()
        assert "watching" not in result.lower()

    def test_removes_subscribe(self):
        result = _filter_hallucinations("Please subscribe to my channel")
        assert "subscribe" not in result.lower()

    def test_keeps_real_text(self):
        text = "The tomato crop looks healthy with no signs of blight"
        result = _filter_hallucinations(text)
        assert result == text

    def test_mixed_content(self):
        text = "The crop is healthy. Thank you for watching!"
        result = _filter_hallucinations(text)
        assert "crop is healthy" in result
        assert "thank you" not in result.lower()

    def test_empty_string(self):
        assert _filter_hallucinations("") == ""

    def test_subtitle_hallucination(self):
        result = _filter_hallucinations("Subtitles by the community of Amara.org")
        assert "subtitles" not in result.lower()


class TestSttService:
    def test_missing_api_key_raises(self):
        with patch("app.stt.service.settings") as mock_settings:
            mock_settings.groq_api_key = ""
            with pytest.raises(ValueError, match="GROQ_API_KEY"):
                SttService().transcribe(b"audio", "test.wav")

    def test_min_audio_bytes_rejection(self):
        with patch("app.stt.service.settings") as mock_settings:
            mock_settings.groq_api_key = "test-key"
            with pytest.raises(ValueError, match="too short"):
                SttService().transcribe(b"ab", "test.wav")

    @patch("app.stt.service.httpx.post")
    @patch("app.stt.service.preprocess_audio")
    def test_transcribe_calls_groq(self, mock_preprocess, mock_post):
        mock_preprocess.return_value = b"fake-wav-bytes"
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {"text": "hello world"}
        mock_post.return_value = mock_response

        with patch("app.stt.service.settings") as mock_settings:
            mock_settings.groq_api_key = "test-key"
            result = SttService().transcribe(
                b"x" * 5000, "test.wav", language="en", sample_rate=48000, channels=1
            )

        assert result == "hello world"
        mock_preprocess.assert_called_once()
        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args
        assert "whisper-large-v3" in str(call_kwargs)

    @patch("app.stt.service.httpx.post")
    @patch("app.stt.service.preprocess_audio")
    def test_transcribe_applies_prompt(self, mock_preprocess, mock_post):
        mock_preprocess.return_value = b"fake-wav"
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {"text": "test"}
        mock_post.return_value = mock_response

        with patch("app.stt.service.settings") as mock_settings:
            mock_settings.groq_api_key = "test-key"
            SttService().transcribe(b"x" * 5000, "test.wav")

        assert "prompt" in str(mock_post.call_args)

    @patch("app.stt.service.httpx.post")
    @patch("app.stt.service.preprocess_audio")
    def test_transcribe_filters_hallucinations(self, mock_preprocess, mock_post):
        mock_preprocess.return_value = b"fake-wav"
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {"text": "The crop is healthy. Thank you for watching!"}
        mock_post.return_value = mock_response

        with patch("app.stt.service.settings") as mock_settings:
            mock_settings.groq_api_key = "test-key"
            result = SttService().transcribe(b"x" * 5000, "test.wav")

        assert "crop is healthy" in result
        assert "thank you" not in result.lower()

    @patch("app.stt.service.httpx.post")
    @patch("app.stt.service.preprocess_audio")
    def test_transcribe_http_error(self, mock_preprocess, mock_post):
        mock_preprocess.return_value = b"fake-wav"
        import httpx

        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal error"
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "500", request=MagicMock(), response=mock_response
        )
        mock_post.return_value = mock_response

        with patch("app.stt.service.settings") as mock_settings:
            mock_settings.groq_api_key = "test-key"
            with pytest.raises(RuntimeError, match="STT failed"):
                SttService().transcribe(b"x" * 5000, "test.wav")
