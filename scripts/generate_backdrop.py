"""
Dynamic Backdrop Generator for Nuvio Collections
Fetches poster images from TMDB for a given list of IMDB IDs
and composites them into a single backdrop image.

Requirements: requests, Pillow (installed via requirements.txt)
"""

import os
import requests
import json
from PIL import Image
from io import BytesIO

# ─── CONFIGURATION ───────────────────────────────────────────────
TMDB_API_KEY = os.environ.get("TMDB_API_KEY")   # Set in GitHub Secrets
BACKDROP_WIDTH = 1920
BACKDROP_HEIGHT = 600
POSTER_HEIGHT = 600
# ─────────────────────────────────────────────────────────────────


def get_tmdb_poster(imdb_id):
    """Fetch the poster image for a title using its IMDB ID."""
    # First, find the TMDB ID from the IMDB ID
    find_url = f"https://api.themoviedb.org/3/find/{imdb_id}"
    params = {
        "api_key": TMDB_API_KEY,
        "external_source": "imdb_id"
    }
    response = requests.get(find_url, params=params, timeout=10)
    data = response.json()

    results = data.get("movie_results", []) or data.get("tv_results", [])
    if not results:
        return None

    poster_path = results[0].get("poster_path")
    if not poster_path:
        return None

    img_url = f"https://image.tmdb.org/t/p/w342{poster_path}"
    img_response = requests.get(img_url, timeout=10)
    return Image.open(BytesIO(img_response.content)).convert("RGB")


def generate_backdrop(catalog_name, imdb_ids, output_path):
    """Generate a backdrop collage from a list of IMDB IDs."""
    print(f"  Generating backdrop for: {catalog_name}")
    posters = []

    for imdb_id in imdb_ids[:20]:   # Use up to 20 titles
        print(f"    Fetching poster for {imdb_id}...")
        try:
            img = get_tmdb_poster(imdb_id)
            if img:
                # Resize poster to standard height, keep aspect ratio
                ratio = POSTER_HEIGHT / img.height
                new_width = int(img.width * ratio)
                img = img.resize((new_width, POSTER_HEIGHT), Image.LANCZOS)
                posters.append(img)
        except Exception as e:
            print(f"    Warning: Could not fetch poster for {imdb_id}: {e}")

    if not posters:
        print(f"  No posters found for {catalog_name}, skipping.")
        return

    # Build collage
    total_width = sum(p.width for p in posters)
    collage = Image.new("RGB", (total_width, POSTER_HEIGHT))
    x_offset = 0
    for poster in posters:
        collage.paste(poster, (x_offset, 0))
        x_offset += poster.width

    # Crop/resize to final backdrop dimensions
    if collage.width < BACKDROP_WIDTH:
        # Tile horizontally if not wide enough
        tiles_needed = (BACKDROP_WIDTH // collage.width) + 1
        tiled = Image.new("RGB", (collage.width * tiles_needed, POSTER_HEIGHT))
        for i in range(tiles_needed):
            tiled.paste(collage, (i * collage.width, 0))
        collage = tiled

    # Center-crop to 1920×600
    left = (collage.width - BACKDROP_WIDTH) // 2
    collage = collage.crop((left, 0, left + BACKDROP_WIDTH, BACKDROP_HEIGHT))

    # Save
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    collage.save(output_path, "PNG", optimize=True)
    print(f"  ✅ Saved: {output_path}")


def main():
    catalogs_dir = "catalogs"
    backdrops_dir = "backdrops"

    if not os.path.exists(catalogs_dir):
        print("No catalogs/ folder found. Nothing to do.")
        return

    for filename in os.listdir(catalogs_dir):
        if not filename.endswith(".json"):
            continue

        catalog_path = os.path.join(catalogs_dir, filename)
        with open(catalog_path, "r") as f:
            catalog = json.load(f)

        catalog_name = catalog.get("name", filename.replace(".json", ""))
        imdb_ids = catalog.get("imdb_ids", [])
        output_file = os.path.join(backdrops_dir, filename.replace(".json", ".png"))

        generate_backdrop(catalog_name, imdb_ids, output_file)


if __name__ == "__main__":
    main()
