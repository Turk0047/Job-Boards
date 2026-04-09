# Discord Job Feed for MEE6 via GitHub Pages

This repo builds a single RSS feed from multiple job boards and publishes it to GitHub Pages so MEE6 can read it.

## What this repo does

- pulls job feeds from multiple sources
- filters for art, animation, and game-related roles
- deduplicates items
- writes one RSS 2.0 XML file at `docs/feed.xml`
- deploys that XML file to GitHub Pages automatically every 30 minutes

## Files

- `scripts/build_feed.py` — merges feeds and builds the XML output
- `config/sources.json` — where you enable feeds and paste your generated RSS links
- `.github/workflows/build-and-deploy.yml` — GitHub Actions workflow
- `docs/feed.xml` — published output used by MEE6

## Setup

### 1) Create a new GitHub repo

Create a repo such as `discord-job-feed`.

### 2) Paste these files into the repo

Keep the folder structure exactly the same.

### 3) Turn on GitHub Pages

In **Settings → Pages**, set the site to deploy from **GitHub Actions**.

### 4) Edit `config/sources.json`

Replace:

- `YOUR_GITHUB_USERNAME`
- `YOUR_REPO_NAME`

Then enable or disable sources.

For boards that do not have a native RSS feed, generate a feed URL using a feed generation service and paste it into `feed_url`.

### 5) Run the workflow

Go to **Actions → Build and deploy jobs RSS → Run workflow**.

When it finishes, your feed should be live at:

```text
https://YOUR_GITHUB_USERNAME.github.io/YOUR_REPO_NAME/feed.xml
```

That is the URL you paste into MEE6.

## Example MEE6 flow

- open MEE6 dashboard
- go to RSS
- add feed URL
- choose your jobs channel
- test post formatting

## Recommended first sources

Start with these enabled first:

- We Work Remotely
- Jobicy
- one or two generated niche feeds such as ArtStation or Hitmarker

Then expand after you confirm the volume is manageable.

## Notes

- GitHub Actions scheduled workflows use cron syntax and run in UTC.
- GitHub Pages can publish from a custom GitHub Actions workflow.
- GitHub recommends Actions as the publishing approach for GitHub Pages custom builds.
