from __future__ import annotations

import json
import urllib.parse
import urllib.request
from typing import Any


def search_pubmed_public(query: str, retmax: int = 5, timeout: int = 10) -> dict[str, Any]:
    """Query PubMed ESearch public API when network is available."""
    params = urllib.parse.urlencode({"db": "pubmed", "term": query, "retmode": "json", "retmax": retmax})
    url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?{params}"
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:  # noqa: S310 - public NCBI endpoint.
            payload = json.loads(response.read().decode("utf-8"))
        ids = payload.get("esearchresult", {}).get("idlist", [])
        return {"status": "pubmed_search_success", "query": query, "pmids": ids, "url": url, "trace": [{"stage": "pubmed_esearch", "count": len(ids)}]}
    except Exception as exc:  # noqa: BLE001
        return {"status": "pubmed_search_review_required", "query": query, "pmids": [], "url": url, "error": str(exc), "trace": [{"stage": "pubmed_esearch_failed"}]}
