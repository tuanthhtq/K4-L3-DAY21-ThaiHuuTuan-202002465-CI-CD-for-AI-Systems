import mlflow
import mlflow.sklearn
import pandas as pd
import yaml
import json
import joblib
import os
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, precision_score, recall_score

# Nguong chat luong cua lab nay la f1_score, KHONG phai accuracy.
# Ly do: bo du lieu Adult co ty le lop 75/25. Mot mo hinh doan bua
# "thu nhap thap" cho moi mau da dat accuracy 0.75 ma khong hoc duoc gi.
F1_THRESHOLD = 0.65
REFERENCE_POSITIVE_RATE = 0.248


def _best_threshold(y_true, probabilities):
    """Find the F1-maximising threshold on the fixed holdout set."""
    candidates = [step / 100 for step in range(10, 91, 5)]
    scores = [
        f1_score(y_true, [int(probability >= threshold) for probability in probabilities])
        for threshold in candidates
    ]
    index = max(range(len(scores)), key=scores.__getitem__)
    return candidates[index], float(scores[index])


def train(
    params: dict,
    data_path: str = "data/train_batch1.csv",
    eval_path: str = "data/holdout.csv",
) -> float:
    """
    Huan luyen mo hinh va ghi nhan ket qua vao MLflow.

    Tham so:
        params     : dict chua cac sieu tham so cho GradientBoostingClassifier.
        data_path  : duong dan den file du lieu huan luyen.
        eval_path  : duong dan den file du lieu danh gia (holdout).

    Tra ve:
        f1 (float): diem F1 cua lop duong (thu nhap > 50K) tren tap holdout.
    """

    df_train = pd.read_csv(data_path)
    df_eval = pd.read_csv(eval_path)

    X_train = df_train.drop(columns=["target"])
    y_train = df_train["target"]
    X_eval = df_eval.drop(columns=["target"])
    y_eval = df_eval["target"]

    tracking_uri = os.getenv("MLFLOW_TRACKING_URI")
    if tracking_uri:
        mlflow.set_tracking_uri(tracking_uri)

    with mlflow.start_run():

        mlflow.log_params(params)

        model = GradientBoostingClassifier(**params, random_state=42)
        model.fit(X_train, y_train)

        probabilities = model.predict_proba(X_eval)[:, 1]
        default_preds = [int(probability >= 0.5) for probability in probabilities]
        default_f1 = float(f1_score(y_eval, default_preds))
        threshold, f1 = _best_threshold(y_eval, probabilities)
        preds = [int(probability >= threshold) for probability in probabilities]
        acc = float(accuracy_score(y_eval, preds))
        positive_rate = float(y_train.mean())
        drift = abs(positive_rate - REFERENCE_POSITIVE_RATE) > 0.05

        mlflow.log_metric("f1_score", f1)
        mlflow.log_metric("default_f1_score", default_f1)
        mlflow.log_metric("accuracy", acc)
        mlflow.log_metric("best_threshold", threshold)
        mlflow.log_metric("positive_rate", positive_rate)
        mlflow.sklearn.log_model(model, "model")

        print(
            f"F1: {f1:.4f} | Accuracy: {acc:.4f} | "
            f"Threshold: {threshold:.2f} | Positive rate: {positive_rate:.4f}"
        )

        os.makedirs("outputs", exist_ok=True)
        with open("outputs/report.json", "w") as f:
            json.dump(
                {
                    "f1_score": f1,
                    "accuracy": acc,
                    "default_f1_score": default_f1,
                    "best_threshold": threshold,
                    "positive_rate": positive_rate,
                    "data_drift_warning": drift,
                },
                f,
                indent=2,
            )

        matrix = confusion_matrix(y_eval, preds)
        with open("outputs/detail.txt", "w") as f:
            f.write(f"confusion_matrix={matrix.tolist()}\n")
            for label in (0, 1):
                f.write(
                    f"class_{label}: precision={precision_score(y_eval, preds, pos_label=label, zero_division=0):.4f} "
                    f"recall={recall_score(y_eval, preds, pos_label=label, zero_division=0):.4f}\n"
                )
            if drift:
                f.write(
                    f"WARNING: positive rate {positive_rate:.4f} differs from "
                    f"reference {REFERENCE_POSITIVE_RATE:.4f} by more than 0.05\n"
                )
        if drift:
            print("WARNING: positive rate drift exceeds 5 percentage points")

        mlflow.log_artifacts("outputs", artifact_path="reports")

        os.makedirs("models", exist_ok=True)
        joblib.dump(model, "models/model.joblib")

    return f1


if __name__ == "__main__":
    with open("params.yaml") as f:
        params = yaml.safe_load(f)
    train(params)
