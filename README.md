# SOUTH MOVIES

**South Indian Cinema. One Place.**

A mobile-first South Indian movie discovery platform focused **exclusively on Hindi-dubbed Telugu, Tamil, Kannada, and Malayalam movies** that are publicly available and embeddable on YouTube.

## What the catalog means

- `language` = original South Indian cinema language.
- `audioLanguage` = Hindi.
- `dubbed` = `true`.
- The uploader is preserved as the **Original YouTube Source**; uploader identity is not treated as proof of movie ownership.
- Unknown rights/ownership information is never fabricated.

## Architecture

YouTube Data API → GitHub Actions discovery → Hindi-dubbed filtering → public/embeddable validation → duplicate detection → source verification → ranking → JSON catalog → static page generation → GitHub Pages.

The frontend also filters the catalog defensively, so a non-Hindi record cannot be displayed even if stale data is accidentally committed.

No movie video files are downloaded, proxied, re-hosted, or redistributed. Playback uses YouTube's permitted embedded player.

## Setup

1. Add a repository secret named `YOUTUBE_API_KEY`.
2. Enable GitHub Pages from the `main` branch root.
3. Run **Update South Movies Catalog** manually once.
4. The catalog refreshes every 6 hours.
5. Health Check runs separately every 6 hours and validates source availability and Hindi-dubbed scope.

The YouTube API key is never sent to frontend JavaScript; discovery happens in GitHub Actions.
