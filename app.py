from flask import Flask, jsonify, request
from flask_cors import CORS
import requests
import html
from datetime import datetime, timezone
from yt_dlp import YoutubeDL
import math
from concurrent.futures import ThreadPoolExecutor

app = Flask(__name__)
CORS(app)

HEADERS = { "User-Agent": "MyRedditSearchApp/2.0" }
WEIGHT_ENGAGEMENT = 0.4
WEIGHT_RECENCY = 0.3
WEIGHT_MATCH = 0.3

# --- Utilities ---
def clean_preview_url(url):
    if not url: return None
    u = html.unescape(str(url))
    if u.startswith("//"): u = "https:" + u
    if u.startswith("preview.redd.it") or u.startswith("i.redd.it"):
        u = "https://" + u
    return u

def extract_image_url(post_data):
    preview = post_data.get("preview")
    if preview and isinstance(preview, dict):
        images = preview.get("images")
        if images and isinstance(images, list) and images:
            src = images[0].get("source", {}).get("url")
            if src: return clean_preview_url(src)
    url_over = post_data.get("url_overridden_by_dest")
    if url_over and any(url_over.lower().endswith(ext) for ext in (".jpg", ".png", ".jpeg", ".webp")):
        return clean_preview_url(url_over)
    thumb = post_data.get("thumbnail")
    if thumb and thumb.startswith("http"):
        return clean_preview_url(thumb)
    return None

def calculate_relevance_score(item, query):
    raw_score = item.get('score', 0) or item.get('views', 0)
    engagement_score = min(math.log10(raw_score + 1), 10) / 10.0 

    try:
        if 'created_utc' in item:
            item_date = datetime.fromtimestamp(item['created_utc'], timezone.utc)
        elif 'upload_date' in item:
            item_date = datetime.strptime(item['upload_date'], "%Y%m%d").replace(tzinfo=timezone.utc)
        else:
            item_date = datetime.now(timezone.utc)
        days_old = (datetime.now(timezone.utc) - item_date).days
        recency_score = 1 / (1 + (days_old / 365.0))
    except:
        recency_score = 0.5

    title_lower = (item.get('title') or "").lower()
    query_lower = query.lower()
    match_score = 0.0
    if query_lower in title_lower: match_score = 1.0
    else:
        words = query_lower.split()
        matches = sum(1 for w in words if w in title_lower)
        if len(words) > 0: match_score = matches / len(words)

    return (engagement_score * WEIGHT_ENGAGEMENT) + (recency_score * WEIGHT_RECENCY) + (match_score * WEIGHT_MATCH)

def rank_results(items, query):
    for item in items: item['ranking_score'] = calculate_relevance_score(item, query)
    return sorted(items, key=lambda x: x['ranking_score'], reverse=True)

# --- REDDIT FETCH ---
def fetch_reddit_posts(query, sort_type, limit=25, after=None):
    base_url = "https://www.reddit.com/r/all/search.json"
    params = { "q": query, "limit": limit, "sort": sort_type, "t": "all" }
    if after and after != 'null': params["after"] = after

    try:
        resp = requests.get(base_url, headers=HEADERS, params=params, timeout=3)
        if resp.status_code != 200: return [], None
        data = resp.json().get("data", {})
        
        parsed = []
        for post in data.get("children", []):
            p = post.get("data", {})
            created_utc = p.get("created_utc", 0)
            try:
                dt = datetime.fromtimestamp(created_utc, timezone.utc)
                date_str = dt.strftime("%Y-%m-%d")
            except: date_str = "N/A"

            parsed.append({
                "title": p.get("title"),
                "description": (p.get("selftext", "")[:150] + "...") if p.get("selftext") else "",
                "full_description": p.get("selftext", ""), 
                "url": p.get("url"),
                "author": p.get("author"),
                "created_at": date_str,
                "created_utc": created_utc,
                "image_url": extract_image_url(p),
                "score": p.get("score", 0)
            })
        return parsed, data.get("after")
    except: return [], None

