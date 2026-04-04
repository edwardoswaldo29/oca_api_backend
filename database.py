"""
database.py
-----------
Conexión centralizada a Supabase para toda la aplicación OCA.
Utiliza las variables de entorno definidas en el archivo .env

Si en el futuro se modulariza el proyecto, este archivo va en:
    📁 app/core/database.py   ←  o   📁 app/db/connection.py
"""

import os
from dotenv import load_dotenv
from supabase import create_client, Client

# ─────────────────────────────────────────────
# Carga de variables de entorno desde .env
# ─────────────────────────────────────────────
load_dotenv()

SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "")  # service_role key (acceso total sin RLS)

if not SUPABASE_URL or not SUPABASE_KEY:
    raise EnvironmentError(
        "❌ Las variables SUPABASE_URL y SUPABASE_KEY deben estar definidas en el archivo .env"
    )

# ─────────────────────────────────────────────
# Cliente Supabase (singleton)
# ─────────────────────────────────────────────
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


def get_supabase() -> Client:
    """
    Función de dependencia para FastAPI.
    Retorna el cliente Supabase listo para usar.

    Uso en rutas:
        from database import get_supabase
        from supabase import Client

        @router.get("/ejemplo")
        def ejemplo(db: Client = Depends(get_supabase)):
            ...
    """
    return supabase