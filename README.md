# World News Globe

A slowly rotating globe that pops up the latest headlines for each country as it turns into view, with day/night shading for the current time and ambient background music.

## How the news stays fresh

- `.github/workflows/update-news.yml` runs every 30 minutes on GitHub.
- It runs `scripts/fetch_news.py`, which asks the free GDELT news index for the newest articles from each of 64 countries' press and writes `news.json`.
- `index.html` reads `news.json` from the same site every 5 minutes. The badge at the top right shows **Live · N countries** when this is working.

## Setup on GitHub Pages

1. Put these files in the repository the site is published from (keep the folders as they are).
2. In the repository, go to **Settings → Actions → General → Workflow permissions** and choose **Read and write permissions**, then Save.
3. Go to the **Actions** tab, pick **Update news**, and click **Run workflow** to fill `news.json` the first time (takes about 6–8 minutes).
4. Make sure **Settings → Pages** publishes from the branch the workflow commits to (normally `main`).

## Adding a country

Add it to `COUNTRIES` in `scripts/fetch_news.py` (GDELT country name without spaces, or its FIPS code) and to `COUNTRIES` in `index.html` with the same ISO code and its longitude/latitude.