# --- YOUTUBE FETCH (Optimized) ---
def search_youtube_smart(query, page=1):
    start = ((page - 1) * 15) + 1
    end = start + 14 
    
    ydl_opts = {
        'quiet': True,
        'extract_flat': True,
        'noplaylist': True,
        'playliststart': start,
        'playlistend': end,
        'ignoreerrors': True,
        'no_warnings': True,
        'nocheckcertificate': True, 
        'geo_bypass': False,
    }
    
    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"ytsearch{end}:{query}", download=False)
            entries = info.get('entries', [])
            
            clean_entries = []
            for v in entries:
                if not v: continue
                clean_entries.append({
                    "title": v.get("title"),
                    "url": v.get("url"),
                    "id": v.get("id"),
                    "thumbnail": f"https://img.youtube.com/vi/{v.get('id')}/mqdefault.jpg",
                    "channel": v.get("uploader"),
                    "views": v.get("view_count") or 0,
                    "upload_date": v.get("upload_date") or "20000101"
                })

            ranked_videos = rank_results(clean_entries, query)
            
            channels = []
            seen_channels = set()
            for video in ranked_videos: 
                c_name = video.get("channel")
                if c_name and c_name not in seen_channels:
                    seen_channels.add(c_name)
                    channels.append({
                        "name": c_name,
                        "url": f"https://www.youtube.com/results?search_query={c_name}",
                        "icon": None 
                    })
            
            return ranked_videos, channels[:5]
    except Exception as e:
        print(f"YouTube Error: {e}")
        return [], []

def search_communities(query):
    url = "https://www.reddit.com/subreddits/search.json"
    params = { "q": query, "limit": 5, "sort": "relevance" }
    try:
        resp = requests.get(url, headers=HEADERS, params=params, timeout=3)
        children = resp.json().get("data", {}).get("children", [])
        communities = []
        for item in children:
            data = item.get("data", {})
            icon = data.get("icon_img") or data.get("community_icon") or ""
            if "?" in icon: icon = icon.split("?")[0]
            communities.append({
                "name": data.get("display_name_prefixed"),
                "subscribers": data.get("subscribers"),
                "icon": clean_preview_url(icon),
                "url": "https://www.reddit.com" + data.get("url")
            })
        return communities
    except: return []

# --- NEW: Get Trending Topics ---
@app.route('/get-trending', methods=['GET'])
def get_trending():
    # Fetches popular subreddits to use as trending topics
    url = "https://www.reddit.com/subreddits/popular.json"
    params = { "limit": 10 }
    try:
        resp = requests.get(url, headers=HEADERS, params=params, timeout=3)
        children = resp.json().get("data", {}).get("children", [])
        trending = []
        for item in children:
            name = item.get("data", {}).get("display_name")
            if name: trending.append(name)
        return jsonify(trending)
    except:
        # Fallback if API fails
        return jsonify(["Technology", "Movies", "Science", "Gaming", "WorldNews", "Programming", "Space", "Music"])

# --- ROUTES ---

@app.route('/get-answer', methods=['GET'])
def get_answer():
    query = request.args.get('query', '').strip()
    after_token = request.args.get('after', '').strip()
    if not query: return jsonify({"error": "Missing query"}), 400

    with ThreadPoolExecutor() as executor:
        future_rel = executor.submit(fetch_reddit_posts, query, "relevance", 20, after_token)
        future_new = None
        if not after_token or after_token == 'null':
            future_new = executor.submit(fetch_reddit_posts, query, "new", 15)
        
        future_comm = None
        if not after_token or after_token == 'null':
            future_comm = executor.submit(search_communities, query)

        rel_posts, next_after = future_rel.result()
        new_posts = []
        if future_new: new_posts, _ = future_new.result()
        communities = []
        if future_comm: communities = future_comm.result()

    all_posts = rel_posts + new_posts
    seen = set()
    unique_posts = []
    for p in all_posts:
        if p['url'] not in seen:
            seen.add(p['url'])
            unique_posts.append(p)

    final_results = rank_results(unique_posts, query)

    return jsonify({
        "results": final_results[:15],
        "communities": communities,
        "after": next_after
    })

@app.route('/get-videos', methods=['GET'])
def get_videos():
    query = request.args.get('query', '').strip()
    try: page = int(request.args.get('page', 1))
    except: page = 1
    if not query: return jsonify([])
    
    videos, channels = search_youtube_smart(query, page)
    return jsonify({ "videos": videos, "channels": channels })

if __name__ == "__main__":
    app.run(debug=True, port=5000)