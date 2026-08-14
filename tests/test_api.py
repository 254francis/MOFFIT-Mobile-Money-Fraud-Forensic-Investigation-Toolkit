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


def test_post_case_upload_csv(tmp_path):
    # Set EVIDENCE_DIR for testing
    os.environ["EVIDENCE_DIR"] = str(tmp_path / "evidence_store")

    case = manager.create_case("Upload Test", "Desc", "Inv")

    # Create an in-memory CSV file
    file_content = b"step,type,amount,nameOrig,oldbalanceOrg,newbalanceOrig,nameDest,oldbalanceDest,newbalanceDest,isFraud,isFlaggedFraud\n1,PAYMENT,1060.31,C429214117,1089.0,28.69,M1591654462,0.0,0.0,0,0\n"
    files = {"file": ("test_evidence.csv", file_content, "text/csv")}

    response = client.post(f"/case/{case.id}/upload", files=files, follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == f"/case/{case.id}"

    evidence = manager.get_evidence(case.id)
    assert len(evidence) == 1
    assert evidence[0].sha256_hash != ""

def test_post_case_upload_non_csv():
    case = manager.create_case("Upload Test 2", "Desc", "Inv")

    file_content = b"This is just a text file."
    files = {"file": ("test.txt", file_content, "text/plain")}

    response = client.post(f"/case/{case.id}/upload", files=files, follow_redirects=False)

    assert response.status_code == 400


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

def test_case_timeline_has_chart_data():
    case = manager.create_case("Chart Test", "Desc", "Inv")
    import tempfile
    import os
    fd, path = tempfile.mkstemp(suffix=".csv")
    with os.fdopen(fd, 'w') as f:
        f.write("step,type,amount,nameOrig,oldbalanceOrg,newbalanceOrig,nameDest,oldbalanceDest,newbalanceDest,isFlaggedFraud,isFraud\n")
        f.write("1,TRANSFER,1000.0,C123,5000.0,4000.0,C456,1000.0,2000.0,0,0\n")
        f.write("3,TRANSFER,4000.0,C123,4000.0,0.0,C456,1000.0,5000.0,1,1\n")
    manager.add_evidence(case.id, path)
    manager.add_finding(case.id, "rapid_drain", "high", "Drained", ["C123", "C456"], 1, 4, 0.99)
    response = client.get(f"/case/{case.id}/timeline/C123")
    assert response.status_code == 200
    assert "chart_data" in response.text or "Chart" in response.text

def test_get_findings_html_returns_fragment():
    # First create a case
    case = manager.create_case("Findings Test", "Desc", "Inv")
    # Add some findings
    manager.add_finding(case.id, "Pattern A", "high", "Desc", ["A"], 1, 2, 0.9)
    manager.add_finding(case.id, "Pattern B", "low", "Desc", ["B"], 1, 2, 0.4)
    # GET /case/{id}/findings?page=1
    response = client.get(f"/case/{case.id}/findings?page=1")
    assert response.status_code == 200
    assert "Pattern A" in response.text
    assert "Pattern B" in response.text
    assert "id=\"findings-table-container\"" in response.text

def test_get_findings_html_respects_severity():
    case = manager.create_case("Severity Test", "Desc", "Inv")
    manager.add_finding(case.id, "Pattern A", "high", "Desc", ["A"], 1, 2, 0.9)
    manager.add_finding(case.id, "Pattern B", "low", "Desc", ["B"], 1, 2, 0.4)
    response = client.get(f"/case/{case.id}/findings?page=1&severity=high")
    assert response.status_code == 200
    assert "Pattern A" in response.text
    assert "<td>Pattern B</td>" not in response.text
