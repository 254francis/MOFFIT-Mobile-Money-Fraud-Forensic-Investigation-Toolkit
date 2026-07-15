import os
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.metrics import precision_score, recall_score, f1_score, roc_auc_score, average_precision_score, confusion_matrix, precision_recall_curve
from .features import FeatureEngineer
from .classifier import FraudClassifier

def evaluate_all(df: pd.DataFrame, output_dir: str) -> dict:
    """
    Trains all three model types, evaluates them, and generates reporting artifacts.

    Args:
        df (pd.DataFrame): Normalized PaySim DataFrame containing 'is_fraud' column.
        output_dir (str): Directory to save artifacts (metrics.json, plots).

    Returns:
        dict: The calculated metrics for all models.
    """
    os.makedirs(output_dir, exist_ok=True)

    # 1. Feature Engineering
    fe = FeatureEngineer()
    X = fe.transform(df)

    # Check if target 'is_fraud' exists in original df
    if "is_fraud" not in df.columns:
        raise ValueError("DataFrame must contain 'is_fraud' column for training and evaluation.")

    y = df.loc[X.index, "is_fraud"].astype(int)

    models = {
        "logistic": FraudClassifier("logistic"),
        "random_forest": FraudClassifier("random_forest"),
        "xgboost": FraudClassifier("xgboost")
    }

    metrics = {}
    pr_curves_data = {}

    # 2. Train and Evaluate each model
    for name, clf in models.items():
        clf.train(X, y)

        # Evaluate on the held-out test set
        X_test = clf.X_test
        y_test = clf.y_test

        y_probs = clf.predict_proba(X_test)

        # Calculate optimal F1 threshold
        precisions, recalls, thresholds = precision_recall_curve(y_test, y_probs)
        # Avoid division by zero
        f1_scores = np.divide(2 * (precisions * recalls), (precisions + recalls), out=np.zeros_like(precisions), where=(precisions + recalls) != 0)

        # The threshold maximizing F1
        best_idx = np.argmax(f1_scores)
        best_threshold = thresholds[best_idx] if best_idx < len(thresholds) else 0.5

        y_pred_best = (y_probs >= best_threshold).astype(int)

        # Metrics
        precision = precision_score(y_test, y_pred_best, zero_division=0)
        recall = recall_score(y_test, y_pred_best, zero_division=0)
        f1 = f1_score(y_test, y_pred_best, zero_division=0)
        auprc = average_precision_score(y_test, y_probs)

        # Handle cases where test set only has 1 class
        try:
            roc_auc = roc_auc_score(y_test, y_probs)
        except ValueError:
            roc_auc = float('nan')

        metrics[name] = {
            "precision": float(precision),
            "recall": float(recall),
            "f1": float(f1),
            "auprc": float(auprc),
            "roc_auc": float(roc_auc),
            "best_threshold": float(best_threshold)
        }

        pr_curves_data[name] = (precisions, recalls)

        # Confusion matrix
        cm = confusion_matrix(y_test, y_pred_best)
        metrics[name]["confusion_matrix"] = cm.tolist()

        # Save model
        clf.save(os.path.join(output_dir, f"{name}_model.joblib"))

    # 3. Save metrics to json
    with open(os.path.join(output_dir, "metrics.json"), "w") as f:
        json.dump(metrics, f, indent=4)

    # 4. Plot Precision-Recall Curves
    plt.figure(figsize=(8, 6))
    for name, (precisions, recalls) in pr_curves_data.items():
        plt.plot(recalls, precisions, label=name)
    plt.xlabel("Recall")
    plt.ylabel("Precision")
    plt.title("Precision-Recall Curve Comparison")
    plt.legend()
    plt.grid(True)
    plt.savefig(os.path.join(output_dir, "pr_curves.png"), bbox_inches="tight")
    plt.close()

    # 5. XGBoost Feature Importance
    xgb_clf = models["xgboost"]
    import xgboost as xgb

    # Extract importances
    booster = xgb_clf.model.get_booster()
    importance_dict = booster.get_score(importance_type="gain")

    if importance_dict:
        # Sort and take top 15
        sorted_importance = sorted(importance_dict.items(), key=lambda x: x[1], reverse=False)[-15:]
        features, gains = zip(*sorted_importance)

        plt.figure(figsize=(10, 6))
        plt.barh(features, gains, color='skyblue')
        plt.xlabel("Gain")
        plt.title("Top 15 Feature Importances (XGBoost)")
        plt.grid(axis='x')
        plt.savefig(os.path.join(output_dir, "feature_importance.png"), bbox_inches="tight")
        plt.close()

    # 6. SHAP Summary Plot
    import shap
    shap_X = X.sample(n=min(5000, len(X)), random_state=42)
    explainer = shap.TreeExplainer(xgb_clf.model)
    shap_values = explainer.shap_values(shap_X)

    plt.figure()
    shap.summary_plot(shap_values, shap_X, show=False)
    plt.savefig(os.path.join(output_dir, "shap_summary.png"), bbox_inches="tight")
    plt.close()

    return metrics
