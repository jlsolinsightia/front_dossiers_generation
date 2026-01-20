from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    APP_NAME: str = "Dossiers App"
    APP_VERSION: str = "0.1.0"
    
    # AUTH
    AUTH_MODE: str = "file"
    # Mock local con JSON de ejemplo
    USERS_PATH: Path = Path("data/mock/users.json")
    AUTH_SALT: str = "insightia_salt_v1"

    CLIENTES_TEMAS_PATH: Path = Path("data\mock\clientes_temas.json")


    # Fuente de datos: "file" o "api"
    DATA_SOURCE: str = "file"

    # Mock local (JSON ejemplo)
    MOCK_JSON_PATH: Path = Path("data/mock/JSON_EJEMPLO_Dossier.json")
    # Plantilla de Dossier (Senadores y Diputados)
    TEMPLATE_DOCX_PATH: Path = Path("templates\Plantilla_Dossier Legislativo.docx")

    # API real (futuro)
    API_BASE_URL: str = "http://127.0.0.1:8000"
    API_DOSSIER_ENDPOINT: str = "/dossier"

