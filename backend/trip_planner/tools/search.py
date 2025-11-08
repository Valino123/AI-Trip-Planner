import requests
from langchain_core.tools import tool

UA = {"User-Agent": "LangGraph-Demo/1.0 (+https://example.local)"}
meta = {"verbose": True}


@tool("search_tool")
def search_tool(query: str) -> str:
    """Search the web for a concise answer/snippet (Wikipedia→DuckDuckGo fallback)."""
    if meta["verbose"]:
        print("[INFO] search_tool is called. Executing...")
    q = (query or "").strip()
    try:
        r = requests.get(
            "https://en.wikipedia.org/api/rest_v1/page/summary/" + requests.utils.quote(q),
            headers=UA,
            timeout=4,
        )
        if r.status_code == 200:
            data = r.json()
            extract = data.get("extract")
            if extract:
                title = data.get("title", "Wikipedia")
                return f"{title}: {extract}"
    except Exception:
        pass

    try:
        r = requests.get(
            "https://api.duckduckgo.com/",
            params={"q": q, "format": "json", "no_html": 1, "skip_disambig": 1},
            headers=UA,
            timeout=4,
        )
        if r.status_code == 200:
            data = r.json()
            abstract = data.get("AbstractText")
            if abstract:
                return abstract
            heading = data.get("Heading")
            if heading:
                return heading
    except Exception:
        pass

    return f"[search] No concise result for: {q}. Try rephrasing or a more specific query."


