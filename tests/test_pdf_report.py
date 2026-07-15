import os
import tempfile
import pytest
from moffit.reporting.pdf_report import ForensicReportGenerator

def test_pdf_report_generation():
    generator = ForensicReportGenerator()

    case = {
        "id": "123e4567-e89b-12d3-a456-426614174000",
        "name": "Test Fraud Case",
        "investigator": "Agent Smith",
        "status": "open"
    }

    findings = [
        {
            "finding_type": "rapid_drain",
            "severity": "high",
            "description": "Rapid draining of account",
            "account_ids": ["C12345"],
            "step_start": 1,
            "step_end": 5,
            "confidence": 0.95
        },
        {
            "finding_type": "dormant_activation",
            "severity": "medium",
            "description": "Dormant account activated",
            "account_ids": ["M98765"],
            "step_start": 2,
            "step_end": 3,
            "confidence": 0.80
        },
        {
            "finding_type": "rapid_drain_0",
            "severity": "high",
            "description": "Rapid draining of account padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding",
            "account_ids": ["C12345_0"],
            "step_start": 0,
            "step_end": 5,
            "confidence": 0.95
        },

        {
            "finding_type": "rapid_drain_1",
            "severity": "high",
            "description": "Rapid draining of account padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding",
            "account_ids": ["C12345_1"],
            "step_start": 1,
            "step_end": 6,
            "confidence": 0.95
        },

        {
            "finding_type": "rapid_drain_2",
            "severity": "high",
            "description": "Rapid draining of account padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding",
            "account_ids": ["C12345_2"],
            "step_start": 2,
            "step_end": 7,
            "confidence": 0.95
        },

        {
            "finding_type": "rapid_drain_3",
            "severity": "high",
            "description": "Rapid draining of account padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding",
            "account_ids": ["C12345_3"],
            "step_start": 3,
            "step_end": 8,
            "confidence": 0.95
        },

        {
            "finding_type": "rapid_drain_4",
            "severity": "high",
            "description": "Rapid draining of account padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding",
            "account_ids": ["C12345_4"],
            "step_start": 4,
            "step_end": 9,
            "confidence": 0.95
        },

        {
            "finding_type": "rapid_drain_5",
            "severity": "high",
            "description": "Rapid draining of account padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding",
            "account_ids": ["C12345_5"],
            "step_start": 5,
            "step_end": 10,
            "confidence": 0.95
        },

        {
            "finding_type": "rapid_drain_6",
            "severity": "high",
            "description": "Rapid draining of account padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding",
            "account_ids": ["C12345_6"],
            "step_start": 6,
            "step_end": 11,
            "confidence": 0.95
        },

        {
            "finding_type": "rapid_drain_7",
            "severity": "high",
            "description": "Rapid draining of account padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding",
            "account_ids": ["C12345_7"],
            "step_start": 7,
            "step_end": 12,
            "confidence": 0.95
        },

        {
            "finding_type": "rapid_drain_8",
            "severity": "high",
            "description": "Rapid draining of account padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding",
            "account_ids": ["C12345_8"],
            "step_start": 8,
            "step_end": 13,
            "confidence": 0.95
        },

        {
            "finding_type": "rapid_drain_9",
            "severity": "high",
            "description": "Rapid draining of account padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding",
            "account_ids": ["C12345_9"],
            "step_start": 9,
            "step_end": 14,
            "confidence": 0.95
        },

        {
            "finding_type": "rapid_drain_10",
            "severity": "high",
            "description": "Rapid draining of account padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding",
            "account_ids": ["C12345_10"],
            "step_start": 10,
            "step_end": 15,
            "confidence": 0.95
        },

        {
            "finding_type": "rapid_drain_11",
            "severity": "high",
            "description": "Rapid draining of account padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding",
            "account_ids": ["C12345_11"],
            "step_start": 11,
            "step_end": 16,
            "confidence": 0.95
        },

        {
            "finding_type": "rapid_drain_12",
            "severity": "high",
            "description": "Rapid draining of account padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding",
            "account_ids": ["C12345_12"],
            "step_start": 12,
            "step_end": 17,
            "confidence": 0.95
        },

        {
            "finding_type": "rapid_drain_13",
            "severity": "high",
            "description": "Rapid draining of account padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding",
            "account_ids": ["C12345_13"],
            "step_start": 13,
            "step_end": 18,
            "confidence": 0.95
        },

        {
            "finding_type": "rapid_drain_14",
            "severity": "high",
            "description": "Rapid draining of account padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding",
            "account_ids": ["C12345_14"],
            "step_start": 14,
            "step_end": 19,
            "confidence": 0.95
        },

        {
            "finding_type": "rapid_drain_15",
            "severity": "high",
            "description": "Rapid draining of account padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding",
            "account_ids": ["C12345_15"],
            "step_start": 15,
            "step_end": 20,
            "confidence": 0.95
        },

        {
            "finding_type": "rapid_drain_16",
            "severity": "high",
            "description": "Rapid draining of account padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding",
            "account_ids": ["C12345_16"],
            "step_start": 16,
            "step_end": 21,
            "confidence": 0.95
        },

        {
            "finding_type": "rapid_drain_17",
            "severity": "high",
            "description": "Rapid draining of account padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding",
            "account_ids": ["C12345_17"],
            "step_start": 17,
            "step_end": 22,
            "confidence": 0.95
        },

        {
            "finding_type": "rapid_drain_18",
            "severity": "high",
            "description": "Rapid draining of account padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding",
            "account_ids": ["C12345_18"],
            "step_start": 18,
            "step_end": 23,
            "confidence": 0.95
        },

        {
            "finding_type": "rapid_drain_19",
            "severity": "high",
            "description": "Rapid draining of account padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding",
            "account_ids": ["C12345_19"],
            "step_start": 19,
            "step_end": 24,
            "confidence": 0.95
        },

        {
            "finding_type": "rapid_drain_20",
            "severity": "high",
            "description": "Rapid draining of account padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding",
            "account_ids": ["C12345_20"],
            "step_start": 20,
            "step_end": 25,
            "confidence": 0.95
        },

        {
            "finding_type": "rapid_drain_21",
            "severity": "high",
            "description": "Rapid draining of account padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding",
            "account_ids": ["C12345_21"],
            "step_start": 21,
            "step_end": 26,
            "confidence": 0.95
        },

        {
            "finding_type": "rapid_drain_22",
            "severity": "high",
            "description": "Rapid draining of account padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding",
            "account_ids": ["C12345_22"],
            "step_start": 22,
            "step_end": 27,
            "confidence": 0.95
        },

        {
            "finding_type": "rapid_drain_23",
            "severity": "high",
            "description": "Rapid draining of account padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding",
            "account_ids": ["C12345_23"],
            "step_start": 23,
            "step_end": 28,
            "confidence": 0.95
        },

        {
            "finding_type": "rapid_drain_24",
            "severity": "high",
            "description": "Rapid draining of account padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding",
            "account_ids": ["C12345_24"],
            "step_start": 24,
            "step_end": 29,
            "confidence": 0.95
        },

        {
            "finding_type": "rapid_drain_25",
            "severity": "high",
            "description": "Rapid draining of account padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding",
            "account_ids": ["C12345_25"],
            "step_start": 25,
            "step_end": 30,
            "confidence": 0.95
        },

        {
            "finding_type": "rapid_drain_26",
            "severity": "high",
            "description": "Rapid draining of account padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding",
            "account_ids": ["C12345_26"],
            "step_start": 26,
            "step_end": 31,
            "confidence": 0.95
        },

        {
            "finding_type": "rapid_drain_27",
            "severity": "high",
            "description": "Rapid draining of account padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding",
            "account_ids": ["C12345_27"],
            "step_start": 27,
            "step_end": 32,
            "confidence": 0.95
        },

        {
            "finding_type": "rapid_drain_28",
            "severity": "high",
            "description": "Rapid draining of account padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding",
            "account_ids": ["C12345_28"],
            "step_start": 28,
            "step_end": 33,
            "confidence": 0.95
        },

        {
            "finding_type": "rapid_drain_29",
            "severity": "high",
            "description": "Rapid draining of account padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding",
            "account_ids": ["C12345_29"],
            "step_start": 29,
            "step_end": 34,
            "confidence": 0.95
        },

        {
            "finding_type": "rapid_drain_30",
            "severity": "high",
            "description": "Rapid draining of account padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding",
            "account_ids": ["C12345_30"],
            "step_start": 30,
            "step_end": 35,
            "confidence": 0.95
        },

        {
            "finding_type": "rapid_drain_31",
            "severity": "high",
            "description": "Rapid draining of account padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding",
            "account_ids": ["C12345_31"],
            "step_start": 31,
            "step_end": 36,
            "confidence": 0.95
        },

        {
            "finding_type": "rapid_drain_32",
            "severity": "high",
            "description": "Rapid draining of account padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding",
            "account_ids": ["C12345_32"],
            "step_start": 32,
            "step_end": 37,
            "confidence": 0.95
        },

        {
            "finding_type": "rapid_drain_33",
            "severity": "high",
            "description": "Rapid draining of account padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding",
            "account_ids": ["C12345_33"],
            "step_start": 33,
            "step_end": 38,
            "confidence": 0.95
        },

        {
            "finding_type": "rapid_drain_34",
            "severity": "high",
            "description": "Rapid draining of account padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding",
            "account_ids": ["C12345_34"],
            "step_start": 34,
            "step_end": 39,
            "confidence": 0.95
        },

        {
            "finding_type": "rapid_drain_35",
            "severity": "high",
            "description": "Rapid draining of account padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding",
            "account_ids": ["C12345_35"],
            "step_start": 35,
            "step_end": 40,
            "confidence": 0.95
        },

        {
            "finding_type": "rapid_drain_36",
            "severity": "high",
            "description": "Rapid draining of account padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding",
            "account_ids": ["C12345_36"],
            "step_start": 36,
            "step_end": 41,
            "confidence": 0.95
        },

        {
            "finding_type": "rapid_drain_37",
            "severity": "high",
            "description": "Rapid draining of account padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding",
            "account_ids": ["C12345_37"],
            "step_start": 37,
            "step_end": 42,
            "confidence": 0.95
        },

        {
            "finding_type": "rapid_drain_38",
            "severity": "high",
            "description": "Rapid draining of account padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding",
            "account_ids": ["C12345_38"],
            "step_start": 38,
            "step_end": 43,
            "confidence": 0.95
        },

        {
            "finding_type": "rapid_drain_39",
            "severity": "high",
            "description": "Rapid draining of account padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding",
            "account_ids": ["C12345_39"],
            "step_start": 39,
            "step_end": 44,
            "confidence": 0.95
        },

        {
            "finding_type": "rapid_drain_40",
            "severity": "high",
            "description": "Rapid draining of account padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding",
            "account_ids": ["C12345_40"],
            "step_start": 40,
            "step_end": 45,
            "confidence": 0.95
        },

        {
            "finding_type": "rapid_drain_41",
            "severity": "high",
            "description": "Rapid draining of account padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding",
            "account_ids": ["C12345_41"],
            "step_start": 41,
            "step_end": 46,
            "confidence": 0.95
        },

        {
            "finding_type": "rapid_drain_42",
            "severity": "high",
            "description": "Rapid draining of account padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding",
            "account_ids": ["C12345_42"],
            "step_start": 42,
            "step_end": 47,
            "confidence": 0.95
        },

        {
            "finding_type": "rapid_drain_43",
            "severity": "high",
            "description": "Rapid draining of account padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding",
            "account_ids": ["C12345_43"],
            "step_start": 43,
            "step_end": 48,
            "confidence": 0.95
        },

        {
            "finding_type": "rapid_drain_44",
            "severity": "high",
            "description": "Rapid draining of account padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding",
            "account_ids": ["C12345_44"],
            "step_start": 44,
            "step_end": 49,
            "confidence": 0.95
        },

        {
            "finding_type": "rapid_drain_45",
            "severity": "high",
            "description": "Rapid draining of account padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding",
            "account_ids": ["C12345_45"],
            "step_start": 45,
            "step_end": 50,
            "confidence": 0.95
        },

        {
            "finding_type": "rapid_drain_46",
            "severity": "high",
            "description": "Rapid draining of account padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding",
            "account_ids": ["C12345_46"],
            "step_start": 46,
            "step_end": 51,
            "confidence": 0.95
        },

        {
            "finding_type": "rapid_drain_47",
            "severity": "high",
            "description": "Rapid draining of account padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding",
            "account_ids": ["C12345_47"],
            "step_start": 47,
            "step_end": 52,
            "confidence": 0.95
        },

        {
            "finding_type": "rapid_drain_48",
            "severity": "high",
            "description": "Rapid draining of account padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding",
            "account_ids": ["C12345_48"],
            "step_start": 48,
            "step_end": 53,
            "confidence": 0.95
        },

        {
            "finding_type": "rapid_drain_49",
            "severity": "high",
            "description": "Rapid draining of account padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding",
            "account_ids": ["C12345_49"],
            "step_start": 49,
            "step_end": 54,
            "confidence": 0.95
        },

    ]

    timeline_map = {
        "C12345": [
            {
                "step": 1,
                "event_type": "TRANSFER_SENDER",
                "amount": 1000.0,
                "balance_before": 1000.0,
                "balance_after": 0.0,
                "annotation": "[RAPID DRAIN]"
            }
        ]
    }

    custody = {
        "case_id": "123e4567-e89b-12d3-a456-426614174000",
        "investigator": "Agent Smith",
        "manifest_hash": "dummy_hash",
        "items": [
            {
                "type": "file",
                "filename": "test.csv",
                "sha256": "abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
                "acquired_at": "2023-10-27T10:00:00Z"
            }
        ]
    }

    narrative = "The forensic analysis reveals anomalous transactions..."

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        output_path = tmp.name

    try:
        generator.generate(case, findings, timeline_map, custody, narrative, output_path)

        assert os.path.exists(output_path)
        # Expected to be large since we have fonts, formatting, multiple pages
        assert os.path.getsize(output_path) > 15000
    finally:
        if os.path.exists(output_path):
            os.remove(output_path)
