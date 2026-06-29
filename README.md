# Spotify
🎵 Spotify Discovery Agent


An AI-powered agent that ingests, analyzes, and surfaces insights from Spotify user reviews across multiple platforms.




🚧 Project Status

This project is currently in active development.

PhaseDescriptionStatusPhase 1Data Ingestion Pipeline✅ In ProgressPhase 2Data Cleaning & Preprocessing🔜 PlannedPhase 3Sentiment & Theme Analysis🔜 PlannedPhase 4Discovery Agent & Insights🔜 Planned


📌 Overview

The Spotify Discovery Agent collects user reviews and feedback from multiple sources to help identify patterns, pain points, and feature requests that Spotify users express across different platforms.

Rather than relying on a single source, this agent aggregates data from 4 distinct channels to build a comprehensive picture of user sentiment.


📦 Data Sources

SourceRecords IngestedStatusGoogle Play Store2,649✅ CompleteApple App Store499✅ CompleteSpotify Community Forum155✅ CompleteReddit0🔄 In Progress

Total records ingested so far: 3,303


🗂️ Project Structure

Spotify/
├── docs/
│   └── phases/
│       └── phase-1-ingestion/
│           └── data/
│               ├── raw_reviews.json        # All ingested reviews
│               └── phase1_ingest_log.json  # Ingestion metadata & stats
├── .gitignore
├── ProblemStatement.md
└── README.md


⚙️ Phase 1 — Data Ingestion

The first phase focuses on collecting raw review data from all target platforms and storing it in a unified JSON format.

What's been done:


Scraped reviews from Google Play Store, Apple App Store, and Spotify Community Forum
Stored all records in a single raw_reviews.json file
Generated an ingestion log (phase1_ingest_log.json) tracking source counts and completion time


What's in progress:


Reddit integration — requires Reddit API credentials (PRAW)
Target subreddits: r/spotify, r/androidapps, r/iosapps



🔧 Setup & Installation


⚠️ Full setup instructions will be added as the project progresses.



Prerequisites


Python 3.8+
pip


Install dependencies

bashpip install -r requirements.txt

Reddit API Setup

To enable Reddit data ingestion, you will need to:


Create a Reddit account at reddit.com
Go to reddit.com/prefs/apps
Create a new script type application
Copy your client_id and client_secret
Create a .env file in the project root:


envREDDIT_CLIENT_ID=your_client_id_here
REDDIT_CLIENT_SECRET=your_client_secret_here
REDDIT_USER_AGENT=spotify-discovery-agent/1.0 by u/your_username
