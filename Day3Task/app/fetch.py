import requests

urls = [
    "https://en.wikibooks.org/wiki/Category:Indian_recipes",
    "https://en.wikibooks.org/wiki/Cookbook:Cuisine_of_India",
    "https://en.wikibooks.org/wiki/Cookbook:Moong_Dal"
]

for url in urls:
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()

        print("Downloaded successfully:", url)

    except requests.exceptions.RequestException as e:
        print("Download failed:", url, e)