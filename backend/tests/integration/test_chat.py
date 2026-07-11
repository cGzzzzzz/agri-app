from datetime import datetime, timezone
from unittest.mock import MagicMock, patch


class TestChatFlow:
    def test_chat_with_message(self, client, auth_headers):
        with patch("app.chat.router.ChatService") as MockChat:
            mock_conv = MagicMock()
            mock_conv.id = 1
            mock_conv.user_id = 1
            mock_conv.farm_id = None
            mock_conv.crop_id = None
            mock_conv.input_type = "text"
            mock_conv.question = "My rice leaves have brown spots"
            mock_conv.response = ""
            mock_conv.status = "pending"
            mock_conv.created_at = datetime.now(timezone.utc)
            MockChat.return_value.create_pending.return_value = (mock_conv, {})

            resp = client.post(
                "/api/v1/chat",
                headers=auth_headers,
                json={"message": "My rice leaves have brown spots"},
            )
        assert resp.status_code == 202
        data = resp.json()
        assert data["success"] is True
        assert data["data"]["message_id"] == 1
        assert data["data"]["status"] == "pending"

    def test_chat_without_message(self, client, auth_headers):
        resp = client.post("/api/v1/chat", headers=auth_headers, json={})
        assert resp.status_code in (400, 422)
