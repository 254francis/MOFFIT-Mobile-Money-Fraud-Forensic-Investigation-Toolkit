import os
import json
import pytest
import pandas as pd
from moffit.custody.integrity import (
    hash_file,
    hash_dataframe,
    verify_file,
    sign_record,
    EvidenceManifest
)

def test_hash_file_and_verify(tmp_path):
    # Create a temp file
    test_file = tmp_path / "test.txt"
    test_file.write_text("Hello, world!")

    # Hash it
    file_info = hash_file(str(test_file))

    assert "sha256" in file_info
    assert "md5" in file_info
    assert "file_size" in file_info
    assert "filename" in file_info
    assert "acquired_at" in file_info

    assert file_info["filename"] == "test.txt"
    assert file_info["file_size"] == len(b"Hello, world!")

    # Verify it passes
    assert verify_file(str(test_file), file_info["sha256"]) is True

    # Modify it
    test_file.write_text("Hello, modified world!")

    # Verify it fails
    assert verify_file(str(test_file), file_info["sha256"]) is False


def test_hash_dataframe():
    df = pd.DataFrame({"col1": [1, 2], "col2": ["A", "B"]})
    df_hash = hash_dataframe(df)
    assert isinstance(df_hash, str)
    assert len(df_hash) == 64  # SHA-256 hex digest length


def test_sign_record():
    record = {"case_id": "123", "status": "open"}
    secret_key = "super_secret_key"

    signature = sign_record(record, secret_key)

    assert isinstance(signature, str)
    assert len(signature) == 64

    # Tamper with the record
    tampered_record = {"case_id": "123", "status": "closed"}
    tampered_signature = sign_record(tampered_record, secret_key)

    assert signature != tampered_signature


def test_evidence_manifest(tmp_path):
    # Create temp files
    file1 = tmp_path / "file1.txt"
    file1.write_text("Evidence 1")
    file2 = tmp_path / "file2.txt"
    file2.write_text("Evidence 2")

    manifest = EvidenceManifest()

    # Test add_item
    manifest.add_item(str(file1), "Notes for file 1")
    manifest.add_item(str(file2))

    assert len(manifest.items) == 2
    assert manifest.items[0]["filepath"] == str(file1)

    # Test add_dataframe
    df = pd.DataFrame({"col": [1, 2, 3]})
    manifest.add_dataframe(df, "Test DF")

    assert len(manifest.items) == 3
    assert manifest.items[2]["type"] == "dataframe"
    assert manifest.items[2]["label"] == "Test DF"

    # Test finalize
    finalized = manifest.finalize("CASE-001", "Investigator Smith")

    assert finalized["case_id"] == "CASE-001"
    assert finalized["investigator"] == "Investigator Smith"
    assert "finalized_at" in finalized
    assert "manifest_hash" in finalized
    assert len(finalized["items"]) == 3

    # Test to_json
    json_path = tmp_path / "manifest.json"
    manifest.to_json(str(json_path))

    assert json_path.exists()

    # Test verify_manifest (valid)
    all_valid, failed_items = manifest.verify_manifest(str(json_path))
    assert all_valid is True
    assert len(failed_items) == 0

    # Test verify_manifest with tampered file (invalid)
    file1.write_text("Tampered Evidence 1")
    all_valid, failed_items = manifest.verify_manifest(str(json_path))
    assert all_valid is False
    assert "file1.txt" in failed_items

    # Restore file1
    file1.write_text("Evidence 1")

    # Test verify_manifest with tampered manifest hash (invalid)
    with open(str(json_path), "r") as f:
        tampered_manifest_data = json.load(f)

    tampered_manifest_data["manifest_hash"] = "0000000000000000000000000000000000000000000000000000000000000000"

    with open(str(json_path), "w") as f:
        json.dump(tampered_manifest_data, f)

    all_valid, failed_items = manifest.verify_manifest(str(json_path))
    assert all_valid is False
    assert "manifest_hash" in failed_items
