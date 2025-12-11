from flask import Flask, jsonify, request
from flask_cors import CORS
import requests
import html
from datetime import datetime

app = Flask(__name__)
CORS(app)

HEADERS = {
    "User-Agent": "MyRedditSearchApp/1.0"
}

def clean_preview_url(url):
    if not url: return None
    u = html.unescape(str(url))
    if u.startswith("//"): u = "https:" + u
    if u.startswith("preview.redd.it") or u.startswith("i.redd.it") or u.startswith("i.reddituploads.com"):
        u = "https://" + u
    return u

def extract_image_url(post_data):
    # (Same image extraction logic as before)
    preview = post_data.get("preview")
    if preview and isinstance(preview, dict):
        images = preview.get("images")
        if images and isinstance(images, list) and images:
            src = images[0].get("source", {}).get("url")
            if src: return clean_preview_url(src)

    media_metadata = post_data.get("media_metadata")
    if media_metadata and isinstance(media_metadata, dict):
        for key, meta in media_metadata.items():
            if isinstance(meta, dict):
                s = meta.get("s")
                if s and s.get("u"): return clean_preview_url(s.get("u"))
                if meta.get("p") and isinstance(meta.get("p"), list):
                    last = meta["p"][-1]
                    if last and last.get("u"): return clean_preview_url(last.get("u"))

    url_override = post_data.get("url_overridden_by_dest")
    if url_override:
        if any(url_override.lower().endswith(ext) for ext in (".jpg", ".jpeg", ".png", ".gif", ".webp")):
            return clean_preview_url(url_override)

    thumbnail = post_data.get("thumbnail")
    if thumbnail and thumbnail.startswith("http"):
        return clean_preview_url(thumbnail)
    return None

# --- NEW FUNCTION: Search Subreddits ---
def search_communities(query):
    url = "https://www.reddit.com/subreddits/search.json"
    params = {
        "q": query,
        "limit": 5, # We only need the top 5 communities
        "sort": "relevance"
    }
    try:
        resp = requests.get(url, headers=HEADERS, params=params, timeout=5)
        if resp.status_code != 200: return []
        
        children = resp.json().get("data", {}).get("children", [])
        communities = []
        
        for item in children:
            data = item.get("data", {})
            icon = data.get("icon_img") or data.get("community_icon") or ""
            # clean up icon url
            if "?" in icon: icon = icon.split("?")[0] 
            
            communities.append({
                "name": data.get("display_name_prefixed"), # e.g. r/python
                "title": data.get("title"),
                "subscribers": data.get("subscribers"),
                "description": data.get("public_description", "")[:100] + "...",
                "icon": clean_preview_url(icon),
                "url": "https://www.reddit.com" + data.get("url")
            })
        return communities
    except Exception as e:
        print(f"Community search error: {e}")
        return []

@app.route('/get-answer', methods=['GET'])
def get_answer():
    query = request.args.get('query', '').strip()
    after_token = request.args.get('after', '').strip()
    
    if not query:
        return jsonify({"error": "Query parameter is missing!"}), 400

    # 1. Fetch Posts (Existing Logic)
    base_url = "https://www.reddit.com/r/all/search.json"
    params = {
        "q": query,
        "sort": "relevance",
        "t": "all",
        "limit": 15,
        "count": 0
    }
    if after_token and after_token != 'null':
        params["after"] = after_token

    try:
        resp = requests.get(base_url, headers=HEADERS, params=params, timeout=5)
        if resp.status_code != 200:
             return jsonify({"error": "Reddit API error", "results": []}), resp.status_code
        
        payload = resp.json()
        data = payload.get("data", {})
        children = data.get("children", [])
        next_after = data.get("after")
        
        results = []
        for post in children:
            post_data = post.get("data", {})
            # (Data extraction same as before)
            title = post_data.get("title", "") or ""
            selftext = post_data.get("selftext", "") or ""
            description = " ".join((selftext or "").split()[:50])
            url = post_data.get("url") or post_data.get("url_overridden_by_dest") or ""
            author = post_data.get("author") or ""
            created_utc = post_data.get("created_utc")
            created_at = None
            if created_utc:
                try: created_at = datetime.utcfromtimestamp(float(created_utc)).strftime("%Y-%m-%d %H:%M:%S")
                except: pass
            
            results.append({
                "title": title,
                "description": (description + '...') if description else "",
                "full_description": selftext or "",
                "url": url,
                "author": author,
                "created_at": created_at,
                "image_url": extract_image_url(post_data)
            })

        # 2. Fetch Communities (Only on first page)
        communities = []
        if not after_token or after_token == 'null':
            communities = search_communities(query)

        response = {
            "query": query,
            "results": results,
            "communities": communities, # Send communities to frontend
            "after": next_after,
            "count": len(results)
        }
        return jsonify(response)

    except requests.RequestException as e:
        print(f"Error: {e}")
        return jsonify({"error": "Backend connection error"}), 500

if __name__ == "__main__":
    app.run(debug=True)