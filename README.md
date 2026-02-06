# Recipe Manager Web App

A beautiful web application to browse and view your Google Docs recipe collection. Select any recipe from a dropdown to view recipe links, quick recipe information, and notes.

## Features

- **Recipe Dropdown**: Select any recipe from a dropdown menu at the top of the page
- **Recipe Links**: Clickable "Recipe" button that links to the full recipe URL
- **Quick Recipe**: Automatically displays quick recipe information (e.g., "Oven: 400 deg - 30-40 min")
- **Notes**: Automatically displays recipe notes (special instructions or modifications)
- **Modern UI**: Beautiful, responsive design with gradient styling
- **Recipe URL Mapping**: Easy configuration of recipe URLs via JSON file

## Setup

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set up Google Cloud credentials:**
   - Set the `GOOGLE_SERVICE_ACCOUNT` environment variable to point to your service account JSON file
   - Example: `export GOOGLE_SERVICE_ACCOUNT=/path/to/service-account.json`

3. **Share your documents:**
   - Run `python3 share_document.py` to get your service account email: `self-550@creds-443417.iam.gserviceaccount.com`
   - **Main Recipe Document**: Already shared (ID: `1ZKRBHoqKoQQ7RcnHoNtLtx0O0ae7ZMHF_XF1UUNp2kY`)
   - **Quick Recipe Document**: Share this document with the service account:
     - URL: https://docs.google.com/document/d/1BpJj3ECDU2Z_QYcorncs3SbeiKUD_WI_Lj29hnRjI18/edit
     - Click "Share" and add `self-550@creds-443417.iam.gserviceaccount.com` as a Viewer

4. **Add Recipe URLs (optional):**
   - Edit `recipe_urls.json` to add recipe URLs
   - Format: `{"Recipe Name": "https://recipe-url.com"}`
   - Example: `{"Chicken Thighs": "https://iowagirleats.com/baked-chicken-thighs/#wprm-recipe-container-145028"}`

## Usage

### Start the Web Server

```bash
python3 app.py
```

Then open your browser and go to:
```
http://localhost:5001
```

**Note:** Port 5001 is used instead of 5000 to avoid conflicts with macOS AirPlay Receiver.

### Get Service Account Email
```bash
python3 share_document.py
```

## Document Format

Your Google Doc should have recipes formatted like:

```
Chicken Breast Recipe Quick_Recipe
[Recipe link here]
[Quick recipe instructions]

Chicken Noodle Soup Recipe
[Recipe link here]
Note: from Jack: I didn't make the noodles and used a rotisserie chicken
```

The parser extracts:
- Recipe titles (e.g., "Chicken Breast", "Chicken Noodle Soup")
- Recipe links (clickable links to the full recipe)
- Quick Recipe sections (when available)
- Notes (special instructions or modifications)

## Static Site (GitHub Pages)

A schedule-only static site is available at **dustinwicker.github.io/recipe_manager** (or recipe-manager, depending on repo name). No Refresh button — recipes are updated daily by GitHub Actions.

### Setup

1. **Enable GitHub Pages**  
   Repo Settings → Pages → Source: Deploy from branch → branch `main`, folder `/` (root).

2. **Add secret**  
   Settings → Secrets and variables → Actions → add `GOOGLE_SERVICE_ACCOUNT_JSON` with the full service account JSON.

3. **Run workflow**  
   Actions → Refresh Recipes → Run workflow (or wait for the daily 6 AM UTC run).

The workflow runs `fetch_recipes.py` to write `data/recipes.json`, then commits and pushes. The static `index.html` loads recipes from that file.

### URL note

For **dustinwicker.github.io/recipe_manager**, the repo must be named `recipe_manager`. If the repo is `recipe-manager`, the URL will be `dustinwicker.github.io/recipe-manager`.

## Project Structure

```
recipes/
├── app.py                    # Flask web application
├── index.html                # Static site for GitHub Pages
├── fetch_recipes.py          # Fetches recipes → data/recipes.json (used by Actions)
├── recipe_parser.py          # Main recipe parser
├── quick_recipe_parser.py    # Quick Recipe document parser
├── creds.py                  # Google API credentials handler
├── share_document.py         # Helper to get service account email
├── recipe_urls.json          # Recipe URL mappings
├── data/
│   └── recipes.json         # Cached recipes (updated by workflow)
├── requirements.txt          # Python dependencies
├── .github/workflows/
│   └── refresh-recipes.yml  # Daily recipe refresh
├── templates/
│   └── index.html           # Flask web interface
└── README.md                # This file
```

## How It Works

1. The app parses your main Google Doc to extract recipe titles
2. Recipe URLs are loaded from `recipe_urls.json` (or default to the Google Doc)
3. Quick Recipe information is loaded from a separate Google Doc
4. When you select a recipe, the web interface displays:
   - A clickable "Recipe" link
   - Quick Recipe information (if available)
   - Notes (if available)

## License

MIT

