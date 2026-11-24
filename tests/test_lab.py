"""Pruebas ejecutables del contrato del Lab 1.

Los nombres describen el comportamiento esperado. Cada prueba prepara un caso,
ejecuta una unidad pequeña y comprueba una evidencia observable.
"""

import json
import sys
from pathlib import Path

import pytest

from frc_incidents.classifier import tokenize
from frc_incidents.cli import main
from frc_incidents.domain import DomainValidationError, Incident, Prediction
from frc_incidents.repositories import IncidentCsvRepository
from frc_incidents.service import IncidentClassificationService, JsonPredictionWriter, PriorityPolicy


# Dominio: los datos imposibles deben fallar antes de llegar al clasificador.
def test_incident_rejects_negative_amount() -> None:
    with pytest.raises(DomainValidationError):
        Incident("INC-X", "Descripción válida", -1, False)


def test_prediction_rejects_invalid_confidence_and_priority() -> None:
    with pytest.raises(DomainValidationError, match="confidence"):
        Prediction("INC-X", "transfer_risk", 1.1, "HIGH", "Explicación válida")
    with pytest.raises(DomainValidationError, match="priority"):
        Prediction("INC-X", "transfer_risk", 0.8, "URGENT", "Explicación válida")


def test_csv_repository_loads_synthetic_incidents(tmp_path) -> None:
    # ``tmp_path`` aísla el archivo de prueba y evita modificar el dataset del Lab.
    source = tmp_path / "incidents.csv"
    source.write_text("incident_id,description,amount_eur,urgent\nINC-1,Transferencia duplicada detectada,30.5,true\n", encoding="utf-8")
    assert IncidentCsvRepository().load(source)[0].urgent is True


def test_csv_repository_rejects_invalid_urgent(tmp_path: Path) -> None:
    source = tmp_path / "invalid.csv"
    source.write_text(
        "incident_id,description,amount_eur,urgent\n"
        "INC-1,Transferencia duplicada detectada,30.5,yes\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="urgent debe ser true o false"):
        IncidentCsvRepository().load(source)


def test_classifier_tokenizes_and_predicts(classifier) -> None:
    assert tokenize("¡TRANSFERENCIA, sospechosa!") == ["transferencia", "sospechosa"]
    category, confidence = classifier.predict("Transferencia internacional sospechosa")

    assert category
    assert 0 <= confidence <= 1


@pytest.mark.parametrize(
    ("amount", "urgent", "expected"),
    [
        (20, False, "LOW"),
        (1_500, False, "MEDIUM"),
        (12_000, False, "HIGH"),
        (20, True, "HIGH"),
        # Casos límite añadidos: justo por debajo y justo en cada umbral, y
        # urgencia con importe mínimo.
        (999.99, False, "LOW"),
        (1_000, False, "MEDIUM"),
        (9_999.99, False, "MEDIUM"),
        (10_000, False, "HIGH"),
        (0, True, "HIGH"),
    ],
)
def test_priority_policy(amount: float, urgent: bool, expected: str) -> None:
    # Una sola prueba parametrizada documenta las cuatro ramas de la política.
    assert PriorityPolicy().calculate(Incident("INC-1", "Descripción de prueba", amount, urgent)) == expected


def test_service_returns_explained_prediction(classifier) -> None:
    incident = Incident("INC-2", "Transferencia internacional sospechosa", 12_000, True)
    prediction = IncidentClassificationService(classifier, PriorityPolicy()).classify(incident)
    assert prediction.category
    assert prediction.priority == "HIGH"
    assert "prioridad HIGH" in prediction.explanation


def test_json_writer_exports_valid_json(classifier, tmp_path) -> None:
    service = IncidentClassificationService(classifier, PriorityPolicy())
    predictions = [service.classify(Incident("INC-3", "Documento de cliente caducado", 0, False))]
    destination = tmp_path / "predictions.json"
    JsonPredictionWriter().write(predictions, destination)
    payload = json.loads(destination.read_text(encoding="utf-8"))
    assert payload[0]["incident_id"] == "INC-3"
    assert set(payload[0]) == {"incident_id", "category", "confidence", "priority", "explanation"}


def test_cli_processes_all_incidents(monkeypatch, capsys, tmp_path: Path) -> None:
    # El test extremo a extremo sustituye los argumentos de consola, captura la
    # salida y escribe en una carpeta temporal segura.
    lab_root = Path(__file__).parents[1]
    destination = tmp_path / "predictions.json"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "frc-incidents",
            "--training",
            str(lab_root / "data" / "training.csv"),
            "--input",
            str(lab_root / "data" / "incidents.csv"),
            "--output",
            str(destination),
        ],
    )

    main()

    output = capsys.readouterr().out
    payload = json.loads(destination.read_text(encoding="utf-8"))
    assert "Procesadas 3 incidencias sintéticas" in output
    assert len(payload) == 3
