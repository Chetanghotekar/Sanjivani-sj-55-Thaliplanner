"""Day 3: Download source pages into data/raw/."""
from pathlib import Path
import requests

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
PAGES = {
    "indian_recipes.html": "https://en.wikibooks.org/wiki/Cookbook:Indian_Recipes",
    "dal_recipes.html": "https://en.wikibooks.org/wiki/Cookbook:Dal",
    "rice_recipes.html": "https://en.wikibooks.org/wiki/Cookbook:Rice",
}

def fetch_pages():
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    headers = {"User-Agent": "ThaliPlannerStudentProject/1.0 (educational use)"}
    for filename, url in PAGES.items():
        destination = RAW_DIR / filename
        try:
            response = requests.get(url, headers=headers, timeout=20)
            response.raise_for_status()
            destination.write_text(response.text, encoding="utf-8")
            print(f"Downloaded: {filename}")
        except requests.RequestException as exc:
            print(f"Could not download {url}: {exc}")

if __name__ == "__main__":
    fetch_pages()
