# ...existing code...
#!/usr/bin/env python3
"""
Indexer for SideFX Houdini 20.5 Solaris docs subtree:
https://www.sidefx.com/docs/houdini20.5/solaris/index.html

Usage:
  python scripts/index_sidefx_solaris.py --index   # crawl + build index
  python scripts/index_sidefx_solaris.py --query "how to create a light"  # query the index
"""
import re
import sys
import time
import json
import argparse
import textwrap
from urllib.parse import urljoin, urlparse
import os
import math
import heapq

import requests
from bs4 import BeautifulSoup
from tqdm import tqdm

# optional Playwright fallback for JS-rendered pages
try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except Exception:
    PLAYWRIGHT_AVAILABLE = False

try:
    from sentence_transformers import SentenceTransformer
except Exception:  # pragma: no cover - environment dependent
    SentenceTransformer = None

try:
    import chromadb
    from chromadb.config import Settings
except Exception:  # pragma: no cover - environment dependent
    chromadb = None
    Settings = None

ROOT = "https://www.sidefx.com/docs/houdini20.5/solaris/index.html"
BASE_PREFIX = "https://www.sidefx.com/docs/houdini20.5/solaris/"
CHROMA_DIR = "./chroma_db/sidefx_solaris"
COLLECTION_NAME = "sidefx_solaris"

# ---------- utilities ----------
def normalize_url(href, base=ROOT):
    if not href:
        return None
    href = href.split("#")[0]
    href = href.strip()
    if href.startswith("http"):
        return href if href.startswith(BASE_PREFIX) else None
    if href.startswith("/"):
        candidate = urljoin("https://www.sidefx.com", href)
        return candidate if candidate.startswith(BASE_PREFIX) else None
    return urljoin(base, href)

def fetch_html_requests(url, timeout=20):
    r = requests.get(url, timeout=timeout, headers={"User-Agent": "indexer/1.0"})
    r.raise_for_status()
    return r.text

def fetch_html_playwright(url):
    if not PLAYWRIGHT_AVAILABLE:
        raise RuntimeError("Playwright not available")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url, wait_until="networkidle")
        html = page.content()
        browser.close()
        return html

def fetch_text(url, use_playwright=False):
    try:
        html = fetch_html_requests(url)
    except Exception:
        if use_playwright and PLAYWRIGHT_AVAILABLE:
            html = fetch_html_playwright(url)
        else:
            raise
    soup = BeautifulSoup(html, "html.parser")
    # remove scripts/styles and nav/aside footers which are common noise
    for tag in soup(["script", "style", "aside", "nav", "footer"]):
        tag.decompose()
    # try to find main content regions; fallback to body
    main = soup.find("main") or soup.find("article") or soup.body
    if not main:
        return ""
    # preserve headings for structure
    for h in main.find_all(["h1","h2","h3","h4","h5","h6"]):
        h.string = (h.get_text(strip=True) or "")
    text = main.get_text(separator="\n")
    # normalize whitespace
    text = re.sub(r"\n\s+\n", "\n\n", text)
    text = textwrap.dedent(text).strip()
    return text

# approximate chunking by sentences/words
def chunk_text(text, max_words=400, overlap=50):
    sents = [s.strip() for s in re.split(r'(?<=[.?!])\s+', text) if s.strip()]
    chunks = []
    cur = []
    cur_words = 0
    for s in sents:
        w = len(s.split())
        if cur_words + w > max_words and cur:
            chunks.append(" ".join(cur))
            # keep overlap by retaining last sentences until overlap count reached
            if overlap > 0:
                # naive: keep last sentences whose words sum to <= overlap
                keep = []
                keep_words = 0
                for sent in reversed(cur):
                    sw = len(sent.split())
                    if keep_words + sw > overlap:
                        break
                    keep.insert(0, sent)
                    keep_words += sw
                cur = keep
                cur_words = keep_words
            else:
                cur = []
                cur_words = 0
        cur.append(s)
        cur_words += w
    if cur:
        chunks.append(" ".join(cur))
    return chunks

# ---------- crawler ----------
def crawl_site(root=ROOT, max_pages=500, use_playwright=False):
    to_visit = [root]
    visited = set()
    pages = []
    pbar = tqdm(total=max_pages, desc="Crawling", unit="page")
    while to_visit and len(visited) < max_pages:
        url = to_visit.pop(0)
        if url in visited:
            continue
        try:
            html = fetch_html_requests(url)
        except Exception:
            if use_playwright and PLAYWRIGHT_AVAILABLE:
                html = fetch_html_playwright(url)
            else:
                # skip on error
                visited.add(url)
                pbar.update(1)
                continue
        visited.add(url)
        pbar.update(1)
        soup = BeautifulSoup(html, "html.parser")
        # store the page
        pages.append({"url": url, "html": html})
        # discover links
        for a in soup.find_all("a", href=True):
            n = normalize_url(a["href"], base=url)
            if n and n not in visited and n not in to_visit:
                to_visit.append(n)
        time.sleep(0.1)  # polite
    pbar.close()
    return pages

