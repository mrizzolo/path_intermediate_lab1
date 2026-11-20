"""Adaptadores que traducen CSV sintéticos a objetos Python.

El repositorio se ocupa del formato del archivo, no de decidir categoría o
prioridad. Esta separación permite sustituir un CSV por una base de datos sin
reescribir las reglas del dominio.
"""

import csv
from pathlib import Path

from .domain import Incident


def _as_bool(value: str) -> bool:
    """Convierte el texto del CSV a booleano o falla de forma explícita."""
    normalized = value.strip().lower()
    # No usamos ``bool(value)``: en Python, ``bool("false")`` también es True
    # porque cualquier cadena no vacía se considera verdadera.
    if normalized not in {"true", "false"}:
        raise ValueError("urgent debe ser true o false")
    return normalized == "true"


class IncidentCsvRepository:
    """Lee las incidencias de entrada y deja su validación al dominio."""

    def load(self, path: str | Path) -> list[Incident]:
        """Devuelve una lista de ``Incident`` a partir de un CSV UTF-8."""
        # ``newline=""`` deja que el módulo csv gestione los saltos de línea
        # igual en Windows, macOS y Linux.
        with Path(path).open(encoding="utf-8", newline="") as handle:
            # El repositorio solo convierte tipos; las reglas de negocio
            # (id vacío, importe negativo...) las valida ``Incident``.
            return [
                Incident(
                    incident_id=row["incident_id"],
                    description=row["description"],
                    amount_eur=float(row["amount_eur"]),
                    urgent=_as_bool(row["urgent"]),
                )
                for row in csv.DictReader(handle)
            ]


class TrainingCsvRepository:
    """Lee pares ``(texto, categoría)`` para entrenar el clasificador dado."""

    def load(self, path: str | Path) -> list[tuple[str, str]]:
        """Conserva el contrato sencillo que espera ``classifier.fit``."""
        with Path(path).open(encoding="utf-8", newline="") as handle:
            return [(row["text"], row["category"]) for row in csv.DictReader(handle)]
