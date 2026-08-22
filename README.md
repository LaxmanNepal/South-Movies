# SOUTH MOVIES

South Indian Cinema. One Place.

A mobile-first movie discovery platform for Telugu, Tamil, Kannada, and Malayalam cinema. Movies are discovered from publicly available, embeddable YouTube videos and played only through YouTube's permitted embed player.

## Architecture

YouTube Data API → GitHub Actions discovery → validation/filtering → duplicate detection → source verification → ranking → JSON catalog → static page generation → GitHub Pages.

No movie video files are downloaded, proxied, re-hosted, or redistributed.

## Setup

1. Add a repository secret named `YOUTUBE_API_KEY`.
2. Enable GitHub Pages from the `main` branch root.
3. Run **Update South Movies Catalog** manually once to populate the catalog.
4. The workflow runs every 6 hours afterward.

The frontend never receives the YouTube API key. All discovery and metadata enrichment happen in GitHub Actions.
