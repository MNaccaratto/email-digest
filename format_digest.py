"""
format_digest.py
------------------
Responsibility: turn a list of clean task dicts into an HTML string ready to email.
"""

from datetime import date
import re

SOURCE_LABELS = {
    "Professional": "Professional Hub",
    "College": "Coursework",
}
SOURCE_ORDER = ["Professional", "College"]

# Dark Academia Color Palette
BG_COLOR = "#FDFBF7"
TEXT_MAIN = "#2C2C2C"
TEXT_MUTED = "#555555"
ACCENT_DARK_RED = "#722F37"
BORDER_COLOR = "#E6DCD3"


def _parse_minutes(time_str: str) -> int:
    """Converts strings like '<30min', '1-2hrs', or '1 hr' into an integer of minutes."""
    if not time_str:
        return 0
    t = time_str.lower()
    nums = re.findall(r"\d+", t)
    if not nums:
        return 0

    # If it's a range (e.g. 1-2), take the average
    if "-" in t and len(nums) >= 2:
        val = (float(nums[0]) + float(nums[1])) / 2
    else:
        val = float(nums[0])

    # Convert hours to minutes
    if "hr" in t or "hour" in t:
        return int(val * 60)
    return int(val)


def _format_minutes(mins: int) -> str:
    """Formats raw minutes back into a clean 'X hr Y min' string."""
    h = mins // 60
    m = mins % 60
    if h > 0 and m > 0:
        return f"{h} hr {m} min"
    elif h > 0:
        return f"{h} hr"
    return f"{m} min"


def _render_task_row(task: dict, today: date) -> str:
    due_label = "Today" if task["due"] == today else task["due"].strftime("%a %m/%d")
    meta_pieces = [due_label]
    if task["task_type"]:
        meta_pieces.append(task["task_type"])
    if task["estimated_time"]:
        meta_pieces.append(task["estimated_time"])
    meta_line = " · ".join(meta_pieces)

    note = task["notes_links"]
    if note.startswith("http://") or note.startswith("https://"):
        link_html = f' — <a href="{note}" style="color:{ACCENT_DARK_RED}; text-decoration:none; border-bottom:1px solid {ACCENT_DARK_RED};">link</a>'
    elif note:
        link_html = f' — <span style="color:{TEXT_MUTED};">{note}</span>'
    else:
        link_html = ""

    return (
        f'<li style="margin-bottom:10px; line-height:1.4;">'
        f'<strong style="color:{TEXT_MAIN}; font-size:15px;">{task["title"]}</strong>{link_html}<br>'
        f'<span style="color:{TEXT_MUTED}; font-size:13px; font-style:italic;">{meta_line}</span>'
        f"</li>"
    )


def _render_source_section(source_tasks: list[dict], today: date) -> list[str]:
    overdue = [t for t in source_tasks if t["overdue"]]
    today_tasks = [t for t in source_tasks if not t["overdue"] and t["due"] == today]
    future_tasks = sorted(
        (t for t in source_tasks if not t["overdue"] and t["due"] > today),
        key=lambda t: t["due"],
    )

    parts = []

    if overdue:
        parts.append(
            f'<h4 style="font-family: Georgia, serif; color: #990000; margin-bottom: 6px; margin-top: 16px; font-size: 16px; text-transform: uppercase; letter-spacing: 0.5px;">⚠ Overdue</h4>'
            f'<ul style="font-family: Georgia, serif; padding-left: 20px; margin-top: 0; list-style-type: square;">'
        )
        parts.extend(_render_task_row(t, today) for t in overdue)
        parts.append("</ul>")

    if today_tasks:
        # Calculate daily workload
        total_mins = sum(
            _parse_minutes(t.get("estimated_time", "")) for t in today_tasks
        )
        workload_html = ""
        if total_mins > 0:
            workload_html = f'<span style="color: {TEXT_MUTED}; font-size: 13px; font-weight: normal; font-style: italic; margin-left: 10px;">(~{_format_minutes(total_mins)} total)</span>'

        parts.append(
            f'<h4 style="font-family: Georgia, serif; color: {ACCENT_DARK_RED}; margin-bottom: 6px; margin-top: 20px; font-size: 16px; border-bottom: 1px solid {BORDER_COLOR}; padding-bottom: 4px;">Today{workload_html}</h4>'
        )
        by_context_today: dict[str, list[dict]] = {}
        for task in today_tasks:
            by_context_today.setdefault(task["context"], []).append(task)

        for context, tasks in by_context_today.items():
            parts.append(
                f'<h5 style="font-family: Georgia, serif; margin-bottom: 4px; margin-top: 12px; color: {TEXT_MAIN}; font-size: 14px; font-weight: normal; font-style: italic;">{context}</h5>'
                f'<ul style="font-family: Georgia, serif; padding-left: 20px; margin-top: 0; color: {ACCENT_DARK_RED};">'
            )
            parts.extend(_render_task_row(t, today) for t in tasks)
            parts.append("</ul>")

    if future_tasks:
        parts.append(
            f'<h4 style="font-family: Georgia, serif; color: {TEXT_MUTED}; margin-bottom: 6px; margin-top: 24px; font-size: 15px; border-bottom: 1px solid {BORDER_COLOR}; padding-bottom: 4px;">Looking Ahead</h4>'
        )
        by_context_future: dict[str, list[dict]] = {}
        for task in future_tasks:
            by_context_future.setdefault(task["context"], []).append(task)

        for context, tasks in by_context_future.items():
            parts.append(
                f'<h5 style="font-family: Georgia, serif; margin-bottom: 4px; margin-top: 12px; color: {TEXT_MAIN}; font-size: 14px; font-weight: normal; font-style: italic;">{context}</h5>'
                f'<ul style="font-family: Georgia, serif; padding-left: 20px; margin-top: 0; color: {TEXT_MUTED};">'
            )
            parts.extend(_render_task_row(t, today) for t in tasks)
            parts.append("</ul>")

    return parts


