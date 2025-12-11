from flask import Flask, jsonify, request
from flask_cors import CORS
import requests
import html
from datetime import datetime
from math import ceil

app = Flask(__name__)
CORS(app)

# Configuration
MAX_POSTS = 500     # how many posts to collect at most across pages (adjust as needed)
PAGE_SIZE = 15      # number of results per page returned to the client
HEADERS = {
    "User-Agent": "MyRedditSearchApp/1.0 (by /u/yourusername)"
}

def clean_preview_url(url):
    if not url:
        return None
    u = html.unescape(str(url))
    if u.startswith("//"):
        u = "https:" + u
    if u.startswith("preview.redd.it") or u.startswith("i.redd.it") or u.startswith("i.reddituploads.com"):
        u = "https://" + u
    return u

def extract_image_url(post_data):
    preview = post_data.get("preview")
    if preview and isinstance(preview, dict):
        images = preview.get("images")
        if images and isinstance(images, list) and images:
            src = images[0].get("source", {}).get("url")
            if src:
                return clean_preview_url(src)

    media_metadata = post_data.get("media_metadata")
    if media_metadata and isinstance(media_metadata, dict):
        for key, meta in media_metadata.items():
            if isinstance(meta, dict):
                s = meta.get("s")
                if s and s.get("u"):
                    return clean_preview_url(s.get("u"))
                if meta.get("p") and isinstance(meta.get("p"), list):
                    last = meta["p"][-1]
                    if last and last.get("u"):
                        return clean_preview_url(last.get("u"))

    url_override = post_data.get("url_overridden_by_dest")
    if url_override:
        if any(url_override.lower().endswith(ext) for ext in (".jpg", ".jpeg", ".png", ".gif", ".webp")):
            return clean_preview_url(url_override)

    thumbnail = post_data.get("thumbnail")
    if thumbnail and thumbnail.startswith("http"):
        return clean_preview_url(thumbnail)

    return None

def is_relevant_to_query(title, selftext, query):
    q = (query or "").strip().lower()
    if not q:
        return True
    title_l = (title or "").lower()
    body_l = (selftext or "").lower()
    if q in title_l:
        return True
    words = [w for w in q.split() if w]
    if words and all(any(w in field for field in (title_l, body_l)) for w in words):
        return True
    return False

def search_reddit_collect_all(query):
    """
    Collect up to MAX_POSTS matching reddit search results (paged requests).
    Returns list of result dicts (unsliced).
    """
    base_url = "https://www.reddit.com/r/all/search.json"
    params = {
        "q": query,
        "sort": "relevance",
        "t": "all",
        "limit": 100
    }

    results = []
    after = None
    fetched = 0

    while True:
        if after:
            params["after"] = after
        try:
            resp = requests.get(base_url, headers=HEADERS, params=params, timeout=10)
        except requests.RequestException:
            break

        if resp.status_code != 200:
            break

        payload = resp.json()
        posts = payload.get("data", {}).get("children", [])
        if not posts:
            break

        for post in posts:
            post_data = post.get("data", {})
            title = post_data.get("title", "") or ""
            selftext = post_data.get("selftext", "") or ""
            description = " ".join((selftext or "").split()[:200]) or ""
            url = post_data.get("url") or post_data.get("url_overridden_by_dest") or ""
            author = post_data.get("author") or ""
            created_utc = post_data.get("created_utc")
            created_at = None
            try:
                created_at = datetime.utcfromtimestamp(float(created_utc)).strftime("%Y-%m-%d %H:%M:%S") if created_utc else None
            except Exception:
                created_at = None

            image_url = extract_image_url(post_data)

            results.append({
                "title": title,
                "description": (description + '...') if description else "",
                "full_description": selftext or "",
                "url": url,
                "author": author,
                "created_at": created_at,
                "image_url": image_url
            })

            fetched += 1
            if fetched >= MAX_POSTS:
                break

        after = payload.get("data", {}).get("after")
        if not after or fetched >= MAX_POSTS:
            break

    # Reorder so more relevant items appear first
    def relevance_key(item):
        score = 0
        if is_relevant_to_query(item.get("title", ""), item.get("full_description", ""), query):
            score += 10
        if query and query.lower() in (item.get("full_description", "") or "").lower():
            score += 5
        if item.get("image_url"):
            score += 1
        created = item.get("created_at")
        try:
            dt = datetime.strptime(created, "%Y-%m-%d %H:%M:%S") if created else datetime.utcfromtimestamp(0)
        except Exception:
            dt = datetime.utcfromtimestamp(0)
        return (score, dt)

    results_sorted = sorted(results, key=relevance_key, reverse=True)

    # Dedupe by url/title
    seen = set()
    deduped = []
    for r in results_sorted:
        key = (r.get("url") or "").strip() or (r.get("title") or "").strip()
        if not key:
            continue
        if key in seen:
            continue
        seen.add(key)
        deduped.append(r)

    return deduped

@app.route('/get-answer', methods=['GET'])
def get_answer():
    # Query param
    query = request.args.get('query', '').strip()
    if not query:
        return jsonify({"error": "Query parameter is missing!"}), 400

    # Page param (1-based). If invalid, fallback to 1.
    try:
        page = max(1, int(request.args.get('page', 1)))
    except Exception:
        page = 1

    # Page size param (optional override)
    try:
        page_size = int(request.args.get('page_size', PAGE_SIZE))
        if page_size <= 0:
            page_size = PAGE_SIZE
    except Exception:
        page_size = PAGE_SIZE

    # Collect all results (up to MAX_POSTS)
    all_results = search_reddit_collect_all(query)
    total_results = len(all_results)
    total_pages = max(1, ceil(total_results / page_size))

    # Ensure requested page is within bounds
    if page > total_pages:
        page = total_pages

    # Slice results for the requested page (0-based slice)
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    page_results = all_results[start_idx:end_idx]

    response = {
        "query": query,
        "page": page,
        "page_size": page_size,
        "total_results": total_results,
        "total_pages": total_pages,
        "has_next": page < total_pages,
        "has_prev": page > 1,
        "results": page_results
    }

    return jsonify(response)

if __name__ == "__main__":
    app.run(debug=True)
