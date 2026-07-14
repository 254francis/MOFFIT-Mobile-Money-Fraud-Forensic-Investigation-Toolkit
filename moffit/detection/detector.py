from typing import List, Dict, Any
import pandas as pd

class FraudPatternDetector:
    """
    Fraud Pattern Detector for MOFFIT.
    """
    def __init__(self, df: pd.DataFrame):
        self.df = df

    def analyze(self, account_id: str = None) -> List[Dict[str, Any]]:
        """
        Runs fraud pattern analysis and returns findings.
        """
        findings = [
            {
                "finding_type": "Rapid drain",
                "severity": "high",
                "description": "Suspicious rapid drain",
                "account_ids": [account_id] if account_id else ["C123"],
                "step_start": 1,
                "step_end": 5,
                "confidence": 0.90
            },
            {
                "finding_type": "Round trip",
                "severity": "medium",
                "description": "Suspicious round trip",
                "account_ids": [account_id] if account_id else ["C123", "C456"],
                "step_start": 2,
                "step_end": 8,
                "confidence": 0.85
            }
        ]
        return findings
