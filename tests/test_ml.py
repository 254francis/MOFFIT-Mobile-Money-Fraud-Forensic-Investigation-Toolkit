import pytest
import pandas as pd
import numpy as np
import os
from moffit.ml.features import FeatureEngineer
from moffit.ml.classifier import FraudClassifier
from moffit.ml.evaluate import evaluate_all

def test_feature_engineer_no_leakage():
    # 20 row fixture
    df = pd.DataFrame({
        'step': np.arange(1, 21),
        'tx_type': np.random.choice(['TRANSFER', 'CASH_OUT'], size=20),
        'amount': np.random.uniform(10, 500, size=20),
        'sender_id': ['A', 'B'] * 10,
        'sender_balance_before': np.random.uniform(100, 1000, size=20),
        'sender_balance_after': np.random.uniform(0, 500, size=20),
        'receiver_id': ['X', 'Y'] * 10,
        'receiver_balance_before': np.random.uniform(0, 200, size=20),
        'receiver_balance_after': np.random.uniform(100, 500, size=20),
        'is_fraud': np.zeros(20)
    })

    # Introduce some values to check leakage
    # Sender A has tx at steps 1, 3, 5, 7, 9...
    fe = FeatureEngineer()
    features = fe.transform(df)

    # Check no NaNs
    assert not features.isnull().any().any()

    # Expected columns
    expected_cols = [
        "amount", "tx_type_CASH_IN", "tx_type_CASH_OUT", "tx_type_DEBIT",
        "tx_type_PAYMENT", "tx_type_TRANSFER", "balance_change_ratio",
        "sender_drained", "balance_mismatch", "receiver_prior_tx_count",
        "sender_tx_velocity", "amount_vs_sender_median", "hour_of_day"
    ]
    assert all(col in features.columns for col in expected_cols)

    # Verify receiver_prior_tx_count is strictly increasing starting from 0
    x_txs = features[df['receiver_id'] == 'X']
    assert list(x_txs['receiver_prior_tx_count']) == list(range(10))

    # Verify sender_tx_velocity starts at 0 for first tx
    assert features.loc[0, 'sender_tx_velocity'] == 0.0

def test_classifier_imbalanced():
    # 500 row fixture, 2% positive
    n_samples = 500
    np.random.seed(42)
    X = pd.DataFrame(np.random.randn(n_samples, 5), columns=[f'f_{i}' for i in range(5)])

    # 10 frauds
    y = pd.Series(np.zeros(n_samples))
    y[:10] = 1

    # Needs to shuffle
    idx = np.random.permutation(n_samples)
    X = X.iloc[idx].reset_index(drop=True)
    y = y.iloc[idx].reset_index(drop=True)

    clf = FraudClassifier("xgboost")
    clf.train(X, y)

    probs = clf.predict_proba(clf.X_test)
    preds = (probs >= 0.5).astype(int)

    # Not guaranteed to have recall > 0 on completely random data,
    # Let's add some signal
    X.loc[y == 1, 'f_0'] += 10

    clf = FraudClassifier("xgboost")
    clf.train(X, y)

    probs = clf.predict_proba(clf.X_test)
    preds = (probs >= 0.5).astype(int)

    # Should be easy to detect now
    assert sum((preds == 1) & (clf.y_test == 1)) > 0

def test_evaluate_all(tmp_path):
    df = pd.DataFrame({
        'step': np.arange(1, 101),
        'tx_type': np.random.choice(['TRANSFER', 'CASH_OUT'], size=100),
        'amount': np.random.uniform(10, 500, size=100),
        'sender_id': np.random.choice(['A', 'B', 'C'], size=100),
        'sender_balance_before': np.random.uniform(100, 1000, size=100),
        'sender_balance_after': np.random.uniform(0, 500, size=100),
        'receiver_id': np.random.choice(['X', 'Y', 'Z'], size=100),
        'receiver_balance_before': np.random.uniform(0, 200, size=100),
        'receiver_balance_after': np.random.uniform(100, 500, size=100),
        'is_fraud': np.random.choice([0, 1], size=100, p=[0.9, 0.1])
    })

    output_dir = str(tmp_path)
    metrics = evaluate_all(df, output_dir)

    for model in ["logistic", "random_forest", "xgboost"]:
        assert model in metrics
        assert all(k in metrics[model] for k in ["precision", "recall", "f1", "auprc", "roc_auc"])

    assert os.path.exists(os.path.join(output_dir, "metrics.json"))
    assert os.path.exists(os.path.join(output_dir, "pr_curves.png"))
    assert os.path.exists(os.path.join(output_dir, "shap_summary.png"))
