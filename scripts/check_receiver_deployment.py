"""Validate the public receiver without sending fiscal documents or printing tokens."""
import argparse
import os
import sys
from pathlib import Path
from urllib.parse import urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import requests
from lxml import etree


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--signed-auth", action="store_true", help="Sign a real seed with the configured certificate.")
    args = parser.parse_args()
    base = args.base_url.rstrip("/")
    parts = urlsplit(base)
    if parts.scheme != "https" or not parts.netloc or parts.query or parts.fragment:
        raise ValueError("Use an HTTPS base URL without query or fragment.")
    session = requests.Session()

    def request(method, route, **kwargs):
        return session.request(method, base + route, timeout=30, allow_redirects=False, **kwargs)

    for route in ("/fe/autenticacion/api/semilla", "/FE/AUTENTICACION/API/SEMILLA"):
        response = request("GET", route, headers={"Accept": "application/xml"})
        if response.status_code != 200 or "xml" not in response.headers.get("Content-Type", ""):
            raise ValueError(f"{route}: expected XML HTTP 200, got {response.status_code}.")
        seed = response.content
        root = etree.fromstring(seed, etree.XMLParser(resolve_entities=False, no_network=True))
        if etree.QName(root).localname.lower() != "semillamodel" or not root.findtext("valor") or not root.findtext("fecha"):
            raise ValueError("Invalid seed response.")
    print("OK: HTTPS, XML seed and case-insensitive authentication route.")
    headers = {}
    if args.signed_auth:
        import django
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "MultiServices.settings")
        django.setup()
        from ecf.config import Settings
        from ecf.certificate import load_pkcs12
        from ecf.signing import sign_xml
        cfg = Settings.from_env()
        if cfg.environment != "cert":
            raise ValueError("This check requires DGII_ENVIRONMENT=cert.")
        certificate = load_pkcs12(cfg.certificate_path, cfg.certificate_password)
        signed = sign_xml(seed, certificate)
        response = request("POST", "/fe/autenticacion/api/validacioncertificado",
                           files={"xml": ("seed.xml", signed, "application/xml")}, headers={"Accept": "application/json"})
        if response.status_code != 200:
            message = "inspect server logs and trusted CA chain"
            if "json" in response.headers.get("Content-Type", ""):
                try:
                    result = response.json()
                    if isinstance(result, dict) and result.get("status") == "error":
                        message = str(result.get("message") or message)[:500]
                except ValueError:
                    pass
            raise ValueError(f"Signed authentication failed: HTTP {response.status_code}; {message}")
        result = response.json()
        if not all(result.get(key) for key in ("token", "expira", "expedido")):
            raise ValueError("Incomplete authentication response.")
        headers = {"Authorization": "Bearer " + result["token"]}
        print("OK: signed seed -> bearer token (token not displayed).")
    for route in ("/fe/recepcion/api/ecf", "/fe/aprobacioncomercial/api/ecf"):
        # A missing XML must never be acknowledged as accepted.
        response = request("POST", route, headers=headers)
        expected = {400} if args.signed_auth else {400, 401}
        if response.status_code not in expected:
            raise ValueError(f"{route}: missing XML returned unexpected HTTP {response.status_code}.")
        upper = request("POST", route.upper(), headers=headers)
        if upper.status_code != response.status_code:
            raise ValueError(f"{route}: uppercase route behaves differently.")
        print(f"OK: {route}: rejects missing XML, including uppercase route.")
    print("No e-CF/ACECF transmitted. Valid signed fiscal reception still requires DGII steps 8-11.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"NOT READY: {exc}", file=sys.stderr)
        sys.exit(1)
