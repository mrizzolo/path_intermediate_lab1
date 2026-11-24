"""Casos de uso: clasificación, prioridad y exportación.

Esta capa coordina piezas ya especializadas. El clasificador propone una
categoría; la política calcula una prioridad operativa; el servicio combina
ambas sin convertir ninguna de ellas en una decisión bancaria automática.
"""

import json
from dataclasses import asdict
from pathlib import Path
from typing import Protocol

from .domain import Incident, Prediction


class Classifier(Protocol):
    """Contrato mínimo que debe cumplir cualquier clasificador compatible."""

    def predict(self, text: str) -> tuple[str, float]: ...


class PriorityPolicy:
    """Regla didáctica, explícita y auditable de priorización."""

    def calculate(self, incident: Incident) -> str:
        """Calcula prioridad usando solo urgencia e importe sintético."""
        # La urgencia prevalece aunque el importe sea bajo. Un importe igual o
        # superior a 10 000 también requiere atención prioritaria en el Lab.
        # Retornos tempranos ordenados de mayor a menor prioridad: cada
        # incidencia cae exactamente en una rama, sin solapamientos.
        if incident.urgent or incident.amount_eur >= 10_000:
            return "HIGH"
        if incident.amount_eur >= 1_000:
            return "MEDIUM"
        return "LOW"


class IncidentClassificationService:
    """Orquesta la clasificación de una o varias incidencias."""

    def __init__(self, classifier: Classifier, priority_policy: PriorityPolicy) -> None:
        # Recibir las dependencias desde fuera facilita probar el servicio con
        # un clasificador controlado y sustituir implementaciones.
        self.classifier = classifier
        self.priority_policy = priority_policy

    def classify(self, incident: Incident) -> Prediction:
        """Construye una predicción trazable para una incidencia."""
        # Categoría y prioridad son dimensiones distintas: el modelo interpreta
        # el texto; la política aplica reglas operativas visibles.
        category, confidence = self.classifier.predict(incident.description)
        priority = self.priority_policy.calculate(incident)
        urgency = "urgente" if incident.urgent else "no urgente"
        explanation = (
            f"Categoría sugerida {category} (confianza {confidence:.2f}) a partir de la descripción; "
            f"prioridad {priority} por importe {incident.amount_eur:.2f} EUR e incidencia {urgency}. "
            "Propuesta para revisión por un analista."
        )
        return Prediction(
            incident_id=incident.incident_id,
            category=category,
            confidence=confidence,
            priority=priority,
            explanation=explanation,
        )

    def classify_all(self, incidents: list[Incident]) -> list[Prediction]:
        """Aplica el mismo caso de uso a todas las incidencias, en orden."""
        return [self.classify(incident) for incident in incidents]


class JsonPredictionWriter:
    """Adaptador de salida que serializa predicciones en JSON legible."""

    def write(self, predictions: list[Prediction], path: str | Path) -> None:
        """Crea la carpeta de destino y escribe todas las predicciones."""
        destination = Path(path)
        # ``parents=True`` crea también carpetas intermedias; ``exist_ok=True``
        # permite repetir la ejecución sin fallar si ya existen.
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(
            # ``asdict`` convierte cada dataclass en un diccionario serializable.
            json.dumps([asdict(item) for item in predictions], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