def build_digest_html(all_tasks: list[dict], briefing: dict = None) -> str:
    today = date.today()
    briefing = briefing or {}

    by_source: dict[str, list[dict]] = {}
    for task in all_tasks:
        by_source.setdefault(task["source"], []).append(task)

    html_parts = [
        f'<div style="background-color: {BG_COLOR}; padding: 30px; border-radius: 8px; max-width: 600px; margin: 0 auto; border: 1px solid {BORDER_COLOR};">'
        f'<h2 style="font-family: Georgia, serif; color: {ACCENT_DARK_RED}; font-weight: normal; border-bottom: 2px solid {ACCENT_DARK_RED}; padding-bottom: 10px; margin-top: 0; font-size: 24px;">Daily Digest <span style="color: {TEXT_MUTED}; font-size: 16px; float: right; margin-top: 6px;">{today.strftime("%A, %B %d")}</span></h2>'
    ]

    # Inject the Morning Briefing (Weather & Quote)
    if briefing.get("weather") or briefing.get("quote"):
        html_parts.append(
            f'<div style="margin-top: 20px; margin-bottom: 20px; padding: 15px; background-color: #F8F5F0; border-radius: 6px; border: 1px solid {BORDER_COLOR};">'
        )
        if briefing.get("weather"):
            html_parts.append(
                f'<div style="font-family: Georgia, serif; font-size: 14px; color: {TEXT_MAIN}; margin-bottom: 10px;"><strong>New York:</strong> {briefing["weather"]}</div>'
            )
        if briefing.get("quote"):
            html_parts.append(
                f'<div style="font-family: Georgia, serif; font-size: 14px; color: {TEXT_MUTED}; font-style: italic; line-height: 1.5;">"{briefing["quote"]}"<br><span style="color: {TEXT_MAIN};">&mdash; {briefing["author"]}</span></div>'
            )
        html_parts.append("</div>")

    if not all_tasks:
        html_parts.append(
            f'<p style="font-family: Georgia, serif; color: {TEXT_MUTED}; font-style: italic; text-align: center; margin-top: 40px; margin-bottom: 40px;">Nothing due today or overdue. A quiet day awaits.</p>'
        )
        html_parts.append("</div>")
        return "\n".join(html_parts)

    ordered_sources = SOURCE_ORDER + sorted(
        s for s in by_source if s not in SOURCE_ORDER
    )

    for source in ordered_sources:
        source_tasks = by_source.get(source)
        if not source_tasks:
            continue

        label = SOURCE_LABELS.get(source, source)
        html_parts.append(
            f'<h3 style="font-family: Georgia, serif; color: {TEXT_MAIN}; text-transform: uppercase; letter-spacing: 2px; font-size: 14px; margin-top: 30px; margin-bottom: 0;">{label}</h3>'
        )
        html_parts.extend(_render_source_section(source_tasks, today))

    html_parts.append("</div>")

    return "\n".join(html_parts)
