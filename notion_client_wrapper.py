"""
notion_client_wrapper.py
-------------------------
Responsibility: talk to the Notion API. Nothing else.

This file knows HOW to authenticate with Notion and HOW to page through
a database's results. It does NOT know what a "task" means, does NOT
filter by due date, and does NOT care about Context/Status/etc.

Why keep it this dumb on purpose? If you ever reuse this fetch logic for
something else (a stats dashboard, a backup script), you don't have to
untangle "digest filtering logic" out of "fetching logic" first. Fetching
and interpreting are two different jobs.
"""

from notion_client import Client


def fetch_tasks(database_id: str, token: str) -> list[dict]:
    """
    Fetch ALL pages (rows) from a Notion database, unfiltered and unshaped.

    Parameters:
        database_id: the 32-character ID of the Notion database
        token: your Notion integration's secret token

    Returns:
        A list of raw Notion "page" dicts. Each dict is Notion's own JSON
        structure for one row -- properties, ids, timestamps, etc. We do
        NOT simplify this here; transform.py's job is to make sense of it.
    """
    # The Client object handles auth headers + HTTP requests to Notion's API
    # for us. We create a fresh one per call for simplicity -- for a script
    # that runs once a day, there's no real cost to this.
    client = Client(auth=token)

    # As of Notion's September 2025 API update, a database can contain
    # multiple "data sources" (think of it like a database having several
    # underlying tables). The old one-step `databases.query()` is
    # deprecated -- we now have to (1) look up the database's data
    # source ID, then (2) query THAT. For a normal single-table database
    # like yours, there's just one data source, so we grab the first one.
    db_info = client.databases.retrieve(database_id)
    data_source_id = db_info["data_sources"][0]["id"]

    all_pages = []
    cursor = None  # Notion paginates results; None means "start from the top"

    # Notion returns results in pages of up to 100 rows at a time.
    # has_more / next_cursor tell us whether to keep asking for more.
    while True:
        # Notion's API rejects an explicit "start_cursor": null on the first
        # request, so we only pass it once we actually have a cursor value.
        query_kwargs = {"data_source_id": data_source_id}
        if cursor:
            query_kwargs["start_cursor"] = cursor

        response = client.data_sources.query(**query_kwargs)

        all_pages.extend(response["results"])

        if not response.get("has_more"):
            break  # we've collected every row; stop looping

        cursor = response.get("next_cursor")

    return all_pages


def _extract_title(page: dict) -> str:
    """
    Find whichever property on a page has type "title" (every Notion page
    has exactly one) and return its plain text. Used when resolving a
    relation -- we've fetched a related page and just want its name.
    """
    for prop in page["properties"].values():
        if prop["type"] == "title":
            return "".join(fragment["plain_text"] for fragment in prop["title"])
    return "Unknown"


def resolve_relation_contexts(tasks: list[dict], token: str) -> None:
    """
    Fill in the real "context" value for any task whose context came from
    a relation property (transform.py leaves these as "Uncategorized"
    with a "context_relation_id" set as a placeholder).

    Mutates `tasks` in place. Uses a local cache so that if 10 assignments
    all point to the same course, we only fetch that course page once,
    not 10 times -- Notion's API rate limit is ~3 requests/second, so this
    matters once you have more than a handful of tasks.

    Parameters:
        tasks: the list of task dicts produced by transform.shape_tasks()
        token: your Notion integration token
    """
    cache: dict[str, str] = {}
    client = Client(auth=token)

    for task in tasks:
        related_id = task.get("context_relation_id")
        if not related_id:
            continue  # this task's context wasn't a relation; nothing to do

        if related_id not in cache:
            related_page = client.pages.retrieve(related_id)
            cache[related_id] = _extract_title(related_page)

        task["context"] = cache[related_id]
