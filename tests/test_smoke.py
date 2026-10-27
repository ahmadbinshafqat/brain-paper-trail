from fastapi.testclient import TestClient

from app.main import app


def test_analyze_text_returns_ranked_sentences():
    client = TestClient(app)
    payload = {
        "title": "Smoke Test",
        "text": "Reading changes how we notice the world. The strongest sentences carry pressure, precision, and a little risk. This is short. However, a memorable line gives readers language for something they already felt but could not yet say.",
        "top_n": 3,
    }
    response = client.post("/analyze-text", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["document_id"] > 0
    assert len(data["sentences"]) >= 1
    scores = [sentence["score"] for sentence in data["sentences"]]
    assert scores == sorted(scores, reverse=True)
