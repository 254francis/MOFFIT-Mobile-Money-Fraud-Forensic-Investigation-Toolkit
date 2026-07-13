import os
import pytest
import hashlib
from moffit.custody.case_db import CaseManager, Case, Evidence, Finding

def test_case_manager_init(tmp_path):
    db_path = tmp_path / "test_case.db"
    manager = CaseManager(str(db_path))
    assert os.path.exists(db_path)

def test_create_case(tmp_path):
    db_path = tmp_path / "test_case.db"
    manager = CaseManager(str(db_path))

    case = manager.create_case(
        name="Test Case",
        description="A test case",
        investigator="Test Investigator"
    )

    assert case.id is not None
    assert case.name == "Test Case"
    assert case.description == "A test case"
    assert case.investigator == "Test Investigator"
    assert case.status == "open"

    cases = manager.list_cases()
    assert len(cases) == 1
    assert cases[0].id == case.id

def test_add_evidence(tmp_path):
    db_path = tmp_path / "test_case.db"
    manager = CaseManager(str(db_path))

    case = manager.create_case(
        name="Test Case",
        description="A test case",
        investigator="Test Investigator"
    )

    # Create a dummy evidence file
    evidence_path = tmp_path / "evidence.txt"
    with open(evidence_path, "w") as f:
        f.write("test data")

    expected_md5 = hashlib.md5(b"test data").hexdigest()
    expected_sha256 = hashlib.sha256(b"test data").hexdigest()

    evidence = manager.add_evidence(
        case_id=case.id,
        filepath=str(evidence_path),
        notes="Test evidence"
    )

    assert evidence.id is not None
    assert evidence.case_id == case.id
    assert evidence.filename == "evidence.txt"
    assert evidence.file_size == 9
    assert evidence.md5_hash == expected_md5
    assert evidence.sha256_hash == expected_sha256
    assert evidence.notes == "Test evidence"

def test_add_finding(tmp_path):
    db_path = tmp_path / "test_case.db"
    manager = CaseManager(str(db_path))

    case = manager.create_case(
        name="Test Case",
        description="A test case",
        investigator="Test Investigator"
    )

    finding = manager.add_finding(
        case_id=case.id,
        finding_type="Fan-out",
        severity="high",
        description="Suspicious fan-out behavior detected",
        account_ids=["A123", "B456", "C789"],
        step_start=1,
        step_end=10,
        confidence=0.85
    )

    assert finding.id is not None
    assert finding.case_id == case.id
    assert finding.finding_type == "Fan-out"
    assert finding.severity == "high"
    assert finding.description == "Suspicious fan-out behavior detected"
    assert finding.account_ids == ["A123", "B456", "C789"]
    assert finding.step_start == 1
    assert finding.step_end == 10
    assert finding.confidence == 0.85

    findings = manager.get_findings(case.id)
    assert len(findings) == 1
    assert findings[0].id == finding.id

def test_get_case_summary(tmp_path):
    db_path = tmp_path / "test_case.db"
    manager = CaseManager(str(db_path))

    case = manager.create_case(
        name="Test Case",
        description="A test case",
        investigator="Test Investigator"
    )

    # Add evidence
    evidence_path = tmp_path / "evidence.txt"
    with open(evidence_path, "w") as f:
        f.write("test data")
    manager.add_evidence(case.id, str(evidence_path))

    # Add findings
    manager.add_finding(case.id, "Type1", "high", "desc", ["A"], 1, 2, 0.9)
    manager.add_finding(case.id, "Type2", "high", "desc", ["B"], 1, 2, 0.8)
    manager.add_finding(case.id, "Type3", "medium", "desc", ["C"], 1, 2, 0.5)

    summary = manager.get_case_summary(case.id)

    assert summary["case"]["id"] == case.id
    assert summary["evidence_count"] == 1
    assert summary["findings_count"] == 3
    assert summary["findings_by_severity"]["high"] == 2
    assert summary["findings_by_severity"]["medium"] == 1
    assert summary["findings_by_severity"]["low"] == 0

def test_invalid_case_id(tmp_path):
    db_path = tmp_path / "test_case.db"
    manager = CaseManager(str(db_path))

    evidence_path = tmp_path / "evidence.txt"
    with open(evidence_path, "w") as f:
        f.write("test data")

    with pytest.raises(ValueError):
        manager.add_evidence("invalid-id", str(evidence_path))

    with pytest.raises(ValueError):
        manager.add_finding("invalid-id", "Type", "high", "desc", ["A"], 1, 2, 0.9)

    with pytest.raises(ValueError):
        manager.get_case_summary("invalid-id")
