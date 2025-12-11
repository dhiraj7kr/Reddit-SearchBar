from flask import Flask, jsonify, request
from flask_cors import CORS
import requests

app = Flask(__name__)

# Enable CORS for all routes
CORS(app)

# Function to search Reddit and fetch relevant posts
def search_reddit(query):
    # URL to the Reddit search API endpoint (recent posts)
    url = f"https://www.reddit.com/r/all/search.json?q={query}&sort=relevance&limit=10&t=day"  # 't=day' fetches posts from the last 24 hours
    
    # Make the request to Reddit API with User-Agent header to prevent being blocked
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    # Send GET request to Reddit API
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        # Parse JSON response
        data = response.json()
        posts = data.get('data', {}).get('children', [])
        
        # Extract titles, descriptions, URLs, and image URLs of posts
        results = []
        for post in posts:
            post_data = post['data']
            title = post_data['title']
            description = post_data['selftext'] if post_data['selftext'] else "No description available."
            # Trim description to 3 lines (or a certain character length)
            description = ' '.join(description.split()[:100])  # Get first 50 words (or you can split by sentences)
            url = post_data['url']
            author = post_data['author']
            created_utc = post_data['created_utc']
            
            # Convert timestamp to human-readable format
            from datetime import datetime
            created_at = datetime.utcfromtimestamp(created_utc).strftime('%Y-%m-%d %H:%M:%S')
            
            # Check for image in the post (either from direct media or image URLs in the content)
            image_url = None
            if 'preview' in post_data and 'images' in post_data['preview']:
                # Look for images if preview is present
                image_url = post_data['preview']['images'][0].get('source', {}).get('url')
            
            results.append({
                "title": title,
                "description": description + '...',  # Add ellipsis to indicate truncated description
                "url": url,
                "author": author,
                "created_at": created_at,
                "image_url": image_url
            })
        
        return results
    else:
        return [{"title": "No relevant posts found", "description": "We couldn't find any relevant posts.", "url": "", "image_url": None}]

# Route to handle the question and return Reddit search results
@app.route('/get-answer', methods=['GET'])
def get_answer():
    # Get the query from the request parameters
    query = request.args.get('query', '')
    
    if not query:
        return jsonify({"error": "Query parameter is missing!"}), 400
    
    # Fetch relevant posts from Reddit
    reddit_results = search_reddit(query)
    
    return jsonify({"results": reddit_results})

if __name__ == "__main__":
    app.run(debug=True)
