from unittest.mock import AsyncMock, MagicMock, patch


class TestScanPipeline:
    def test_scan_with_valid_image(self, client, auth_headers, sample_image_bytes):
        mock_image = MagicMock()
        mock_image.id = 1
        mock_image.storage_path = "/tmp/test.jpg"
        mock_storage_instance = MagicMock()
        mock_storage_instance.save_image = AsyncMock(return_value=mock_image)

        with (
            patch("app.main._get_user_farm_and_crop") as mock_farm_crop,
            patch("app.main.LocalFileStorage", return_value=mock_storage_instance),
            patch("app.main.HierarchicalAgriculturalOrchestrator") as MockOrch,
        ):
            mock_farm_crop.return_value = (MagicMock(id=1), MagicMock(id=1))
            mock_result = MagicMock()
            mock_result.disease.label = "Bacterial Leaf Blight"
            mock_result.disease.confidence = 0.85
            mock_result.disease.evidence = ["Test evidence"]
            mock_result.disease.rules_fired = ["onnx_model:Rice"]
            mock_result.severity.label = "none"
            mock_result.severity.score = 0.9
            mock_result.severity.evidence = []
            mock_result.severity.rules_fired = []
            mock_result.response = "Treatment: Apply fungicide"
            mock_result.trace = []
            MockOrch.return_value.analyze_image.return_value = mock_result

            resp = client.post(
                "/api/scan",
                headers=auth_headers,
                files={"file": ("leaf.jpg", sample_image_bytes, "image/jpeg")},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert "disease" in data
        assert "severity" in data

    def test_scan_with_crop_override(self, client, auth_headers, sample_image_bytes):
        mock_image = MagicMock()
        mock_image.id = 1
        mock_image.storage_path = "/tmp/test.jpg"
        mock_storage_instance = MagicMock()
        mock_storage_instance.save_image = AsyncMock(return_value=mock_image)

        with (
            patch("app.main._get_user_farm_and_crop") as mock_farm_crop,
            patch("app.main.LocalFileStorage", return_value=mock_storage_instance),
            patch("app.main.HierarchicalAgriculturalOrchestrator") as MockOrch,
        ):
            mock_farm_crop.return_value = (MagicMock(id=1), MagicMock(id=1))
            mock_result = MagicMock()
            mock_result.disease.label = "Healthy"
            mock_result.disease.confidence = 0.99
            mock_result.disease.evidence = []
            mock_result.disease.rules_fired = []
            mock_result.severity.label = "none"
            mock_result.severity.score = 0.95
            mock_result.severity.evidence = []
            mock_result.severity.rules_fired = []
            mock_result.response = "Your crop is healthy"
            mock_result.trace = []
            MockOrch.return_value.analyze_image.return_value = mock_result

            resp = client.post(
                "/api/scan",
                headers=auth_headers,
                files={"file": ("leaf.jpg", sample_image_bytes, "image/jpeg")},
                data={"crop": "Tomato"},
            )
        assert resp.status_code == 200

    def test_scan_without_file_fails(self, client, auth_headers):
        resp = client.post("/api/scan", headers=auth_headers)
        assert resp.status_code == 422

    def test_v1_disease_requires_auth(self, client, sample_image_bytes):
        resp = client.post(
            "/api/v1/disease/analyze",
            files={"file": ("leaf.jpg", sample_image_bytes, "image/jpeg")},
        )
        assert resp.status_code == 401
