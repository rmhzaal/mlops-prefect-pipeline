import json
import joblib
from prefect import flow, task, get_run_logger
from sklearn.datasets import load_breast_cancer
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score


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


@task
def save_artifacts(model, scaler, metrics):
    joblib.dump(model, "models/model.joblib")
    joblib.dump(scaler, "models/scaler.joblib")
    with open("models/metrics.json", "w") as f:
        json.dump(metrics, f, indent=2)


@flow(name="ml-pipeline")
def ml_pipeline():
    X_train, X_test, y_train, y_test, scaler = load_and_preprocess()
    model = train_model(X_train, y_train)
    metrics = evaluate_model(model, X_test, y_test)
    save_artifacts(model, scaler, metrics)
    return metrics


if __name__ == "__main__":
    ml_pipeline()
