import hashlib
import hmac
import json
import os
import pandas as pd
from datetime import datetime, timezone
from typing import Dict, Any, Tuple, List, Optional


def hash_file(filepath: str) -> dict:
    """
    Computes cryptographic hashes and metadata for a given file.

    Args:
        filepath: Path to the file to hash.

    Returns:
        A dictionary containing the sha256 hash, md5 hash, file size in bytes,
        filename, and the ISO 8601 timestamp of acquisition.
    """
    sha256_hash = hashlib.sha256()
    md5_hash = hashlib.md5()

    with open(filepath, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
            md5_hash.update(byte_block)

    file_stat = os.stat(filepath)

    return {
        "sha256": sha256_hash.hexdigest(),
        "md5": md5_hash.hexdigest(),
        "file_size": file_stat.st_size,
        "filename": os.path.basename(filepath),
        "acquired_at": datetime.now(timezone.utc).isoformat()
    }


def hash_dataframe(df: pd.DataFrame) -> str:
    """
    Computes a SHA-256 hash for a pandas DataFrame.

    Args:
        df: The pandas DataFrame to hash.

    Returns:
        The SHA-256 hex digest of the DataFrame's JSON representation.
    """
    records = df.to_dict(orient='records')
    json_bytes = json.dumps(records, sort_keys=True).encode()
    return hashlib.sha256(json_bytes).hexdigest()


def verify_file(filepath: str, expected_sha256: str) -> bool:
    """
    Verifies a file's SHA-256 hash against an expected value.

    Args:
        filepath: Path to the file.
        expected_sha256: The expected SHA-256 hex digest.

    Returns:
        True if the file's hash matches the expected hash, False otherwise.
    """
    if not os.path.exists(filepath):
        return False
    file_info = hash_file(filepath)
    return file_info["sha256"] == expected_sha256


def sign_record(record: dict, secret_key: str) -> str:
    """
    Creates an HMAC-SHA256 signature for a dictionary record.

    Args:
        record: The dictionary record to sign.
        secret_key: The secret key for the HMAC.

    Returns:
        The HMAC-SHA256 hex digest signature.
    """
    json_bytes = json.dumps(record, sort_keys=True).encode()
    return hmac.new(secret_key.encode(), json_bytes, hashlib.sha256).hexdigest()


class EvidenceManifest:
    """
    Manages the chain of custody and integrity of evidence items in a case.
    """

    def __init__(self) -> None:
        """
        Initializes an empty EvidenceManifest.
        """
        self.items: List[Dict[str, Any]] = []
        self.finalized_manifest: Optional[Dict[str, Any]] = None

    def add_item(self, filepath: str, notes: str = "") -> None:
        """
        Hashes a file and adds its metadata to the manifest.

        Args:
            filepath: Path to the file to add.
            notes: Optional notes about the evidence item.
        """
        file_info = hash_file(filepath)
        item_record = {
            "type": "file",
            "filepath": filepath,
            "filename": file_info["filename"],
            "file_size": file_info["file_size"],
            "sha256": file_info["sha256"],
            "md5": file_info["md5"],
            "acquired_at": file_info["acquired_at"],
            "notes": notes
        }
        self.items.append(item_record)

    def add_dataframe(self, df: pd.DataFrame, label: str) -> None:
        """
        Hashes a DataFrame and stores it as a virtual evidence item.

        Args:
            df: The pandas DataFrame to add.
            label: A label to identify the DataFrame.
        """
        sha256_hash = hash_dataframe(df)
        item_record = {
            "type": "dataframe",
            "label": label,
            "sha256": sha256_hash,
            "acquired_at": datetime.now(timezone.utc).isoformat()
        }
        self.items.append(item_record)

    def finalize(self, case_id: str, investigator: str) -> dict:
        """
        Finalizes the manifest, generating a manifest-level hash.

        Args:
            case_id: The ID of the case.
            investigator: The name of the investigator.

        Returns:
            The complete finalized manifest dictionary.
        """
        concatenated_hashes = "".join(item["sha256"] for item in self.items)
        manifest_hash = hashlib.sha256(concatenated_hashes.encode()).hexdigest()

        self.finalized_manifest = {
            "case_id": case_id,
            "investigator": investigator,
            "finalized_at": datetime.now(timezone.utc).isoformat(),
            "items": self.items,
            "manifest_hash": manifest_hash
        }
        return self.finalized_manifest

    def to_json(self, output_path: str) -> None:
        """
        Saves the finalized manifest to a JSON file.

        Args:
            output_path: The path where the JSON file will be saved.

        Raises:
            ValueError: If the manifest has not been finalized yet.
        """
        if self.finalized_manifest is None:
            raise ValueError("Manifest must be finalized before saving to JSON.")

        with open(output_path, "w") as f:
            json.dump(self.finalized_manifest, f, indent=4)

    @staticmethod
    def verify_manifest(manifest_path: str) -> Tuple[bool, List[str]]:
        """
        Verifies a saved manifest by checking the manifest hash and individual file hashes.

        Args:
            manifest_path: Path to the saved manifest JSON file.

        Returns:
            A tuple containing a boolean indicating overall validity,
            and a list of identifiers (filenames or labels) for failed items.
        """
        with open(manifest_path, "r") as f:
            manifest = json.load(f)

        concatenated_hashes = "".join(item["sha256"] for item in manifest.get("items", []))
        expected_manifest_hash = hashlib.sha256(concatenated_hashes.encode()).hexdigest()

        failed_items = []
        all_valid = True

        if manifest.get("manifest_hash") != expected_manifest_hash:
            all_valid = False
            failed_items.append("manifest_hash")

        for item in manifest.get("items", []):
            if item.get("type") == "file":
                if not verify_file(item["filepath"], item["sha256"]):
                    all_valid = False
                    failed_items.append(item.get("filename", item["filepath"]))

        return all_valid, failed_items
