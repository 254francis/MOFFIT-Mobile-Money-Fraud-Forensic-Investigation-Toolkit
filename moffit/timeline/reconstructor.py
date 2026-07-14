from dataclasses import dataclass, asdict
from typing import List, Dict, Any
import pandas as pd

@dataclass
class TimelineEvent:
    """Represents a single transaction event involving an account."""
    step: int
    event_type: str
    amount: float
    counterparty: str
    balance_before: float
    balance_after: float
    annotation: str
    is_flagged: bool


class TimelineReconstructor:
    """Reconstructs and analyzes chronological attack sequences from transaction logs."""

    def build_account_timeline(self, df: pd.DataFrame, account_id: str) -> List[TimelineEvent]:
        """
        Returns chronological list of all events touching account_id.
        Determine event_type from tx_type column + direction (sender vs receiver).
        """
        events = []
        if df.empty:
            return events

        # Filter rows where account_id is either sender or receiver
        mask = (df['sender_id'] == account_id) | (df['receiver_id'] == account_id)
        account_df = df[mask].sort_values(by='step')

        for _, row in account_df.iterrows():
            is_sender = (row['sender_id'] == account_id)

            if is_sender:
                counterparty = str(row['receiver_id'])
                balance_before = float(row['sender_balance_before'])
                balance_after = float(row['sender_balance_after'])
            else:
                counterparty = str(row['sender_id'])
                balance_before = float(row['receiver_balance_before'])
                balance_after = float(row['receiver_balance_after'])

            event_type = str(row['tx_type'])

            # Additional safety check for nan/null in bool flags
            is_flagged = bool(row.get('is_flagged', False))

            event = TimelineEvent(
                step=int(row['step']),
                event_type=event_type,
                amount=float(row['amount']),
                counterparty=counterparty,
                balance_before=balance_before,
                balance_after=balance_after,
                annotation="",
                is_flagged=is_flagged
            )
            events.append(event)

        return events

    def annotate_events(self, events: List[TimelineEvent], findings: List[Dict[str, Any]]) -> List[TimelineEvent]:
        """
        Enriches events with pattern labels from findings.
        """
        for event in events:
            annotations = []
            if event.annotation:
                annotations.append(event.annotation)

            for finding in findings:
                # Assuming finding dictionary structure based on detection module
                if finding.get('step_start', 0) <= event.step <= finding.get('step_end', float('inf')):
                    pattern = finding.get('pattern', '')
                    if pattern == 'rapid_drain':
                        annotations.append("[RAPID DRAIN]")
                    elif pattern == 'dormant_activation':
                        annotations.append("[DORMANT ACTIVATION]")

            if event.balance_after < 0.01 * event.balance_before:
                annotations.append("[ACCOUNT DRAINED]")

            if event.event_type == 'TRANSFER' and event.is_flagged:
                annotations.append("[FLAGGED BY PAYSIM]")

            # Deduplicate annotations and keep order
            unique_annotations = []
            for ann in annotations:
                if ann not in unique_annotations:
                    unique_annotations.append(ann)

            event.annotation = " ".join(unique_annotations).strip()

        return events

    def generate_narrative(self, events: List[TimelineEvent], account_id: str, findings: List[Dict[str, Any]]) -> str:
        """
        Returns a 3-5 sentence plain-English description of the attack sequence.
        """
        if not events:
            return f"No transaction events found for account {account_id}."

        total_amount = sum(e.amount for e in events)

        # Find first suspicious step based on findings
        first_suspicious_step = None
        primary_pattern = "suspicious activity"

        if findings:
            # Sort findings by start step
            sorted_findings = sorted(findings, key=lambda f: f.get('step_start', float('inf')))
            first_finding = sorted_findings[0]
            first_suspicious_step = first_finding.get('step_start')
            primary_pattern = first_finding.get('pattern', primary_pattern).replace('_', ' ')

        # If no findings, try to find flagged events
        if first_suspicious_step is None:
            for e in events:
                if e.is_flagged:
                    first_suspicious_step = e.step
                    primary_pattern = "flagged transactions"
                    break

        if first_suspicious_step is None:
            first_suspicious_step = events[0].step

        narrative = (
            f"The forensic analysis of account {account_id} reveals a sequence of "
            f"{len(events)} transaction events indicative of {primary_pattern}. "
        )
        narrative += f"The suspicious sequence commenced at step {first_suspicious_step}, marking the start of the detected pattern. "
        narrative += f"Throughout the observed timeline, a total amount of {total_amount:.2f} was moved through the account. "

        if findings:
            narrative += f"The primary detected mechanism driving this anomaly is classified as {primary_pattern}."
        else:
            narrative += "These movements exhibit characteristics consistent with unauthorized or anomalous financial flows."

        return narrative

    def to_dict_list(self, events: List[TimelineEvent]) -> List[Dict[str, Any]]:
        """
        Converts a list of TimelineEvent objects to a list of dictionaries.
        """
        return [asdict(event) for event in events]
