from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_demo_analyze_and_scan_lifecycle():
    # 1. Analyze with demo provider
    response = client.post("/api/v1/analyze", json={
        "website_url": "https://my-site.example", "category": "software",
        "country": "IN", "keywords": ["python"], "provider": "demo"
    })
    assert response.status_code == 200
    body = response.json()
    assert body["prospects_found"] == 2
    scan_id = body["scan_id"]
    assert any("synthetic" in warning.lower() for warning in body["warnings"])

    # 2. List scans
    list_resp = client.get("/api/v1/scans?limit=10")
    assert list_resp.status_code == 200
    scans = list_resp.json()["scans"]
    assert any(s["scan_id"] == scan_id for s in scans)

    # 3. Read scan with filtering
    get_resp = client.get(f"/api/v1/scans/{scan_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["scan_id"] == scan_id

    # Filter by verified_free
    filtered_resp = client.get(f"/api/v1/scans/{scan_id}?cost_status=verified_free")
    assert filtered_resp.status_code == 200
    assert filtered_resp.json()["payload"]["prospects_found"] == 1

    # 4. Export to Excel (.xlsx)
    xlsx_resp = client.get(f"/api/v1/export/xlsx/{scan_id}")
    assert xlsx_resp.status_code == 200
    assert "spreadsheetml" in xlsx_resp.headers.get("content-type", "")
    assert len(xlsx_resp.content) > 1000

    # 5. Delete scan
    del_resp = client.delete(f"/api/v1/scans/{scan_id}")
    assert del_resp.status_code == 200
    assert del_resp.json()["deleted"] is True

    # 6. Verify deleted
    not_found = client.get(f"/api/v1/scans/{scan_id}")
    assert not_found.status_code == 404

def test_score_endpoint():
    response = client.post("/api/v1/score", json={"prospects": [{"domain": "example.com"}]})
    assert response.status_code == 200
    assert response.json()["prospects"][0]["cost_status"] == "pending_verification"

def test_live_search_provider(monkeypatch):
    from app.schemas import ProspectInput

    async def mock_discover(self, website_domain, category, keywords, country, target_count=100, **kwargs):
        return [
            ProspectInput(
                domain="real-directory.com",
                page_url="https://real-directory.com/submit",
                title="Real Dev Tools Directory",
                description="Live directory accepting developer resources.",
                category=category,
                evidence_url="https://real-directory.com/submit",
                free_submission_available=True
            )
        ]

    from app.providers.live_search import LiveSearchProvider
    monkeypatch.setattr(LiveSearchProvider, "discover", mock_discover)

    response = client.post("/api/v1/analyze", json={
        "website_url": "https://my-site.example",
        "category": "developer-tools",
        "country": "US",
        "keywords": ["open source"],
        "provider": "live_search"
    })
    assert response.status_code == 200
    body = response.json()
    assert body["provider"] == "live_search"
    assert body["prospects_found"] == 1
    assert body["prospects"][0]["domain"] == "real-directory.com"
    assert any("live web" in w.lower() for w in body["warnings"])

def test_explain_endpoint(monkeypatch):
    # Test with mock response
    async def mock_explain(domain, category, evidence):
        return f"Mocked explanation for {domain} in {category}"

    monkeypatch.setattr("app.main.explain_prospect", mock_explain)

    resp = client.post("/api/v1/prospects/explain", json={
        "domain": "example.org",
        "category": "software",
        "evidence": {"terms_verified": True}
    })
    assert resp.status_code == 200
    assert "Mocked explanation for example.org in software" in resp.json()["explanation"]

def test_backlink_check_ssrf_protection():
    resp = client.post("/api/v1/backlinks/check", json={
        "urls": ["http://127.0.0.1:8000/internal", "http://localhost/admin"]
    })
    assert resp.status_code == 200
    results = resp.json()["results"]
    assert len(results) == 2
    for r in results:
        assert r["reachable"] is False
        assert "ssrf" in r["note"].lower()

def test_backlink_check_html_parsing(monkeypatch):
    import httpx

    html_content = """
    <html>
      <head><meta name="robots" content="index, follow"></head>
      <body>
        <a href="https://mysite.example/page" rel="dofollow">My Best Site</a>
      </body>
    </html>
    """

    class MockResponse:
        status_code = 200
        url = "https://public-resource.example/directory"
        headers = {"content-type": "text/html; charset=utf-8"}
        text = html_content
        is_redirect = False

    async def mock_get(self, url, **kwargs):
        return MockResponse()

    monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)
    monkeypatch.setattr("app.security.validate_public_url", lambda u: u)

    resp = client.post("/api/v1/backlinks/check", json={
        "urls": ["https://public-resource.example/directory"],
        "target_domain": "mysite.example"
    })
    assert resp.status_code == 200
    res = resp.json()["results"][0]
    assert res["reachable"] is True
    assert res["backlink_found"] is True
    assert res["anchor_text"] == "My Best Site"
    assert res["is_dofollow"] is True
    assert res["noindex"] is False

def test_async_scan_job_and_status():
    # 1. Trigger async scan with sync=false
    resp = client.post("/api/v1/analyze?sync=false", json={
        "website_url": "https://my-site.example",
        "category": "software",
        "country": "US",
        "keywords": ["developer tools"],
        "provider": "demo"
    })
    assert resp.status_code == 202
    data = resp.json()
    assert data["status"] in ("queued", "discovering", "completed")
    scan_id = data["scan_id"]
    assert "stream_url" in data
    assert "status_url" in data

    # 2. Check status endpoint
    status_resp = client.get(f"/api/v1/scans/{scan_id}/status")
    assert status_resp.status_code == 200
    status_data = status_resp.json()
    assert status_data["scan_id"] == scan_id
    assert status_data["category"] == "software"
    assert status_data["website_domain"] == "my-site.example"

    # 3. Check stream endpoint starts event stream
    with client.stream("GET", f"/api/v1/scans/{scan_id}/stream") as stream:
        assert stream.status_code == 200
        assert "text/event-stream" in stream.headers.get("content-type", "")
        # Read the first event
        for line in stream.iter_lines():
            if line.startswith("data:"):
                assert scan_id in line
                break

