from __future__ import annotations

import argparse
import json
import os
import ssl
from urllib import request, error


DEFAULT_ITEM = "VACUNA CLOSTRIBAC 8 GOLD X 50 DOS."
DEFAULT_PROVIDER = "COOPRINSEM"


def call_json(
    url: str,
    payload: dict | None = None,
    token: str | None = None,
    timeout: int = 300,
    insecure: bool = False,
) -> dict:
    headers = {"Accept": "application/json"}
    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"

    req = request.Request(url, data=data, headers=headers, method="POST" if payload else "GET")
    context = ssl._create_unverified_context() if insecure else None
    try:
        with request.urlopen(req, timeout=timeout, context=context) as response:
            return json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"HTTP {exc.code} from {url}\n{body}") from exc
    except error.URLError as exc:
        raise SystemExit(f"Could not reach {url}\n{exc}") from exc


def main() -> None:
    parser = argparse.ArgumentParser(description="Smoke test a deployed MCT-37 Cloud Run service.")
    parser.add_argument("base_url", help="Cloud Run base URL, for example https://service.run.app")
    parser.add_argument("--item-text", default=DEFAULT_ITEM)
    parser.add_argument("--description", default="")
    parser.add_argument("--provider", default=DEFAULT_PROVIDER)
    parser.add_argument("--token", default=os.getenv("CLOUD_RUN_ID_TOKEN"))
    parser.add_argument("--insecure", action="store_true", help="Skip TLS verification for local smoke tests.")
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")
    print(f"Testing: {base_url}")

    health = call_json(f"{base_url}/health", token=args.token, timeout=30, insecure=args.insecure)
    print("\n/health")
    print(json.dumps(health, indent=2, ensure_ascii=False))

    artifact_check = call_json(f"{base_url}/artifact-check", token=args.token, timeout=30, insecure=args.insecure)
    print("\n/artifact-check")
    print(json.dumps(artifact_check, indent=2, ensure_ascii=False))

    payload = {
        "input_id": "smoke_test_001",
        "item_text": args.item_text,
        "description": args.description,
        "provider": args.provider,
        "top_k": 3,
    }
    prediction = call_json(
        f"{base_url}/predict",
        payload=payload,
        token=args.token,
        timeout=300,
        insecure=args.insecure,
    )
    print("\n/predict")
    print(json.dumps(prediction, indent=2, ensure_ascii=False))

    print("\nTop labels:")
    for item in prediction.get("predictions", []):
        print(f"- {item['code']} | {item['name']} | score={item['score']}")


if __name__ == "__main__":
    main()
