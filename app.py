from flask import Flask, jsonify, request
from flask_cors import CORS
import requests
import html
from datetime import datetime

app = Flask(__name__)
CORS(app)

# Configuration
HEADERS = {
    "User-Agent": "MyRedditSearchApp/1.0"
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
    # (Kept your original logic here as it works well)
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

@app.route('/get-answer', methods=['GET'])
def get_answer():
    query = request.args.get('query', '').strip()
    after_token = request.args.get('after', '').strip() # Reddit pagination cursor
    
    if not query:
        return jsonify({"error": "Query parameter is missing!"}), 400

    # Reddit API parameters
    base_url = "https://www.reddit.com/r/all/search.json"
    params = {
        "q": query,
        "sort": "relevance",
        "t": "all",
        "limit": 15, # Fetch only what is needed for the UI
        "count": 0
    }
    
    # If we are looking for the next page, pass the 'after' token
    if after_token and after_token != 'null':
        params["after"] = after_token

    try:
        resp = requests.get(base_url, headers=HEADERS, params=params, timeout=5)
        if resp.status_code != 200:
             return jsonify({"error": "Reddit API error", "results": []}), resp.status_code
        
        payload = resp.json()
        data = payload.get("data", {})
        children = data.get("children", [])
        next_after = data.get("after") # The token for the NEXT page
        
        results = []
        for post in children:
            post_data = post.get("data", {})
            
            # Extract basic data
            title = post_data.get("title", "") or ""
            selftext = post_data.get("selftext", "") or ""
            description = " ".join((selftext or "").split()[:50]) # Shorter preview
            url = post_data.get("url") or post_data.get("url_overridden_by_dest") or ""
            author = post_data.get("author") or ""
            created_utc = post_data.get("created_utc")
            
            created_at = None
            if created_utc:
                try:
                    created_at = datetime.utcfromtimestamp(float(created_utc)).strftime("%Y-%m-%d %H:%M:%S")
                except:
                    pass

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

        response = {
            "query": query,
            "results": results,
            "after": next_after, # Send this back to frontend for the "Next" button
            "count": len(results)
        }
        return jsonify(response)

    except requests.RequestException as e:
        print(f"Error: {e}")
        return jsonify({"error": "Backend connection error"}), 500

if __name__ == "__main__":
    app.run(debug=True)