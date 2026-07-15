import pandas as pd
import numpy as np

class FeatureEngineer:
    """
    Feature Engineer for generating ML features from normalized PaySim data.
    """

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Transforms the normalized PaySim DataFrame into a feature matrix.

        Args:
            df (pd.DataFrame): Normalized PaySim DataFrame.

        Returns:
            pd.DataFrame: Feature matrix containing the engineered features.
        """
        # Make a copy to avoid SettingWithCopyWarning
        features = df.copy()
        original_index = features.index

        # Keep track of an internal ID BEFORE sorting so we can properly align later
        features["_row_id"] = np.arange(len(features))

        # We need to sort by step to prevent leakage, but we must restore the original index later
        features = features.sort_values("step")

        # Base features
        features["amount"] = features["amount"].astype(float)
        features["hour_of_day"] = (features["step"] % 24).astype(float)

        # One-hot encoding for tx_type
        tx_types = ["CASH_IN", "CASH_OUT", "DEBIT", "PAYMENT", "TRANSFER"]
        for tx_type in tx_types:
            features[f"tx_type_{tx_type}"] = (features["tx_type"] == tx_type).astype(float)

        # Balance change ratio: amount / (sender_balance_before + 1)
        features["balance_change_ratio"] = features["amount"] / (features["sender_balance_before"] + 1.0)

        # Sender drained: 1 if sender_balance_after < 0.1 * sender_balance_before else 0
        features["sender_drained"] = (features["sender_balance_after"] < 0.1 * features["sender_balance_before"]).astype(float)

        # Balance mismatch: abs(sender_balance_before - amount - sender_balance_after) > 0.01
        features["balance_mismatch"] = (np.abs(features["sender_balance_before"] - features["amount"] - features["sender_balance_after"]) > 0.01).astype(float)

        # receiver_prior_tx_count: rolling count of receiver's prior transactions
        # We need past transactions only. Group by receiver_id, use cumulative count - 1
        features["receiver_prior_tx_count"] = features.groupby("receiver_id").cumcount().astype(float)

        # amount_vs_sender_median: amount / (sender's historical median amount + 1)
        # Note: must be calculated while sorted chronologically to avoid data leakage
        features["historical_median"] = features.groupby("sender_id")["amount"].transform(lambda x: x.shift(1).expanding().median())
        features["historical_median"] = features["historical_median"].fillna(0.0)
        features["amount_vs_sender_median"] = features["amount"] / (features["historical_median"] + 1.0)

        # sender_tx_velocity: sender's transaction count in the prior 10 steps
        # To avoid future data, we set index to 'step' as timedelta, group by sender, count last 10 hours excluding current (closed='left')
        features["time_idx"] = pd.to_timedelta(features["step"], unit="h")

        # An easier way is to map back using the exact order per group
        # Sort features by sender_id and time_idx (step)
        sorted_by_group = features.sort_values(["sender_id", "step"])
        sorted_by_group.set_index("time_idx", inplace=True)

        counts = (
            sorted_by_group.groupby("sender_id")["step"]
            .rolling("10h", closed="left")
            .count()
            .values
        )

        sorted_by_group["sender_tx_velocity"] = counts
        sorted_by_group["sender_tx_velocity"] = sorted_by_group["sender_tx_velocity"].fillna(0.0).astype(float)

        # Now restore the original row order
        features = sorted_by_group.sort_values("_row_id").reset_index(drop=True)

        columns_to_keep = [
            "amount",
            "tx_type_CASH_IN",
            "tx_type_CASH_OUT",
            "tx_type_DEBIT",
            "tx_type_PAYMENT",
            "tx_type_TRANSFER",
            "balance_change_ratio",
            "sender_drained",
            "balance_mismatch",
            "receiver_prior_tx_count",
            "sender_tx_velocity",
            "amount_vs_sender_median",
            "hour_of_day"
        ]

        # The index is currently 0..N-1 aligned with original row positions
        features.index = original_index

        return features[columns_to_keep]
