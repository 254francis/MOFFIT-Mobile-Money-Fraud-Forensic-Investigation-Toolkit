import os
import pytest
from fastapi.testclient import TestClient

# We need to override the DB path for testing before importing the app
test_db_path = "test_api_moffit.db"
os.environ["MOFFIT_DB"] = test_db_path

from moffit.api.main import app, manager
from moffit.custody.case_db import Base

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_teardown():
    # Setup
    if os.path.exists(test_db_path):
        os.remove(test_db_path)
    # the sqlite engine needs to be recreated if the file was deleted
    manager.engine.dispose()

    # Re-initialize DB tables for clean slate
    Base.metadata.create_all(manager.engine)

    yield

    # Teardown
    if os.path.exists(test_db_path):
        os.remove(test_db_path)


def test_get_index_returns_200():
    response = client.get("/")
    assert response.status_code == 200
    assert "MOFFIT Dashboard" in response.text


def test_post_case_creates_and_redirects():
    # Create case via POST
    data = {
        "name": "Test Web Case",
        "investigator": "Agent Web",
        "description": "Created via API test"
    }
    response = client.post("/case", data=data, follow_redirects=False)

    # Check for redirect to case detail
    assert response.status_code == 303
    assert "location" in response.headers

    location = response.headers["location"]
    case_id = location.split("/")[-1]

    # Verify it exists in DB
    cases = manager.list_cases()
    assert len(cases) == 1
    assert cases[0].id == case_id
    assert cases[0].name == "Test Web Case"


def test_get_case_status_returns_json():
    # First create a case
    case = manager.create_case("Status Test", "Desc", "Inv")

    # GET /case/{id}/status
    response = client.get(f"/case/{case.id}/status")
    assert response.status_code == 200

    data = response.json()
    assert "analyzing" in data
    assert "findings_count" in data
    assert data["analyzing"] is False
    assert data["findings_count"] == 0
