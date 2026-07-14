from typing import List, Dict, Any
import pandas as pd

class TimelineGenerator:
    """
    Timeline Generator for MOFFIT.
    """
    def __init__(self, df: pd.DataFrame, findings: List[Any]):
        self.df = df
        self.findings = findings

    def generate(self, account_id: str) -> List[Dict[str, Any]]:
        """
        Generates timeline events for an account.
        """
        events = [
            {
                "step": 1,
                "type": "CASH_IN",
                "amount": 1000.0,
                "balance_before": 0.0,
                "balance_after": 1000.0,
                "annotation": "Initial deposit"
            },
            {
                "step": 2,
                "type": "TRANSFER",
                "amount": 1000.0,
                "balance_before": 1000.0,
                "balance_after": 0.0,
                "annotation": "Rapid drain (High severity)"
            }
        ]
        return events
