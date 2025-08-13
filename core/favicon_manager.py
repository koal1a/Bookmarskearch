import os
import requests
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
import hashlib

# Define the cache directory for favicons
FAVICON_CACHE_DIR = "cache/favicons"

def _get_icon_url_from_html(html_content, page_url):
    """Parses HTML to find the best favicon URL."""
    soup = BeautifulSoup(html_content, 'html.parser')
    icon_links = []

    # Common rel values for favicons
    rel_attributes = ['icon', 'shortcut icon', 'apple-touch-icon', 'apple-touch-icon-precomposed']
    for rel in rel_attributes:
        links = soup.find_all('link', rel=rel)
        for link in links:
            if link.get('href'):
                icon_links.append(link)

    if not icon_links:
        return None

    # Simple approach: return the last one found (often the most modern definition)
    # A more complex approach could be to check 'sizes' attribute, but this is robust enough.
    best_link = icon_links[-1]['href']

    # Join the URL to handle relative paths like '/favicon.ico'
    return urljoin(page_url, best_link)

def get_favicon(page_url):
    """
    Finds, downloads, and caches the favicon for a given URL.

    Args:
        page_url (str): The URL of the website to get the favicon for.

    Returns:
        str: The local path to the cached favicon, or None if it fails.
    """
    if not page_url.startswith(('http://', 'https://')):
        return None

    try:
        # Create the cache directory if it doesn't exist
        os.makedirs(FAVICON_CACHE_DIR, exist_ok=True)

        domain = urlparse(page_url).scheme + "://" + urlparse(page_url).netloc

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36'
        }

        icon_url = None

        # 1. Try to find icon URL from the page's HTML
        try:
            response = requests.get(domain, headers=headers, timeout=5)
            response.raise_for_status()
            if 'text/html' in response.headers.get('Content-Type', ''):
                icon_url = _get_icon_url_from_html(response.text, domain)
        except requests.RequestException:
            pass # Could not connect or failed to get HTML, proceed to next method

        # 2. If not found in HTML, try the default /favicon.ico location
        if not icon_url:
            ico_url = urljoin(domain, '/favicon.ico')
            try:
                # Check if it exists first with a HEAD request
                head_response = requests.head(ico_url, headers=headers, timeout=3)
                if head_response.status_code == 200:
                    icon_url = ico_url
            except requests.RequestException:
                pass # favicon.ico does not exist or network error

        if not icon_url:
            return None

        # 3. Download the icon
        icon_response = requests.get(icon_url, headers=headers, timeout=5, stream=True)
        icon_response.raise_for_status()

        # Get the content and determine file extension
        icon_data = icon_response.content
        content_type = icon_response.headers.get('Content-Type', '')

        if 'svg' in content_type:
            ext = '.svg'
        elif 'png' in content_type:
            ext = '.png'
        elif 'ico' in content_type:
            ext = '.ico'
        else:
            # Fallback based on URL extension
            ext = os.path.splitext(urlparse(icon_url).path)[1]
            if not ext:
                ext = '.ico' # Default assumption

        # 4. Save to cache
        # Use a hash of the domain as the filename to avoid invalid characters
        filename = hashlib.md5(domain.encode()).hexdigest() + ext
        filepath = os.path.join(FAVICON_CACHE_DIR, filename)

        with open(filepath, 'wb') as f:
            f.write(icon_data)

        return filepath

    except requests.RequestException as e:
        print(f"Error fetching favicon for {page_url}: {e}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred while getting favicon for {page_url}: {e}")
        return None
