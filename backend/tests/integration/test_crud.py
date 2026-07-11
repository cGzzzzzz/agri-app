class TestFarmCropCRUD:
    def test_create_farm(self, client, auth_headers):
        resp = client.post(
            "/api/v1/farms",
            headers=auth_headers,
            json={
                "name": "Test Farm",
                "village": "Test Village",
                "district": "Test District",
                "state": "Test State",
                "country": "India",
            },
        )
        assert resp.status_code in (200, 201)
        data = resp.json()["data"]
        assert data["name"] == "Test Farm"

    def test_list_farms(self, client, auth_headers):
        resp = client.get("/api/v1/farms", headers=auth_headers)
        assert resp.status_code == 200
        assert isinstance(resp.json()["data"], list)

    def test_create_crop(self, client, auth_headers):
        farm_resp = client.post(
            "/api/v1/farms",
            headers=auth_headers,
            json={
                "name": "Crop Farm",
                "country": "India",
            },
        )
        farm_id = farm_resp.json()["data"]["id"]
        resp = client.post(
            "/api/v1/crops",
            headers=auth_headers,
            json={
                "farm_id": farm_id,
                "crop_type": "Rice",
                "crop_variety": "Basmati",
            },
        )
        assert resp.status_code in (200, 201)

    def test_list_crops(self, client, auth_headers):
        resp = client.get("/api/v1/crops", headers=auth_headers)
        assert resp.status_code == 200

    def test_delete_farm(self, client, auth_headers):
        farm_resp = client.post(
            "/api/v1/farms",
            headers=auth_headers,
            json={
                "name": "Delete Me Farm",
                "country": "India",
            },
        )
        farm_id = farm_resp.json()["data"]["id"]
        resp = client.delete(f"/api/v1/farms/{farm_id}", headers=auth_headers)
        assert resp.status_code in (200, 204)
