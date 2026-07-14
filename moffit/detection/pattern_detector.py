import pandas as pd
import numpy as np
from typing import List, Dict, Any

class FraudPatternDetector:
    """
    Fraud Pattern Detector for MOFFIT.
    """

    def analyze(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        Runs all 6 detectors below, returns combined findings list.
        """
        findings = []
        findings.extend(self.rapid_drain(df))
        findings.extend(self.round_trip(df))
        findings.extend(self.fan_out(df))
        findings.extend(self.fan_in(df))
        findings.extend(self.dormant_activation(df))
        findings.extend(self.balance_inconsistency(df))
        return findings

#rapid drain

    def rapid_drain(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        rapid_drain(df): sender_balance_after < 0.1 * sender_balance_before
        AND amount > 0 within a 5-step window -> confidence = 0.90
        """
        findings = []
        if df.empty or 'sender_id' not in df.columns:
            return findings

        # Vectorized pre-filter: an account can only fire if its minimum
        # balance_after is below 10% of its maximum balance_before.
        g = df.groupby('sender_id')
        stats = g.agg(
            max_before=('sender_balance_before', 'max'),
            min_after=('sender_balance_after', 'min'),
            max_amount=('amount', 'max'),
        )
        candidates = stats[
            (stats['max_before'] > 0)
            & (stats['min_after'] < 0.1 * stats['max_before'])
            & (stats['max_amount'] > 0)
        ].index

        sub = df[df['sender_id'].isin(candidates)]
        for sender_id, group in sub.groupby('sender_id'):
            group = group.sort_values('step')
            found = False
            for i in range(len(group)):
                start_row = group.iloc[i]
                for j in range(i, len(group)):
                    end_row = group.iloc[j]
                    if end_row['step'] - start_row['step'] > 5:
                        break

                    window = group.iloc[i:j+1]
                    total_amount = window['amount'].sum()
                    balance_before = start_row['sender_balance_before']
                    balance_after = end_row['sender_balance_after']

                    if balance_before > 0 and balance_after < 0.1 * balance_before and total_amount > 0:
                        findings.append({
                            "pattern": "rapid_drain",
                            "account_id": sender_id,
                            "step_start": int(start_row['step']),
                            "step_end": int(end_row['step']),
                            "amount": float(total_amount),
                            "confidence": 0.90,
                            "description": "Rapid drain detected"
                        })
                        found = True
                        break
                if found:
                    break
        return findings

    def round_trip(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        round_trip(df): funds A->B->A within 10 steps, same approximate amount (+-5%)
        → confidence = 0.85
        """
        findings = []
        if df.empty or 'sender_id' not in df.columns or 'receiver_id' not in df.columns:
            return findings

        merged = df.merge(df, left_on=['sender_id', 'receiver_id'], right_on=['receiver_id', 'sender_id'], suffixes=('_1', '_2'))
        valid = merged[(merged['step_2'] >= merged['step_1']) & (merged['step_2'] - merged['step_1'] <= 10)]
        # Use amount_1 > 0 to avoid division by zero
        valid = valid[valid['amount_1'] > 0]
        valid = valid[abs(valid['amount_1'] - valid['amount_2']) / valid['amount_1'] <= 0.05]

        for _, row in valid.iterrows():
            findings.append({
                "pattern": "round_trip",
                "account_id": row['sender_id_1'],
                "step_start": int(row['step_1']),
                "step_end": int(row['step_2']),
                "amount": float(row['amount_1']),
                "confidence": 0.85,
                "description": f"Round trip: {row['sender_id_1']} -> {row['receiver_id_1']} -> {row['sender_id_1']}"
            })
        return findings

#fan out

    def fan_out(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        fan_out(df): account sends to >5 unique receivers within 10 steps
        -> confidence = 0.75
        """
        findings = []
        if df.empty or 'sender_id' not in df.columns:
            return findings

        # Vectorized pre-filter: can't reach >5 unique receivers in any window
        # without >5 unique receivers overall.
        overall = df.groupby('sender_id')['receiver_id'].nunique()
        candidates = overall[overall > 5].index

        sub = df[df['sender_id'].isin(candidates)]
        for sender_id, group in sub.groupby('sender_id'):
            group = group.sort_values('step')
            for i in range(len(group)):
                start_step = group.iloc[i]['step']
                window = group[(group['step'] >= start_step) & (group['step'] <= start_step + 10)]
                unique_receivers = window['receiver_id'].nunique()
                if unique_receivers > 5:
                    findings.append({
                        "pattern": "fan_out",
                        "account_id": sender_id,
                        "step_start": int(start_step),
                        "step_end": int(window['step'].max()),
                        "amount": float(window['amount'].sum()),
                        "confidence": 0.75,
                        "description": f"Fan out to {unique_receivers} receivers"
                    })
                    break
        return findings

#Fan in

    def fan_in(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        fan_in(df): account receives from >5 unique senders within 10 steps
        → confidence = 0.70
        """
        findings = []
        if df.empty or 'receiver_id' not in df.columns:
            return findings

        overall = df.groupby('receiver_id')['sender_id'].nunique()
        candidates = overall[overall > 5].index
        sub = df[df['receiver_id'].isin(candidates)]

        for receiver_id, group in sub.groupby('receiver_id'):
            group = group.sort_values('step')
            found = False
            for i in range(len(group)):
                start_step = group.iloc[i]['step']
                window = group[(group['step'] >= start_step) & (group['step'] <= start_step + 10)]
                unique_senders = window['sender_id'].nunique()
                if unique_senders > 5:
                    findings.append({
                        "pattern": "fan_in",
                        "account_id": receiver_id,
                        "step_start": int(start_step),
                        "step_end": int(window['step'].max()),
                        "amount": float(window['amount'].sum()),
                        "confidence": 0.70,
                        "description": f"Fan in from {unique_senders} senders"
                    })
                    found = True
                    break
        return findings

#dormant activation

    def dormant_activation(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        dormant_activation(df): account with <3 prior txns suddenly sends
        amount > median(all account tx amounts) * 2 -> confidence = 0.80
        """
        findings = []
        if df.empty or 'sender_id' not in df.columns or 'receiver_id' not in df.columns or 'amount' not in df.columns:
            return findings

        global_median = df['amount'].median()
        threshold = global_median * 2

        df_sorted = df.sort_values('step').reset_index(drop=True)
        n = len(df_sorted)

        # Interleaved participation sequence: row0-sender, row0-receiver, row1-sender, ...
        # cumcount per account = number of prior participations, exactly matching
        # the original loop's tx_counts semantics.
        import numpy as np
        accounts = np.column_stack([
            df_sorted['sender_id'].to_numpy(),
            df_sorted['receiver_id'].to_numpy(),
        ]).ravel()
        ev = pd.DataFrame({'account': accounts})
        prior = ev.groupby('account').cumcount().to_numpy()
        sender_prior = prior[0::2]  # sender events sit at even positions

        mask = (sender_prior < 3) & (df_sorted['amount'].to_numpy() > threshold)

        for _, row in df_sorted[mask].iterrows():
            findings.append({
                "pattern": "dormant_activation",
                "account_id": row['sender_id'],
                "step_start": int(row['step']),
                "step_end": int(row['step']),
                "amount": float(row['amount']),
                "confidence": 0.80,
                "description": "Dormant account activation"
            })
        return findings

    def balance_inconsistency(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        balance_inconsistency(df): abs(sender_balance_before - sender_balance_after
        - amount) > 0.01 -> confidence = 1.0 (data integrity flag).
        Emitted as a single dataset-level finding: on PaySim, balance
        non-reconciliation is a pervasive dataset property (annulled fraud
        transactions, zeroed merchant balances), not an account-level signal.
        """
        findings = []
        if df.empty or 'sender_balance_before' not in df.columns or 'sender_balance_after' not in df.columns or 'amount' not in df.columns:
            return findings

        mask = abs(df['sender_balance_before'] - df['sender_balance_after'] - df['amount']) > 0.01
        n_bad = int(mask.sum())
        if n_bad == 0:
            return findings

        rate = n_bad / len(df)
        findings.append({
            "pattern": "balance_inconsistency",
            "account_id": "DATASET",
            "step_start": int(df.loc[mask, 'step'].min()),
            "step_end": int(df.loc[mask, 'step'].max()),
            "amount": float(df.loc[mask, 'amount'].sum()),
            "confidence": 1.0,
            "description": f"{n_bad} of {len(df)} transactions ({rate:.1%}) fail balance reconciliation - evidence-level data integrity flag"
        })
        return findings
