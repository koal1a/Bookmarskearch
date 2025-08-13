
import webbrowser
from PyQt5.QtCore import Qt

def _open_urls_for_query(state, query):
    """Helper function to open all active URLs for a given query."""
    for url, data in state.saved_urls.items():
        if data.get("active", True):
            full_url = f"{url}{query}"
            webbrowser.open(full_url)

def search(state, query):
    if query:
        _open_urls_for_query(state, query)
        save_search_query(state, query)

def search_from_history(state, query):
    _open_urls_for_query(state, query)

def search2(state, query):
    if query:
        _open_urls_for_query(state, query)

def save_search_query(state, query, note=""):
    existing_query = next((item for item in state.search_history if item["query"] == query), None)
    if existing_query:
        existing_query["note"] = note
    else:
        state.search_history.append({"query": query, "note": note, "tags": [], "group": "기본"})
    state.save_search_history()

def save_url(state, url, name=None, note='', group='기본'):
    if url and url not in state.saved_urls:
        if not name:
            try:
                if url.startswith(('http://', 'https://')):
                    domain = url.split("//")[1].split("/")[0]
                else:
                    domain = url.split("/")[0]
                if domain.startswith('www.'):
                    domain = domain[4:]
                name = domain
            except:
                name = url.split("//")[-1].split("/")[0] if "//" in url else url
        state.saved_urls[url] = {"name": name, "active": True, "note": note, "group": group, "favicon_path": None}
        state.save_saved_urls()

def delete_history_item(state, query):
    state.search_history = [record for record in state.search_history if record["query"] != query]
    state.save_search_history()

def delete_url_item(state, url):
    if url in state.saved_urls:
        del state.saved_urls[url]
        state.save_saved_urls()

def update_note_for_query(state, query, note):
    for item in state.search_history:
        if item["query"] == query:
            item["note"] = note
            state.save_search_history()
            break

def uncheck_all_urls(state):
    for url in state.saved_urls:
        state.saved_urls[url]["active"] = False
    state.save_saved_urls()

def toggle_url_state(state, url, is_checked):
    if url in state.saved_urls:
        state.saved_urls[url]["active"] = is_checked
        state.save_saved_urls()

def ensure_tags_in_history(state):
    changed = False
    for item in state.search_history:
        if 'tags' not in item:
            item['tags'] = []
            changed = True
    if changed:
        state.save_search_history()

def search2_and_record(state, query):
    if query:
        search2(state, query)
        if query not in state.left_search_history:
            state.left_search_history.append(query)
            state.save_left_history()

def do_search2_fields(state, q1, q2):
    query = q1 + q2
    if query:
        search2(state, query)
        if query not in state.left_search_history:
            state.left_search_history.append(query)
            state.save_left_history()
