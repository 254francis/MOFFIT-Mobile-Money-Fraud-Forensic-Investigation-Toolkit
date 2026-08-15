"""High-level ML pipeline helpers shared by the CLI and the web API.

Neither consumer should reconstruct the pipeline directly. Any change to
how features are computed, models are loaded, or accounts are ranked
belongs here.
"""
from pathlib import Path
import pandas as pd

from moffit.ml.features import FeatureEngineer
from moffit.ml.classifier import FraudClassifier


def rank_accounts_for_case(df: pd.DataFrame, model_path: str | Path) -> pd.DataFrame:
    """Return a DataFrame of accounts ranked by fraud probability.

    df: normalized transaction DataFrame (from PaySimLoader.normalize).
    model_path: path to a trained classifier joblib file.
    """
    fe = FeatureEngineer()
    X = fe.transform(df)
    clf = FraudClassifier.load(model_path)
return clf.rank_accounts(df, X)
