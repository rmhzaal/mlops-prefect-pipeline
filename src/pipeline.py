import io
import json
import os

import boto3
import joblib
import requests
from botocore.exceptions import ClientError
from dotenv import load_dotenv
from prefect import flow, task, get_run_logger
from sklearn.datasets import load_breast_cancer
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score

load_dotenv()
AWS_REGION = os.getenv("AWS_REGION", "eu-west-2")
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")
TEAMS_WEBHOOK_SECRET_NAME = os.getenv("TEAMS_WEBHOOK_SECRET_NAME", "mlops-prefect-pipeline/teams-webhook-url")

secrets_client = boto3.client("secretsmanager", region_name=AWS_REGION)
s3_client = boto3.client("s3", region_name=AWS_REGION)


def get_teams_webhook_url():
    try:
        response = secrets_client.get_secret_value(SecretId=TEAMS_WEBHOOK_SECRET_NAME)
        return response["SecretString"]
    except ClientError:
        return None


def notify_teams_failure(flow, flow_run, state):
    webhook_url = get_teams_webhook_url()
    if not webhook_url:
        return
    payload = {
        "type": "message",
        "attachments": [{
            "contentType": "application/vnd.microsoft.card.adaptive",
            "content": {
                "type": "AdaptiveCard",
                "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                "version": "1.4",
                "body": [
                    {"type": "TextBlock", "text": "\U0001F534 ml-pipeline flow run failed", "weight": "bolder", "size": "medium"},
                    {"type": "TextBlock", "text": f"Flow run: {flow_run.name}", "wrap": True},
                    {"type": "TextBlock", "text": f"State: {state.name}", "wrap": True},
                ],
            },
        }],
    }
    requests.post(webhook_url, json=payload, timeout=10)


@task(retries=2, retry_delay_seconds=10)
def load_and_preprocess():
    data = load_breast_cancer()
    X_train, X_test, y_train, y_test = train_test_split(
        data.data, data.target, test_size=0.2, random_state=42, stratify=data.target
    )
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    return X_train_scaled, X_test_scaled, y_train, y_test, scaler


@task
def train_model(X_train, y_train):
    model = LogisticRegression(max_iter=1000)
    model.fit(X_train, y_train)
    return model


@task
def evaluate_model(model, X_test, y_test):
    logger = get_run_logger()
    predictions = model.predict(X_test)
    metrics = {
        "accuracy": accuracy_score(y_test, predictions),
        "precision": precision_score(y_test, predictions),
        "recall": recall_score(y_test, predictions),
        "f1": f1_score(y_test, predictions),
    }
    logger.info(f"Evaluation metrics: {metrics}")
    return metrics


@task(retries=2, retry_delay_seconds=10)
def save_artifacts(model, scaler, metrics):
    logger = get_run_logger()

    model_buffer = io.BytesIO()
    joblib.dump(model, model_buffer)
    model_buffer.seek(0)

    scaler_buffer = io.BytesIO()
    joblib.dump(scaler, scaler_buffer)
    scaler_buffer.seek(0)

    s3_client.put_object(Bucket=S3_BUCKET_NAME, Key="models/model.joblib", Body=model_buffer.getvalue())
    s3_client.put_object(Bucket=S3_BUCKET_NAME, Key="models/scaler.joblib", Body=scaler_buffer.getvalue())
    s3_client.put_object(Bucket=S3_BUCKET_NAME, Key="models/metrics.json", Body=json.dumps(metrics, indent=2))

    logger.info(f"Artifacts written to s3://{S3_BUCKET_NAME}/models/")


@flow(name="ml-pipeline", on_failure=[notify_teams_failure])
def ml_pipeline():
    X_train, X_test, y_train, y_test, scaler = load_and_preprocess()
    model = train_model(X_train, y_train)
    metrics = evaluate_model(model, X_test, y_test)
    save_artifacts(model, scaler, metrics)
    return metrics


if __name__ == "__main__":
    ml_pipeline()
