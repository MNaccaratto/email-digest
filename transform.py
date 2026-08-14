"""
transform.py
-------------
Responsibility: turn raw, messy Notion page data into clean, simple task
dicts that the rest of the program can actually work with.

This is the "translation layer" between Notion's JSON structure (which
varies by property type -- title vs select vs date vs rich_text all look
different) and a plain, predictable shape like:

    {"title": "Grade Lab 3", "context": "TA", "due": date(2026, 8, 20), ...}

Everything downstream (formatting, emailing) only ever touches this clean
shape -- it never has to know Notion's property-type quirks.
"""

from datetime import date, datetime, timedelta

# Property name mappings. These MUST match your Notion database's actual
# column names exactly (case-sensitive). Your two databases use genuinely
# different schemas, so each gets its own dict rather than sharing one.

PROF_PROPS = {
    "due_date": "Due Date",
    "status": "Status",
    "context": "Organization",  # e.g. "COMS", "TA"
    "task_type": "Type",
    "estimated_time": "Estimated Time",
    "notes_links": "Link",  # a real URL property here
    "title": "Name",
    "done_values": ["Done"],
}

COLLEGE_PROPS = {
    "due_date": "Due Date",
    "status": "Status",
    "context": "Course",  # a RELATION property -- see shape_tasks()
    "task_type": "Type",
    "estimated_time": "Estimated Time",  # doesn't exist in this DB; will just be blank
    "notes_links": "Notes",  # plain text, not necessarily a URL
    "title": "Title",
    "done_values": ["Complete"],
}


def _get_text(page: dict, prop_name: str, default: str = "") -> str:
    """
    Pull a human-readable string out of a Notion property, regardless of
    whether it's a title, rich_text, select, or url property under the hood.
    Notion's JSON shape differs per property type, so we branch on "type".
    """
    prop = page["properties"].get(prop_name)
    if not prop:
        return default

    prop_type = prop["type"]

    if prop_type == "title":
        # Notion titles are a LIST of text fragments (in case of mixed
        # formatting), so we join them into one plain string.
        return "".join(fragment["plain_text"] for fragment in prop["title"]) or default

    if prop_type == "rich_text":
        return (
            "".join(fragment["plain_text"] for fragment in prop["rich_text"]) or default
        )

    if prop_type == "select":
        return prop["select"]["name"] if prop["select"] else default

    if prop_type == "url":
        return prop["url"] or default

    return default


def _get_date(page: dict, prop_name: str) -> date | None:
    """Pull a plain Python date out of a Notion date property, or None."""
    prop = page["properties"].get(prop_name)
    if not prop or prop["type"] != "date" or not prop["date"]:
        return None

    raw = prop["date"]["start"]  # e.g. "2026-08-20" or "2026-08-20T09:00:00.000-04:00"
    try:
        # fromisoformat handles both date-only and full datetime strings;
        # we only care about the date portion for the digest.
        return datetime.fromisoformat(raw.replace("Z", "+00:00")).date()
    except ValueError:
        return None


def shape_tasks(
    raw_pages: list[dict],
    source_label: str,
    lookahead_days: int = 2,
    props: dict = PROF_PROPS,
) -> list[dict]:
    """
    Filter + reshape raw Notion pages into clean task dicts.

    Filtering rules:
        - Skip anything whose Status is in props["done_values"]
        - Skip anything with no due date at all (nothing urgent to report)
        - Skip anything due further out than `lookahead_days` from today
        - Keep everything overdue (any date before today), no matter how
          far in the past -- you should always be told about overdue work

    A note on "context": most databases store it as a simple select
    property, so we can read it directly as text. But College's "Course"
    property is a RELATION (a link to a row in a separate Courses
    database) -- Notion's API only gives us the related page's ID here,
    not its name. So when we detect a relation property, we store the
    raw page ID in "context_relation_id" and leave "context" as a
    placeholder. notion_client_wrapper.resolve_relation_contexts() does
    the actual name lookup afterward -- see main.py for how they're
    wired together. This keeps this file free of any network calls.

    Parameters:
        raw_pages: the list returned by notion_client_wrapper.fetch_tasks()
        source_label: a tag like "Professional" or "College" so the digest
                       can show which database a task came from
        lookahead_days: how many days ahead (besides today) to include
        props: property-name mapping, in case a database's column names differ

    Returns:
        A list of clean dicts, one per task that should appear in the digest.
    """
    today = date.today()
    horizon = today + timedelta(days=lookahead_days)

    tasks = []
    for page in raw_pages:
        status = _get_text(page, props["status"])
        if status in props["done_values"]:
            continue  # already done, don't clutter the digest

        due = _get_date(page, props["due_date"])
        if due is None:
            continue  # no due date means nothing time-sensitive to report
        if due > horizon:
            continue  # too far in the future, not relevant yet

        # Detect whether "context" is a relation (needs a follow-up API
        # call to resolve) or a plain select/text property (read directly).
        context_prop = page["properties"].get(props["context"])
        context_relation_id = None
        if context_prop and context_prop["type"] == "relation":
            related = context_prop["relation"]
            context_relation_id = related[0]["id"] if related else None
            context = "Uncategorized"  # placeholder; resolved later if possible
        else:
            context = _get_text(page, props["context"], default="Uncategorized")

        tasks.append(
            {
                "title": _get_text(page, props["title"], default="(untitled)"),
                "context": context,
                "context_relation_id": context_relation_id,
                "task_type": _get_text(page, props["task_type"]),
                "due": due,
                "estimated_time": _get_text(page, props["estimated_time"]),
                "notes_links": _get_text(page, props["notes_links"]),
                "overdue": due < today,
                "source": source_label,
            }
        )

    return tasks
