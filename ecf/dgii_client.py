from dataclasses import dataclass
import logging

import requests

from .config import Settings
from .exceptions import DGIIClientError


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DGIIResponse:

    status_code: int
    headers: dict[str, str]
    body: str


class DGIIClient:

    def __init__(
        self,
        settings: Settings,
        session: requests.Session | None = None,
    ):

        self.settings = settings

        self.session = (
            session
            or requests.Session()
        )

        self.session.headers.update({
            "Accept": (
                "application/xml, "
                "text/xml, */*"
            )
        })

    def _url(
        self,
        path: str
    ) -> str:

        return (
            f"{self.settings.dgii_base_url}"
            f"/{path.lstrip('/')}"
        )

    def get(
        self,
        path: str,
        *,
        headers: dict[str, str] | None = None,
    ) -> DGIIResponse:

        return self._request(
            "GET",
            path,
            headers=headers,
        )

    def post_xml(
        self,
        path: str,
        xml: str,
        *,
        headers: dict[str, str] | None = None,
    ) -> DGIIResponse:

        request_headers = {
            "Content-Type": (
                "application/xml; "
                "charset=utf-8"
            )
        }

        if headers:
            request_headers.update(
                headers
            )

        return self._request(
            "POST",
            path,
            headers=request_headers,
            data=xml.encode("utf-8"),
        )

    def _request(
        self,
        method: str,
        path: str,
        *,
        headers: dict[str, str] | None = None,
        data: bytes | None = None,
    ) -> DGIIResponse:

        url = self._url(path)

        try:

            response = self.session.request(
                method,
                url,
                headers=headers,
                data=data,
                timeout=(
                    self.settings
                    .request_timeout_seconds
                ),
            )

        except requests.RequestException as exc:

            raise DGIIClientError(
                f"Error de comunicación "
                f"con DGII: {exc}"
            ) from exc

        logger.info(
            "DGII %s %s -> HTTP %s",
            method,
            path,
            response.status_code,
        )

        return DGIIResponse(
            status_code=response.status_code,
            headers=dict(
                response.headers
            ),
            body=response.text,
        )

    @staticmethod
    def require_success(
        response: DGIIResponse
    ) -> str:

        if not (
            200
            <= response.status_code
            < 300
        ):

            raise DGIIClientError(
                "DGII respondió HTTP "
                f"{response.status_code}: "
                f"{response.body[:1000]}"
            )

        return response.body