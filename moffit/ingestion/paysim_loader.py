import pandas as pd
from typing import Dict, Union, Any

class PaySimLoader:
    """
    A loader class for PaySim CSV data ingestion and normalization.
    """

    def load_csv(self, path: str) -> pd.DataFrame:
        """
        Loads a PaySim CSV file into a pandas DataFrame.

        Args:
            path (str): The file path to the PaySim CSV.

        Returns:
            pd.DataFrame: The loaded raw DataFrame.
        """
        return pd.read_csv(path)

    def normalize(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Normalizes the PaySim DataFrame by renaming columns and casting types.

        The expected original columns are:
        step, type, amount, nameOrig, oldbalanceOrg, newbalanceOrig,
        nameDest, oldbalanceDest, newbalanceDest, isFraud, isFlaggedFraud

        The target columns are:
        step, tx_type, amount, sender_id, sender_balance_before,
        sender_balance_after, receiver_id, receiver_balance_before,
        receiver_balance_after, is_fraud, is_flagged

        Types will be cast to: step=int, amount=float, is_fraud=bool.

        Args:
            df (pd.DataFrame): The raw PaySim DataFrame.

        Returns:
            pd.DataFrame: The normalized DataFrame.
        """
        df_normalized = df.rename(columns={
            "step": "step",
            "type": "tx_type",
            "amount": "amount",
            "nameOrig": "sender_id",
            "oldbalanceOrg": "sender_balance_before",
            "newbalanceOrig": "sender_balance_after",
            "nameDest": "receiver_id",
            "oldbalanceDest": "receiver_balance_before",
            "newbalanceDest": "receiver_balance_after",
            "isFraud": "is_fraud",
            "isFlaggedFraud": "is_flagged"
        })

        df_normalized["step"] = df_normalized["step"].astype(int)
        df_normalized["amount"] = df_normalized["amount"].astype(float)
        df_normalized["is_fraud"] = df_normalized["is_fraud"].astype(bool)

        # is_flagged can also be bool or int, but requirements only said step, amount, is_fraud.
        # I'll leave is_flagged as is unless it's strictly needed.

        return df_normalized

    def filter_by_account(self, df: pd.DataFrame, account_id: str) -> pd.DataFrame:
        """
        Filters the DataFrame to include only transactions involving the specified account ID.

        Args:
            df (pd.DataFrame): The normalized PaySim DataFrame.
            account_id (str): The account ID to filter by.

        Returns:
            pd.DataFrame: The filtered DataFrame containing only rows where the
                          account_id is either the sender or receiver.
        """
        return df[(df["sender_id"] == account_id) | (df["receiver_id"] == account_id)]

    def filter_by_timerange(self, df: pd.DataFrame, start_step: int, end_step: int) -> pd.DataFrame:
        """
        Filters the DataFrame to include only transactions within a specific step range (inclusive).

        Args:
            df (pd.DataFrame): The normalized PaySim DataFrame.
            start_step (int): The starting step.
            end_step (int): The ending step.

        Returns:
            pd.DataFrame: The filtered DataFrame containing rows within the time range.
        """
        return df[(df["step"] >= start_step) & (df["step"] <= end_step)]

    def get_account_history(self, df: pd.DataFrame, account_id: str) -> Dict[str, Any]:
        """
        Generates transaction history statistics and DataFrames for a specific account.

        Args:
            df (pd.DataFrame): The normalized PaySim DataFrame.
            account_id (str): The account ID to analyze.

        Returns:
            Dict[str, Any]: A dictionary with the following keys:
                            - 'sent': DataFrame of transactions sent by the account.
                            - 'received': DataFrame of transactions received by the account.
                            - 'total_sent': float, total amount sent.
                            - 'total_received': float, total amount received.
                            - 'tx_count': int, total number of transactions (sent + received).
        """
        sent_df = df[df["sender_id"] == account_id]
        received_df = df[df["receiver_id"] == account_id]

        total_sent = sent_df["amount"].sum()
        total_received = received_df["amount"].sum()
        tx_count = len(sent_df) + len(received_df)

        return {
            "sent": sent_df,
            "received": received_df,
            "total_sent": float(total_sent),
            "total_received": float(total_received),
            "tx_count": int(tx_count)
        }
