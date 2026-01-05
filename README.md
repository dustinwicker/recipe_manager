# Recipe Manager Web App

A web application to browse and view your Google Docs recipe collection.

## Features

- **Recipe Dropdown**: Select any recipe from a dropdown menu
- **Recipe Links**: Clickable links to the full recipe
- **Quick Recipe**: View quick recipe information when available
- **Notes**: View recipe notes (like special instructions or modifications)

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