# ---------- indexing ----------
def index_pages(pages, collection_name=COLLECTION_NAME, persist_dir=CHROMA_DIR, model_name="all-MiniLM-L6-v2"):
    if SentenceTransformer is None:
        raise RuntimeError(
            "Missing dependency: sentence-transformers is required. Please `pip install -r tools_Houdini/requirements.txt`"
        )
    # try to create a Chroma client; if it fails (newer chroma config), fall back to a JSON index
    client = None
    try:
        if chromadb is not None and Settings is not None:
            client = chromadb.Client(Settings(chroma_db_impl="duckdb+parquet", persist_directory=persist_dir))
            coll = client.get_or_create_collection(collection_name)
        else:
            client = None
    except Exception as e:  # pragma: no cover - runtime environment dependent
        print("Warning: chromadb client creation failed, falling back to local JSON index.\n", str(e))
        client = None
    model = SentenceTransformer(model_name)
    all_docs = []
    all_ids = []
    all_meta = []
    for page in tqdm(pages, desc="Parsing pages"):
        url = page["url"]
        text = fetch_text(url)
        if not text:
            continue
        chunks = chunk_text(text)
        ids = [f"{url}::ch{i}" for i in range(len(chunks))]
        metas = [{"source": url, "chunk_index": i} for i in range(len(chunks))]
        all_docs.extend(chunks)
        all_ids.extend(ids)
        all_meta.extend(metas)
    if not all_docs:
        print("No documents to index.")
        return
    embeddings = model.encode(all_docs)
    # If we have a working chromadb client, use it
    if client is not None:
        embeddings_list = embeddings.tolist()
        # add in batches to avoid overloading
        batch = 512
        for i in range(0, len(all_docs), batch):
            j = min(i + batch, len(all_docs))
            coll.add(documents=all_docs[i:j], metadatas=all_meta[i:j], ids=all_ids[i:j], embeddings=embeddings_list[i:j])
        client.persist()
        print(f"Indexed {len(all_docs)} chunks into {persist_dir} (Chroma)")
        return

    # Fallback: write a simple JSON index with embeddings (as lists) and metadata
    os.makedirs(persist_dir, exist_ok=True)
    json_path = os.path.join(persist_dir, "index.json")
    serial = []
    for i, doc in enumerate(all_docs):
        serial.append({
            "id": all_ids[i],
            "doc": doc,
            "meta": all_meta[i],
            "embedding": embeddings[i].tolist() if hasattr(embeddings[i], "tolist") else list(embeddings[i])
        })
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(serial, f)
    print(f"Indexed {len(all_docs)} chunks into {json_path} (JSON fallback)")

# ---------- query ----------
def query_index(query, k=4, collection_name=COLLECTION_NAME, persist_dir=CHROMA_DIR, model_name="all-MiniLM-L6-v2"):
    if SentenceTransformer is None:
        raise RuntimeError(
            "Missing dependency: sentence-transformers is required. Please `pip install -r tools_Houdini/requirements.txt`"
        )
    # try Chroma first
    client = None
    try:
        if chromadb is not None and Settings is not None:
            client = chromadb.Client(Settings(chroma_db_impl="duckdb+parquet", persist_directory=persist_dir))
            coll = client.get_collection(collection_name)
    except Exception as e:  # pragma: no cover - runtime environment dependent
        print("Warning: chromadb client creation failed, using JSON fallback if available.\n", str(e))
        client = None

    model = SentenceTransformer(model_name)
    q_emb = model.encode([query])[0].tolist()

    if client is not None:
        res = coll.query(query_embeddings=[q_emb], n_results=k, include=["documents", "metadatas", "distances"])
        hits = []
        if res and "documents" in res and res["documents"]:
            for doc, meta, dist in zip(res["documents"][0], res["metadatas"][0], res["distances"][0]):
                hits.append({"text": doc, "meta": meta, "distance": dist})
        return hits

    # Fallback: read local JSON index and do cosine similarity search
    json_path = os.path.join(persist_dir, "index.json")
    if not os.path.exists(json_path):
        raise RuntimeError(f"No index found at {json_path}. Run --index first or install chromadb.")
    with open(json_path, "r", encoding="utf-8") as f:
        items = json.load(f)

    # compute cosine similarities
    def cosine(a, b):
        # a and b are lists
        dot = 0.0
        na = 0.0
        nb = 0.0
        for x, y in zip(a, b):
            dot += x * y
            na += x * x
            nb += y * y
        if na == 0 or nb == 0:
            return 0.0
        return dot / (math.sqrt(na) * math.sqrt(nb))

    heap = []
    for it in items:
        sim = cosine(q_emb, it["embedding"])
        # store negative sim because heapq is a min-heap
        if len(heap) < k:
            heapq.heappush(heap, (sim, it))
        else:
            if sim > heap[0][0]:
                heapq.heapreplace(heap, (sim, it))

    # sort descending
    hits = []
    for sim, it in sorted(heap, key=lambda x: -x[0]):
        hits.append({"text": it["doc"], "meta": it["meta"], "distance": 1.0 - sim})
    return hits

# Optional: small aggregator to build a prompt-ready context
def build_context(hits, max_chars=3000):
    parts = []
    seen_sources = set()
    for h in hits:
        src = h["meta"].get("source")
        if src in seen_sources:
            continue
        seen_sources.add(src)
        parts.append(f"Source: {src}\n\n{h['text']}\n\n---\n")
        if sum(len(p) for p in parts) > max_chars:
            break
    return "\n".join(parts)

# ---------- CLI ----------
def main():
    parser = argparse.ArgumentParser(description="Index / query SideFX Solaris docs (Houdini 20.5)")
    parser.add_argument("--index", action="store_true", help="crawl and index site")
    parser.add_argument("--query", type=str, help="run a query against the index")
    parser.add_argument("--pages", type=int, default=400, help="max pages to crawl")
    parser.add_argument("--use-playwright", action="store_true", help="use Playwright fallback for JS pages")
    args = parser.parse_args()
    if args.index:
        pages = crawl_site(max_pages=args.pages, use_playwright=args.use_playwright)
        index_pages(pages)
        return
    if args.query:
        hits = query_index(args.query)
        ctx = build_context(hits)
        out = {"question": args.query, "results": hits, "context_assembled": ctx[:5000]}
        print(json.dumps(out, indent=2))
        return
    parser.print_help()

if __name__ == "__main__":
    main()
# ...existing code...