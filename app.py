#!/usr/bin/env python3
"""
Flask web application for recipe management.
"""

from flask import Flask, jsonify, request, send_from_directory
from recipe_parser import RecipeParser
from pathlib import Path
import json
import threading
import time

app = Flask(__name__)

# Document IDs
DOC_ID = '1ZKRBHoqKoQQ7RcnHoNtLtx0O0ae7ZMHF_XF1UUNp2kY'
QUICK_RECIPE_DOC_ID = '1BpJj3ECDU2Z_QYcorncs3SbeiKUD_WI_Lj29hnRjI18'

# Cache recipes
recipes_cache = None
ACTIVITY_PATH = Path(__file__).resolve().parent / 'data' / 'recipe_activity.json'
_activity_lock = threading.Lock()


def load_activity():
    """Read visit and link counts stored on this computer."""
    if not ACTIVITY_PATH.exists():
        return {}
    try:
        data = json.loads(ACTIVITY_PATH.read_text())
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def save_activity(data):
    ACTIVITY_PATH.parent.mkdir(parents=True, exist_ok=True)
    ACTIVITY_PATH.write_text(json.dumps(data, indent=2) + '\n')


def clear_cache():
    """Clear the recipes cache so data is re-fetched from Google Docs."""
    global recipes_cache
    recipes_cache = None


def get_recipes():
    """Get recipes, using cache if available."""
    global recipes_cache
    if recipes_cache is None:
        parser = RecipeParser(DOC_ID, QUICK_RECIPE_DOC_ID)
        recipes_cache = parser.parse()
    return recipes_cache


@app.route('/')
def index():
    """Main page. Counts are stored on this computer, so the page is served from here."""
    return send_from_directory(Path(__file__).resolve().parent, 'index.html')


@app.route('/data/recipes.json')
def recipes_file():
    return send_from_directory(Path(__file__).resolve().parent / 'data', 'recipes.json')


@app.route('/api/activity', methods=['GET'])
def get_activity():
    """Return how often each recipe has been opened or its link clicked."""
    with _activity_lock:
        return jsonify(load_activity())


@app.route('/api/activity', methods=['POST'])
def record_activity():
    """Record one visit or outbound link click for a recipe."""
    body = request.get_json(silent=True) or {}
    title = str(body.get('title') or '').strip()
    kind = body.get('kind')
    if not title or kind not in ('visit', 'link'):
        return jsonify({'error': 'title and kind are required'}), 400
    with _activity_lock:
        data = load_activity()
        row = data.get(title) or {'visits': 0, 'linkClicks': 0, 'lastAt': 0}
        if kind == 'link':
            row['linkClicks'] = int(row.get('linkClicks') or 0) + 1
        else:
            row['visits'] = int(row.get('visits') or 0) + 1
        row['lastAt'] = int(time.time() * 1000)
        data[title] = row
        save_activity(data)
    return jsonify(row)


@app.route('/api/recipe/<recipe_title>')
def get_recipe(recipe_title):
    """Get recipe details by title."""
    recipes = get_recipes()
    
    # Find recipe by title (case-insensitive, handle URL encoding)
    import urllib.parse
    recipe_title = urllib.parse.unquote(recipe_title)
    
    for recipe in recipes:
        if recipe['title'].lower() == recipe_title.lower():
            return jsonify(recipe)
    
    return jsonify({'error': 'Recipe not found'}), 404


@app.route('/api/refresh', methods=['POST'])
def refresh_recipes():
    """Clear cache and re-fetch recipes from Google Docs."""
    clear_cache()
    get_recipes()  # Prime the cache
    return jsonify({'status': 'ok', 'message': 'Recipes refreshed'})


@app.route('/api/recipes')
def list_recipes():
    """Get list of all recipe titles."""
    recipes = get_recipes()
    # Sort recipes alphabetically by title
    recipes = sorted(recipes, key=lambda x: x['title'].lower())
    titles = [recipe['title'] for recipe in recipes]
    return jsonify(titles)


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)

