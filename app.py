#!/usr/bin/env python3
"""
Flask web application for recipe management.
"""

from flask import Flask, render_template, jsonify
from recipe_parser import RecipeParser
import os

app = Flask(__name__)

# Document IDs
DOC_ID = '1ZKRBHoqKoQQ7RcnHoNtLtx0O0ae7ZMHF_XF1UUNp2kY'
QUICK_RECIPE_DOC_ID = '1BpJj3ECDU2Z_QYcorncs3SbeiKUD_WI_Lj29hnRjI18'

# Cache recipes
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
    """Main page with recipe dropdown."""
    recipes = get_recipes()
    # Sort recipes alphabetically by title
    recipes = sorted(recipes, key=lambda x: x['title'].lower())
    return render_template('index.html', recipes=recipes)


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

