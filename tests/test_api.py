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
    assert "Home" in response.text


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

@app.get("/case/{id}/report")
async def download_report(id: str):
    report_path = _generate_report_sync(id)
    return FileResponse(report_path, media_type="application/pdf", filename=f"MOFFIT_report_{id}.pdf")

@app.get("/case/{id}/report/preview")
async def preview_report(id: str):
    report_path = _generate_report_sync(id)
    return FileResponse(
        report_path,
        media_type="application/pdf",
        filename=f"MOFFIT_report_{id}.pdf",
        headers={"Content-Disposition": f"inline; filename=MOFFIT_report_{id}.pdf"}
    )

@app.get("/case/{id}/graph/{account}", response_class=HTMLResponse)
async def case_graph(request: Request, id: str, account: str):
    evidence_list = manager.get_evidence(id)
    loader = PaySimLoader()
    builder = TransactionGraph()

    df = None
    for ev in evidence_list:
        filepath = ev.filename
        if os.path.exists(filepath) and str(filepath).lower().endswith(".csv"):
            df = loader.normalize(loader.load_csv(filepath))
            break

    if df is None:
        return HTMLResponse("No valid CSV evidence found for this case.", status_code=404)

    full_graph = builder.build(df)

    if account not in full_graph:
        return HTMLResponse(f"Account {account} not found in the transaction graph.", status_code=404)

    # Get ego network (depth=1)
    ego_net = builder.get_ego_network(full_graph, account, depth=1)

    # Cap neighbors if > 50
    neighbors = list(ego_net.nodes())
    if account in neighbors:
        neighbors.remove(account)

    is_truncated = False
    if len(neighbors) > 50:
        is_truncated = True
        def neighbor_volume(n):
            vol = 0
            if full_graph.has_edge(account, n):
                vol += full_graph[account][n].get('amount', 0)
            if full_graph.has_edge(n, account):
                vol += full_graph[n][account].get('amount', 0)
            return vol

        neighbors.sort(key=neighbor_volume, reverse=True)
        top_neighbors = set(neighbors[:50])
        top_neighbors.add(account)
        ego_net = ego_net.subgraph(top_neighbors).copy()

    nodes = []
    for n in ego_net.nodes():
        stats = ego_net.nodes[n]
        node_data = {
            "id": n,
            "total_sent": stats.get("total_sent", 0),
            "total_received": stats.get("total_received", 0),
            "is_flagged": stats.get("is_flagged", False)
        }
        nodes.append(node_data)

    edges = []
    for u, v, data in ego_net.edges(data=True):
        edges.append({
            "source": u,
            "target": v,
            "amount": data.get("amount", 0),
            "step": data.get("step", 0),
            "tx_type": data.get("tx_type", "")
        })

    return templates.TemplateResponse(
        request=request, name="graph.html", context={
            "case_id": id,
            "account_id": account,
            "nodes_json": json.dumps(nodes),
            "edges_json": json.dumps(edges),
            "is_truncated": is_truncated
        }
    )
