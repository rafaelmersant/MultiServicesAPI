import logging
import sys
from pathlib import Path
from urllib.parse import urljoin

import requests
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ecf.config import Settings
from ecf.certificate import load_pkcs12
from ecf.dgii_auth import DGIIAuthenticator


RNC_EMISOR = "132018559"
ENCF = "E340000000015"

TRACK_IDS = [
    "5de1babf-cc68-46eb-8c5c-b070cb6c8827",
    "fe110d75-3647-4bc2-ab07-e85fb9821f50",
]

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


def print_response(response: requests.Response) -> None:
    print(f"HTTP: {response.status_code}")
    try:
        print(response.json())
    except ValueError:
        print(response.text)


def main() -> int:
    try:
        load_dotenv()
        settings = Settings.from_env()
        logger.info("Ambiente DGII configurado: %s", settings.environment)

        certificate = load_pkcs12(
            settings.certificate_path,
            settings.certificate_password,
        )
        token = DGIIAuthenticator(
            settings=settings,
            certificate=certificate,
        ).authenticate()

        headers = {
            "Authorization": f"Bearer {token.token}",
            "Accept": "application/json",
        }

        trackids_url = urljoin(
            settings.trackids_base_url.rstrip("/") + "/",
            "api/trackids/consulta",
        )
        response = requests.get(
            trackids_url,
            params={"rncemisor": RNC_EMISOR, "encf": ENCF},
            headers=headers,
            timeout=settings.request_timeout_seconds,
        )
        print("\n=== Consulta de TrackIds ===")
        print_response(response)
        response.raise_for_status()

        result_url = urljoin(
            settings.result_base_url.rstrip("/") + "/",
            "api/consultas/estado",
        )
        for track_id in TRACK_IDS:
            logger.info("Consultando resultado del TrackId %s", track_id)
            result_response = requests.get(
                result_url,
                params={"trackid": track_id},
                headers=headers,
                timeout=settings.request_timeout_seconds,
            )
            print(f"\n=== Resultado detallado: {track_id} ===")
            print_response(result_response)
            result_response.raise_for_status()

        return 0
    except requests.RequestException as exc:
        logger.error("Falló la consulta HTTP a DGII: %s", exc)
        return 1
    except Exception as exc:
        logger.error("Falló la consulta: %s", exc, exc_info=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
