import os
import pytest
from fastapi.testclient import TestClient

# We need to override the DB path for testing before importing the app
test_db_path = "test_api_moffit.db"
os.environ["CASE_DB_PATH"] = test_db_path

from moffit.api.main import app, manager
from moffit.custody.case_db import Base

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_teardown():
    # Setup: release the engine's file handle BEFORE deleting (Windows locks open files)
    manager.engine.dispose()
    if os.path.exists(test_db_path):
        os.remove(test_db_path)
    # Re-initialize DB tables for clean slate
    Base.metadata.create_all(manager.engine)
    yield
    # Teardown
    manager.engine.dispose()
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

def test_get_case_graph_no_evidence():
    case = manager.create_case("Graph Test", "Desc", "Inv")
    response = client.get(f"/case/{case.id}/graph/ACC123")
    assert response.status_code == 404
    assert "No valid CSV evidence found" in response.text

def test_get_case_graph_success(tmp_path):
    case = manager.create_case("Graph Success Test", "Desc", "Inv")

    # Create dummy evidence
    csv_file = tmp_path / "dummy_paysim.csv"
    csv_file.write_text("step,type,amount,nameOrig,oldbalanceOrg,newbalanceOrig,nameDest,oldbalanceDest,newbalanceDest,isFraud,isFlaggedFraud\n1,PAYMENT,100.0,ACC1,0,0,ACC2,0,0,0,0")

    manager.add_evidence(case.id, str(csv_file))

    response = client.get(f"/case/{case.id}/graph/ACC1")
    assert response.status_code == 200
    assert "vis-network" in response.text
    assert "ACC1" in response.text
    assert "nodes_json" not in response.text # Just to be sure variables are evaluated
