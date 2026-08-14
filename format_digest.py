"""
format_digest.py
------------------
Responsibility: turn a list of clean task dicts (from transform.py) into
an HTML string ready to email.

This file only cares about PRESENTATION -- it doesn't fetch anything,
doesn't filter anything, doesn't send anything. If you later wanted a
Slack-formatted digest instead of email, you'd add a new file here
(format_slack.py) rather than touching this one.
"""

from datetime import date

# Maps the internal "source" tag (set in main.py when calling shape_tasks)
# to the friendly header shown in the email. Order here also controls the
# order sources appear in the digest -- Professional Hub first, then
# Coursework, then anything else (future sources) alphabetically after.
SOURCE_LABELS = {
    "Professional": "Professional Hub",
    "College": "Coursework",
}
SOURCE_ORDER = ["Professional", "College"]


def _render_task_row(task: dict, today: date) -> str:
    """Render one <li> for a single task, with its metadata line."""
    due_label = "Today" if task["due"] == today else task["due"].strftime("%a %m/%d")

    meta_pieces = [due_label]
    if task["task_type"]:
        meta_pieces.append(task["task_type"])
    if task["estimated_time"]:
        meta_pieces.append(task["estimated_time"])
    meta_line = " · ".join(meta_pieces)

    # notes_links might be a real URL (Professional's "Link" property)
    # or plain text (College's "Notes" property) -- only render it as
    # a clickable link if it actually looks like one.
    note = task["notes_links"]
    if note.startswith("http://") or note.startswith("https://"):
        link_html = f' — <a href="{note}">link</a>'
    elif note:
        link_html = f" — {note}"
    else:
        link_html = ""

    return (
        f'<li style="margin-bottom:6px;">'
        f'<strong>{task["title"]}</strong>{link_html}<br>'
        f'<span style="color:#666;font-size:13px;">{meta_line}</span>'
        f"</li>"
    )


def _render_source_section(source_tasks: list[dict], today: date) -> list[str]:
    """
    Render the Overdue + by-Context sub-sections for ONE source's tasks
    (i.e. everything already filtered down to just Professional, or just
    College). Returns a list of HTML fragment strings.
    """
    overdue = [t for t in source_tasks if t["overdue"]]
    upcoming = sorted(
        (t for t in source_tasks if not t["overdue"]),
        key=lambda t: t["due"],
    )

    by_context: dict[str, list[dict]] = {}
    for task in upcoming:
        by_context.setdefault(task["context"], []).append(task)

    parts = []

    if overdue:
        parts.append(
            '<h4 style="font-family:sans-serif;color:#c0392b;margin-bottom:4px;">Overdue</h4>'
            '<ul style="font-family:sans-serif;padding-left:18px;margin-top:0;">'
        )
        parts.extend(_render_task_row(t, today) for t in overdue)
        parts.append("</ul>")

    for context, tasks in by_context.items():
        parts.append(
            f'<h4 style="font-family:sans-serif;margin-bottom:4px;">{context}</h4>'
            '<ul style="font-family:sans-serif;padding-left:18px;margin-top:0;">'
        )
        parts.extend(_render_task_row(t, today) for t in tasks)
        parts.append("</ul>")

    return parts


def build_digest_html(all_tasks: list[dict]) -> str:
    """
    Build an HTML digest string, structured as:
        Professional Hub
            Overdue (if any)
            <Context group>
            <Context group>
        Coursework
            Overdue (if any)
            <Course name group>
            <Course name group>

    Sources with no tasks at all are skipped entirely, so you don't see
    an empty "Coursework" header on a day nothing's due there.

    Parameters:
        all_tasks: combined list of clean task dicts from both databases

    Returns:
        A single HTML string, ready to hand to send_email.py
    """
    today = date.today()

    # Group all tasks by their source ("Professional" / "College") first.
    by_source: dict[str, list[dict]] = {}
    for task in all_tasks:
        by_source.setdefault(task["source"], []).append(task)

    html_parts = [
        f'<h2 style="font-family:sans-serif;">Daily Digest — {today.strftime("%A, %B %d")}</h2>'
    ]

    if not all_tasks:
        html_parts.append(
            '<p style="font-family:sans-serif;">Nothing due today or overdue. 🎉</p>'
        )
        return "\n".join(html_parts)

    # Walk sources in our preferred order first, then any unrecognized
    # source labels afterward (so a future third database still shows up
    # instead of silently vanishing).
    ordered_sources = SOURCE_ORDER + sorted(
        s for s in by_source if s not in SOURCE_ORDER
    )

    for source in ordered_sources:
        source_tasks = by_source.get(source)
        if not source_tasks:
            continue  # nothing due for this source today -- skip its header entirely

        label = SOURCE_LABELS.get(source, source)
        html_parts.append(
            f'<h3 style="font-family:sans-serif;border-bottom:1px solid #ddd;padding-bottom:4px;">{label}</h3>'
        )
        html_parts.extend(_render_source_section(source_tasks, today))

    return "\n".join(html_parts)
