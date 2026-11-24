# Evidencias de mi práctica

## Identificación

Nombre/equipo: Martín Rizzo Lozano. Fecha: 2026-11-24. Python usado: 3.12.10.

## Comprobaciones reales

| Comando o escenario | Resultado obtenido | Archivo o prueba que lo demuestra |
|---|---|---|
| T1 · `.venv\Scripts\python -m pytest -q -rA tests/test_lab.py::test_incident_rejects_negative_amount tests/test_lab.py::test_prediction_rejects_invalid_confidence_and_priority` | `2 passed` | `tests/test_lab.py::test_incident_rejects_negative_amount` y `tests/test_lab.py::test_prediction_rejects_invalid_confidence_and_priority` · `src/frc_incidents/domain.py` |
| T2 · `.venv\Scripts\python -m pytest -q -rA tests/test_lab.py::test_csv_repository_loads_synthetic_incidents tests/test_lab.py::test_csv_repository_rejects_invalid_urgent` | `2 passed` | `tests/test_lab.py::test_csv_repository_loads_synthetic_incidents` y `tests/test_lab.py::test_csv_repository_rejects_invalid_urgent` · `src/frc_incidents/repositories.py` |

## Casos positivos y negativos

Entrada → resultado observado → explicación. Completar con los casos de la guía. En los workflows incluir aprobación y rechazo; en RAG incluir abstención.

### Tarea 1 · Dominio

- **Negativo (importe `-1`, caso de la guía):**
  - Entrada: `.venv\Scripts\python -c "from frc_incidents.domain import Incident; Incident('INC-X', 'Descripción válida', -1, False)"`
  - Resultado observado: la traza termina con `frc_incidents.domain.DomainValidationError: amount_eur no puede ser negativo` (lanzado en `domain.py`, línea 41, dentro de `__post_init__`).
  - Explicación: `Incident` valida sus invariantes al construirse; un importe negativo es imposible, así que el objeto no llega a crearse y el dato no puede avanzar hacia la clasificación.
- **Positivo (incidencia válida, caso de la guía):**
  - Entrada: `.venv\Scripts\python -c "from frc_incidents.domain import Incident; print(Incident('FRC-1', 'Descripción suficientemente larga', 50, False))"`
  - Resultado observado: `Incident(incident_id='FRC-1', description='Descripción suficientemente larga', amount_eur=50, urgent=False)`
  - Explicación: con ID no vacío, descripción de al menos 10 caracteres e importe no negativo, el objeto se crea sin error y conserva sus cuatro campos tal como se le pasaron.
- **Negativo (ID vacío):**
  - Entrada: `.venv\Scripts\python -c "from frc_incidents.domain import Incident; Incident('  ', 'Descripción suficientemente larga', 50, False)"`
  - Resultado observado: la traza termina con `frc_incidents.domain.DomainValidationError: incident_id no puede estar vacío` (lanzado en `domain.py`, línea 37).
  - Explicación: un ID formado solo por espacios también cuenta como vacío (se aplica `strip()`); sin identificador no se podría rastrear la incidencia en la salida.
- **Negativo (descripción corta):**
  - Entrada: `.venv\Scripts\python -c "from frc_incidents.domain import Incident; Incident('FRC-1', 'Corta', 50, False)"`
  - Resultado observado: la traza termina con `frc_incidents.domain.DomainValidationError: description debe tener al menos 10 caracteres` (lanzado en `domain.py`, línea 39).
  - Explicación: `'Corta'` tiene 5 caracteres; una descripción tan breve no da al clasificador texto suficiente para sugerir una categoría.

### Tarea 2 · Repositorio CSV

- **Positivo (dataset incluido, caso de la guía):**
  - Entrada: `.venv\Scripts\python -c "from frc_incidents.repositories import IncidentCsvRepository; print(len(IncidentCsvRepository().load('data/incidents.csv')))"`
  - Resultado observado: `3`
  - Explicación: el repositorio lee las tres filas sintéticas de `data/incidents.csv` y convierte cada una en un `Incident` tipado; ninguna fila incumple las invariantes del dominio.
- **Negativo (`urgent` inválido):**
  - Entrada: `.venv\Scripts\python -c "from frc_incidents.repositories import _as_bool; _as_bool('yes')"`
  - Resultado observado: la traza termina con `ValueError: urgent debe ser true o false` (lanzado en `repositories.py`, línea 20, dentro de `_as_bool`).
  - Explicación: solo se aceptan `true` y `false`; cualquier otro valor falla de forma explícita. No se usa `bool(cadena)` porque en Python `bool("false")` vale `True` y marcaría como urgente una incidencia que no lo es.
