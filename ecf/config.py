import os
from dataclasses import dataclass
from pathlib import Path


class ConfigurationError(RuntimeError):
    pass


DGII_BASE_URLS = {
    "precert": "https://ecf.dgii.gov.do/testecf",
    "cert": "https://ecf.dgii.gov.do/certecf",
    "prod": "https://ecf.dgii.gov.do/ecf",
}


@dataclass(frozen=True)
class Settings:
    environment: str
    auth_base_url: str
    request_timeout_seconds: int
    certificate_path: Path
    certificate_password: str
    expected_tax_id: str | None
    reception_base_url: str
    result_base_url: str
    trackids_base_url: str

    @classmethod
    def from_env(cls) -> "Settings":
        environment = os.getenv("DGII_ENVIRONMENT", "precert").strip().lower()
        if environment not in DGII_BASE_URLS:
            raise ConfigurationError(
                "DGII_ENVIRONMENT debe ser precert, cert o prod."
            )

        certificate_path = os.getenv("ECF_CERTIFICATE_PATH", "").strip()
        certificate_password = os.getenv("ECF_CERTIFICATE_PASSWORD", "")
        if not certificate_path:
            raise ConfigurationError("ECF_CERTIFICATE_PATH no está configurado.")
        if not certificate_password:
            raise ConfigurationError("ECF_CERTIFICATE_PASSWORD no está configurado.")

        timeout = int(os.getenv("DGII_TIMEOUT_SECONDS", "30"))
        if timeout < 1:
            raise ConfigurationError("DGII_TIMEOUT_SECONDS debe ser positivo.")

        expected_tax_id = os.getenv("ECF_EXPECTED_TAX_ID", "").strip() or None
        base_url = DGII_BASE_URLS[environment].rstrip("/")

        return cls(
            environment=environment,
            auth_base_url=f"{base_url}/autenticacion",
            request_timeout_seconds=timeout,
            certificate_path=Path(certificate_path),
            certificate_password=certificate_password,
            expected_tax_id=expected_tax_id,
            reception_base_url=f"{base_url}/recepcion",
            result_base_url=f"{base_url}/consultaresultado",
            trackids_base_url=f"{base_url}/consultatrackids",
        )
