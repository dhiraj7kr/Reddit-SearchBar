
# Reddit Search Application

## Overview

**Reddit Search** is a powerful, multi-modal discovery tool designed to explore discussions, media, and communities across the Reddit ecosystem. It provides a streamlined, dark-themed interface that categorizes results into text, high-resolution images, and curated video feeds.

---

## User Interface Overview

The application is structured to provide a consistent experience from the landing page to specialized media results. Below is the visual guide to the primary views:

<p align="center">
<img src="[https://github.com/anextsar/AppPhoto/blob/main/RedditBrowserImage/Homepage.png?raw=true](https://github.com/anextsar/AppPhoto/blob/main/RedditBrowserImage/Homepage.png?raw=true)" width="24%" alt="Homepage" />
<img src="[https://github.com/anextsar/AppPhoto/blob/main/RedditBrowserImage/ALL.png?raw=true](https://github.com/anextsar/AppPhoto/blob/main/RedditBrowserImage/ALL.png?raw=true)" width="24%" alt="All Results" />
<img src="[https://github.com/anextsar/AppPhoto/blob/main/RedditBrowserImage/Image.png?raw=true](https://github.com/anextsar/AppPhoto/blob/main/RedditBrowserImage/Image.png?raw=true)" width="24%" alt="Image Results" />
<img src="[https://github.com/anextsar/AppPhoto/blob/main/RedditBrowserImage/Video.png?raw=true](https://github.com/anextsar/AppPhoto/blob/main/RedditBrowserImage/Video.png?raw=true)" width="24%" alt="Video Results" />
</p>

*From left to right: Landing Page, All (List) View, Image Grid, and Video Gallery.*

---

## Key Features

### 1. Multi-Modal Filtering

Users can instantly toggle between different content types using the navigation tabs:

* **All**: A comprehensive list view featuring post titles, short descriptions, and timestamps.
* **Images**: A visually-driven grid layout that extracts and displays images from relevant threads.
* **Videos**: A dedicated gallery featuring video thumbnails with integrated play icons.

### 2. Contextual Sidebar Recommendations

The application dynamically updates a sidebar to help users find where specific discussions are happening:

* **Communities**: Suggests relevant subreddits with subscriber counts and direct "Join" links.
* **Top Channels**: When searching for videos, the sidebar highlights major content creators with "Visit" options.

### 3. Smart Search & Discovery

* **Trending**: A dedicated button on the homepage allows users to jump into current popular topics.
* **Persistent Interface**: A top-navigation search bar allowing for quick queries from any result view.

---

## How It Works

1. **Search Input**: Enter a query into the centralized search bar on the landing page or the results dashboard.
2. **Data Fetching**: The application queries live Reddit data, extracting metadata such as timestamps, author names, and community details.
3. **Media Processing**: It automatically distinguishes between text-based discussions and media-rich threads to populate the Image and Video tabs.
4. **UI State Management**: Using a dark-theme aesthetic, the app manages layout transitions between list formats and responsive grid formats.

---

W
