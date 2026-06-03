"""Complete smoke test for ResearchSensei API endpoints."""

import json
import sys
import time

import httpx

BASE = "http://127.0.0.1:18765"
PASS = 0
FAIL = 0


def run_test(name: str, fn):
    global PASS, FAIL
    try:
        fn()
        PASS += 1
        print(f"  ✅ {name}")
    except Exception as e:
        FAIL += 1
        print(f"  ❌ {name}: {e}")


def test_get_jobs():
    r = httpx.get(f"{BASE}/api/jobs")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)


def test_get_settings():
    r = httpx.get(f"{BASE}/api/settings")
    assert r.status_code == 200
    data = r.json()
    assert "active_provider" in data
    assert "model" in data


def test_settings_test():
    r = httpx.post(f"{BASE}/api/settings/test")
    assert r.status_code == 200
    data = r.json()
    assert "ok" in data
    assert "message" in data


def test_interactive_ask():
    r = httpx.post(
        f"{BASE}/api/interactive/ask",
        json={"job_id": "e2b92219d9aa", "question": "what is this paper about?"},
        timeout=30,
    )
    assert r.status_code == 200
    data = r.json()
    assert "answer_zh" in data
    assert "evidence_status" in data


def test_interactive_ask_with_context():
    r = httpx.post(
        f"{BASE}/api/interactive/ask",
        json={
            "job_id": "e2b92219d9aa",
            "question": "explain the mechanism",
            "selected_text": "anomaly detection",
            "card_type": "paper_card",
        },
        timeout=30,
    )
    assert r.status_code == 200
    data = r.json()
    assert "answer_zh" in data
    # Check that evidence chunks are loaded
    ctx = data.get("context_used", {})
    assert len(ctx.get("evidence_chunks", [])) > 0


def test_learn_bundle():
    r = httpx.get(f"{BASE}/api/learn/e2b92219d9aa/bundle")
    assert r.status_code == 200
    data = r.json()
    assert "paper_card" in data
    assert "skeleton" in data
    assert "formula_cards" in data
    assert "pattern_card" in data
    assert "drill_card" in data


def test_learn_bundle_not_found():
    r = httpx.get(f"{BASE}/api/learn/nonexistent/bundle")
    assert r.status_code == 404


def test_jobs_list():
    r = httpx.get(f"{BASE}/api/jobs")
    assert r.status_code == 200
    jobs = r.json()
    assert len(jobs) > 0
    # Check required fields
    job = jobs[0]
    assert "job_id" in job
    assert "status" in job
    assert "filename" in job


def test_home_page():
    r = httpx.get(f"{BASE}/")
    assert r.status_code == 200
    assert "ResearchSensei" in r.text


def test_settings_page():
    r = httpx.get(f"{BASE}/settings")
    assert r.status_code == 200


def test_directions_new_page():
    r = httpx.get(f"{BASE}/directions/new")
    assert r.status_code == 200


def test_upload_page():
    r = httpx.get(f"{BASE}/papers/upload")
    assert r.status_code == 200


def test_learn_page():
    r = httpx.get(f"{BASE}/learn/e2b92219d9aa")
    assert r.status_code == 200


def test_artifacts_download():
    r = httpx.get(f"{BASE}/artifacts/e2b92219d9aa/download", follow_redirects=True)
    # Just check it returns a zip file
    assert r.status_code in (200, 404)
    if r.status_code == 200:
        assert len(r.content) > 100  # Should be a non-empty zip


def test_direction_search():
    r = httpx.post(
        f"{BASE}/api/directions/search",
        json={"query": "test query"},
        timeout=120,
    )
    assert r.status_code == 200
    data = r.json()
    assert "search_id" in data
    assert "query_plan" in data
    assert "candidate_pool" in data
    assert "reading_plan" in data
    # Check if job was generated
    if data.get("job_id"):
        # Verify learn endpoint works
        r2 = httpx.get(f"{BASE}/api/learn/{data['job_id']}/bundle")
        assert r2.status_code == 200


def test_search_generate():
    # First do a search to get a search_id
    r = httpx.post(
        f"{BASE}/api/directions/search",
        json={"query": "test generation"},
        timeout=120,
    )
    if r.status_code == 200:
        search_id = r.json().get("search_id")
        if search_id:
            # Test generate endpoint
            r2 = httpx.post(f"{BASE}/api/searches/{search_id}/generate", timeout=120)
            assert r2.status_code == 200


if __name__ == "__main__":
    print("=" * 60)
    print("ResearchSensei Smoke Test")
    print("=" * 60)

    print("\n1. API Endpoints:")
    run_test("GET /api/jobs", test_get_jobs)
    run_test("GET /api/settings", test_get_settings)
    run_test("POST /api/settings/test", test_settings_test)
    run_test("GET /api/learn/{id}/bundle", test_learn_bundle)
    run_test("GET /api/learn/notfound/bundle (404)", test_learn_bundle_not_found)
    run_test("POST /api/interactive/ask", test_interactive_ask)
    run_test("POST /api/interactive/ask (with context)", test_interactive_ask_with_context)

    print("\n2. HTML Pages:")
    run_test("GET /", test_home_page)
    run_test("GET /settings", test_settings_page)
    run_test("GET /directions/new", test_directions_new_page)
    run_test("GET /papers/upload", test_upload_page)
    run_test("GET /learn/{id}", test_learn_page)

    print("\n3. Job Operations:")
    run_test("GET /api/jobs (list)", test_jobs_list)
    run_test("GET /artifacts/{id}/download", test_artifacts_download)

    print("\n4. Direction Search (may take time):")
    run_test("POST /api/directions/search", test_direction_search)
    run_test("POST /api/searches/{id}/generate", test_search_generate)

    print("\n" + "=" * 60)
    print(f"Results: {PASS} passed, {FAIL} failed")
    print("=" * 60)

    sys.exit(1 if FAIL > 0 else 0)
