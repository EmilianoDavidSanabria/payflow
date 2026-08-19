from .settings import *
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "test_db.sqlite3",
        # Los tests de concurrencia (services/tests/test_idempotency_service.py,
        # payflow/tests/test_concurrency.py) abren escrituras simultáneas
        # desde varios threads. SQLite es single-writer: sin un timeout,
        # una escritura que encuentra el archivo bloqueado por otra falla
        # inmediatamente con "database is locked" en vez de esperar -- algo
        # que Postgres (el motor real de producción) resuelve con locking
        # a nivel de fila, no de archivo entero. Este timeout solo hace que
        # sqlite3 espere en vez de fallar rápido; no cambia ninguna
        # garantía de negocio, es puramente para que los tests reflejen el
        # comportamiento esperado en Postgres.
        "OPTIONS": {"timeout": 20},
    }
}

print("ENTRO A SETTINGS_TEST")
print(DATABASES)