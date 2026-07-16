import pandas as pd
import numpy as np
import joblib
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
import xgboost as xgb
from typing import Literal

class FraudClassifier:
    """
    Supervised ML model for classifying fraud transactions.
    """

    def __init__(self, model_type: Literal["logistic", "random_forest", "xgboost"] = "xgboost"):
        self.model_type = model_type
        self.model = None
        self.X_test = None
        self.y_test = None

    def train(self, X: pd.DataFrame, y: pd.Series) -> None:
        """
        Trains the classifier with a 70/15/15 train/val/test split and stores the test set.

        Args:
            X (pd.DataFrame): Feature matrix.
            y (pd.Series): Target vector (fraud labels).
        """
        # Stratified 70/15/15 split
        # First split off 30% for val + test
        X_train, X_temp, y_train, y_temp = train_test_split(
            X, y, test_size=0.30, stratify=y, random_state=42
        )
        # Split the 30% into 15% val and 15% test
        X_val, X_test, y_val, y_test = train_test_split(
            X_temp, y_temp, test_size=0.50, stratify=y_temp, random_state=42
        )

        self.X_test = X_test
        self.y_test = y_test

        n_positive = y_train.sum()
        n_negative = len(y_train) - n_positive

        if self.model_type == "logistic":
            self.model = LogisticRegression(class_weight="balanced", random_state=42, max_iter=1000)
            self.model.fit(X_train, y_train)
        elif self.model_type == "random_forest":
            self.model = RandomForestClassifier(class_weight="balanced", random_state=42, n_estimators=100)
            self.model.fit(X_train, y_train)
        elif self.model_type == "xgboost":
            scale_pos_weight = n_negative / n_positive if n_positive > 0 else 1.0
            self.model = xgb.XGBClassifier(
                scale_pos_weight=scale_pos_weight,
                random_state=42,
                eval_metric="logloss",
                early_stopping_rounds=10
            )
            self.model.fit(
                X_train, y_train,
                eval_set=[(X_val, y_val)],
                verbose=False
            )
        else:
            raise ValueError(f"Unknown model_type: {self.model_type}")

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        """
        Predicts fraud probabilities for the given features.

        Args:
            X (pd.DataFrame): Feature matrix.

        Returns:
            np.ndarray: Probabilities of the positive class (fraud).
        """
        if self.model is None:
            raise RuntimeError("Model is not trained yet.")
        return self.model.predict_proba(X)[:, 1]

    def rank_accounts(self, df: pd.DataFrame, X: pd.DataFrame) -> pd.DataFrame:
        """
        Ranks accounts based on maximum transaction fraud probability.

        Args:
            df (pd.DataFrame): Normalized PaySim DataFrame.
            X (pd.DataFrame): Feature matrix corresponding to df.

        Returns:
            pd.DataFrame: DataFrame containing account_id, max_fraud_probability, tx_count sorted descending.
        """
        if len(df) != len(X):
            raise ValueError("DataFrames df and X must have the same number of rows.")

        probs = self.predict_proba(X)

        # Create a temp dataframe to aggregate. We only rank based on sender_id here for simplicity,
        # or we could rank both sender and receiver. The prompt implies we rank 'accounts'.
        # Let's collect probabilities for all accounts involved (sender and receiver).

        # Senders
        sender_df = pd.DataFrame({
            "account_id": df["sender_id"],
            "fraud_prob": probs,
            "tx_count": 1
        })

        # Receivers
        receiver_df = pd.DataFrame({
            "account_id": df["receiver_id"],
            "fraud_prob": probs,
            "tx_count": 1
        })

        combined_df = pd.concat([sender_df, receiver_df], ignore_index=True)

        ranked_df = combined_df.groupby("account_id").agg(
            max_fraud_probability=("fraud_prob", "max"),
            tx_count=("tx_count", "sum")
        ).reset_index()

        ranked_df = ranked_df.sort_values("max_fraud_probability", ascending=False).reset_index(drop=True)

        return ranked_df

    def save(self, path: str) -> None:
        """Saves the trained model to disk."""
        if self.model is None:
            raise RuntimeError("Model is not trained yet.")
        joblib.dump(self, path)

    @classmethod
    def load(cls, path: str) -> "FraudClassifier":
        """Loads a trained model from disk."""
        return joblib.load(path)