- **Positivo (datos de entrenamiento):**
  - Entrada: `.venv\Scripts\python -c "from frc_incidents.repositories import TrainingCsvRepository; d = TrainingCsvRepository().load('data/training.csv'); print(len(d), d[0])"`
  - Resultado observado: `6 ('Compra con tarjeta no reconocida en comercio online', 'card_fraud')`
  - Explicación: el repositorio devuelve 6 pares `(texto, categoría)`, el formato que espera `fit` del clasificador.

## Decisiones y limitaciones

- **Decisión 1 (T1):** las validaciones viven en `__post_init__` de dataclasses `frozen=True`.
  - Motivo: no puede existir un `Incident` o `Prediction` inválido y, una vez creado, no se puede modificar. La regla se cumple igual venga el dato del CSV, del CLI o de un test.
- **Decisión 2 (T2):** el repositorio solo convierte tipos, y `_as_bool` acepta únicamente `true`/`false`.
  - Motivo: las reglas de negocio quedan en el dominio y no se duplican; y `bool("false")` daría `True`, marcando como urgente una incidencia que no lo es.
- **Limitación (T2):** si una sola fila del CSV es inválida, la carga completa falla en esa fila; no se cargan las filas válidas ni se obtiene un informe de qué filas fallaron.

## Ayuda consultada y comprensión

**Ayuda consultada:** he seguido `GUIA_ALUMNO.md` y `RUBRICA.md`, y he leído los comentarios del propio código. He usado Claude Code (asistente de IA) para revisar cómo iba la práctica, entender por qué fallaban algunos tests y ayudarme a redactar este documento. Todo lo que aparece aquí lo he comprobado ejecutando yo mismo los tests y los comandos de la guía; los resultados que pongo son los que me salieron en mi terminal.

**Una invariante (T1):** `Incident` no admite un importe negativo. Me parece importante que lo rechace al crearse, y no más adelante, porque así un dato imposible no puede colarse en ningún punto del proceso: si el objeto existe, ya sé que es válido, y no tengo que repetir la comprobación en el clasificador, en la política de prioridad o en el JSON. Además, al ser `frozen`, nadie puede cambiar el importe después.

**Recorrido de una entrada de extremo a extremo:** pendiente (se completa al terminar T4–T6).

## Autoevaluación

Una fila por subcriterio de RUBRICA.md: puntos solicitados y evidencia localizable. No confundir el resultado esperado con un resultado ejecutado.

| Área · subcriterio | Máx. | Solicitados | Evidencia |
|---|---:|---:|---|
| Dominio · `Incident` y `Prediction` son dataclasses congeladas | 4 | 4 | `src/frc_incidents/domain.py`: `@dataclass(frozen=True)` en ambas clases |
| Dominio · rechaza ID vacío y descripción menor de 10 caracteres | 4 | 4 | Casos negativos T1: ID `'  '` → `incident_id no puede estar vacío`; descripción `'Corta'` → `description debe tener al menos 10 caracteres` |
| Dominio · rechaza importe negativo | 4 | 4 | `test_incident_rejects_negative_amount` PASSED + caso negativo T1 (`DomainValidationError: amount_eur no puede ser negativo`) |
| Dominio · rechaza confianza fuera de [0,1] y prioridad desconocida | 3 | 3 | `test_prediction_rejects_invalid_confidence_and_priority` PASSED |
| CSV · carga tres `Incident` tipados desde `incidents.csv` | 5 | 5 | Caso positivo T2: salida `3` + `test_csv_repository_loads_synthetic_incidents` PASSED |
| CSV · valida `urgent` y convierte `false` a `False` sin `bool(cadena)` | 5 | 5 | `_as_bool` en `repositories.py` + caso negativo T2 (`ValueError: urgent debe ser true o false`) + `test_csv_repository_rejects_invalid_urgent` PASSED |
| CSV · carga pares de entrenamiento y conserva las validaciones de dominio | 5 | 5 | Caso positivo T2: `training.csv` → 6 pares `(texto, categoría)`; las incidencias siguen validándose en `Incident` (casos negativos T1) |

Subtotal T1–T2: 30 / 30.
