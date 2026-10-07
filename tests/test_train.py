import os
import json
import mlflow
import numpy as np
import pandas as pd
from src.train import _best_threshold, train


FEATURE_NAMES = [
    "age", "workclass", "education_num", "marital_status", "occupation",
    "relationship", "sex", "capital_gain", "capital_loss", "hours_per_week",
]


def _make_temp_data(tmp_path):
    """
    Tao dataset nho voi cung schema Adult de su dung trong test.

    pytest cung cap `tmp_path` la mot thu muc tam thoi, tu dong xoa sau khi test ket thuc.
    Ham nay dung du lieu ngau nhien nen khong can ket noi cloud storage hay tai file CSV thuc.
    """
    rng = np.random.default_rng(0)
    n = 200

    X = rng.random((n, len(FEATURE_NAMES)))

    y = rng.integers(0, 2, size=n)

    df = pd.DataFrame(X, columns=FEATURE_NAMES)
    df["target"] = y

    train_path = str(tmp_path / "train.csv")
    eval_path = str(tmp_path / "holdout.csv")
    df.iloc[:160].to_csv(train_path, index=False)
    df.iloc[160:].to_csv(eval_path, index=False)

    return train_path, eval_path


def test_best_threshold():
    threshold, score = _best_threshold([0, 1], [0.4, 0.6])
    assert threshold == 0.45
    assert score == 1.0


def test_train_returns_float(tmp_path, monkeypatch):
    """Kiem tra ham train() tra ve mot so thuc nam trong [0.0, 1.0]."""
    train_path, eval_path = _make_temp_data(tmp_path)
    monkeypatch.chdir(tmp_path)
    mlflow.set_tracking_uri((tmp_path / "mlruns").as_uri())

    f1 = train(
        {"n_estimators": 10, "learning_rate": 0.1, "max_depth": 2},
        data_path=train_path,
        eval_path=eval_path,
    )

    assert isinstance(f1, float)
    assert 0.0 <= f1 <= 1.0


def test_report_file_created(tmp_path, monkeypatch):
    """Kiem tra file outputs/report.json duoc tao sau khi huan luyen."""
    train_path, eval_path = _make_temp_data(tmp_path)
    monkeypatch.chdir(tmp_path)
    mlflow.set_tracking_uri((tmp_path / "mlruns").as_uri())
    train(
        {"n_estimators": 10, "learning_rate": 0.1, "max_depth": 2},
        data_path=train_path,
        eval_path=eval_path,
    )

    assert os.path.exists("outputs/report.json")
    with open("outputs/report.json") as f:
        report = json.load(f)
    assert "f1_score" in report
    assert "accuracy" in report
    assert 0.1 <= report["best_threshold"] <= 0.9
    assert "default_f1_score" in report
    assert "positive_rate" in report
    assert "data_drift_warning" in report
    assert os.path.exists("outputs/detail.txt")
    assert "class_1: precision=" in open("outputs/detail.txt").read()


def test_model_file_created(tmp_path, monkeypatch):
    """Kiem tra file models/model.joblib duoc tao sau khi huan luyen."""
    train_path, eval_path = _make_temp_data(tmp_path)
    monkeypatch.chdir(tmp_path)
    mlflow.set_tracking_uri((tmp_path / "mlruns").as_uri())
    train(
        {"n_estimators": 10, "learning_rate": 0.1, "max_depth": 2},
        data_path=train_path,
        eval_path=eval_path,
    )

    assert os.path.exists("models/model.joblib")
