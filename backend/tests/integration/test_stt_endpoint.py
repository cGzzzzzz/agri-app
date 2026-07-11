from unittest.mock import MagicMock, patch


class TestSttEndpoint:
    @patch("app.stt.router.SttService")
    def test_transcribe_returns_text(self, MockSttService, client, auth_headers):
        mock_service = MagicMock()
        mock_service.transcribe.return_value = "The crop looks healthy"
        MockSttService.return_value = mock_service

        audio_data = b"x" * 10000
        response = client.post(
            "/api/v1/stt/transcribe",
            headers=auth_headers,
            files={"file": ("test.wav", audio_data, "audio/wav")},
            data={"language": "en", "sample_rate": "48000", "channels": "1"},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert body["data"]["text"] == "The crop looks healthy"

    @patch("app.stt.router.SttService")
    def test_transcribe_empty_file(self, MockSttService, client, auth_headers):
        response = client.post(
            "/api/v1/stt/transcribe",
            headers=auth_headers,
            files={"file": ("empty.wav", b"", "audio/wav")},
            data={"language": "en"},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["success"] is False

    @patch("app.stt.router.SttService")
    def test_transcribe_custom_language(self, MockSttService, client, auth_headers):
        mock_service = MagicMock()
        mock_service.transcribe.return_value = "namaskar"
        MockSttService.return_value = mock_service

        response = client.post(
            "/api/v1/stt/transcribe",
            headers=auth_headers,
            files={"file": ("test.wav", b"x" * 10000, "audio/wav")},
            data={"language": "hi", "sample_rate": "48000", "channels": "1"},
        )
        assert response.status_code == 200
        mock_service.transcribe.assert_called_once()
        call_kwargs = mock_service.transcribe.call_args
        assert call_kwargs[1]["language"] == "hi" or call_kwargs[0][2] == "hi"

    @patch("app.stt.router.SttService")
    def test_transcribe_service_error(self, MockSttService, client, auth_headers):
        mock_service = MagicMock()
        mock_service.transcribe.side_effect = ValueError("Audio too short")
        MockSttService.return_value = mock_service

        response = client.post(
            "/api/v1/stt/transcribe",
            headers=auth_headers,
            files={"file": ("test.wav", b"x" * 10000, "audio/wav")},
            data={"language": "en", "sample_rate": "48000", "channels": "1"},
        )
        assert response.status_code == 500
