import importlib
import os
import sys

import boto3
import joblib
import pytest
from fastapi import HTTPException


class FakeS3:
    def download_file(self, bucket, key, path):
        assert bucket == "test-bucket"
        assert key == "artifacts/current/model.joblib"


class FakeModel:
    def predict(self, rows):
        return [1 if rows[0][2] >= 10 else 0]


@pytest.fixture
def serve(monkeypatch, tmp_path):
    monkeypatch.setenv("ARTIFACT_BUCKET", "test-bucket")
    monkeypatch.setattr(os.path, "expanduser", lambda _: str(tmp_path / "model.joblib"))
    monkeypatch.setattr(boto3, "client", lambda service: FakeS3())
    monkeypatch.setattr(joblib, "load", lambda path: FakeModel())
    sys.modules.pop("src.serve", None)
    return importlib.import_module("src.serve")


def test_health_and_score(serve):
    assert serve.healthz() == {"status": "ok"}
    request = serve.ScoreRequest(features=[28, 2, 14, 2, 11, 0, 1, 0, 0, 45])
    assert serve.score(request) == {"prediction": 1, "label": "thu_nhap_cao"}


def test_score_rejects_wrong_feature_count(serve):
    with pytest.raises(HTTPException) as error:
        serve.score(serve.ScoreRequest(features=[1, 2]))
    assert error.value.status_code == 400
