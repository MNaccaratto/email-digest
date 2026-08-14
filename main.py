"""
main.py
--------
Entry point. This file's ONLY job is to call the other four files in
order and pass data between them. It shouldn't contain any real logic
of its own -- if you find yourself writing an if/else or a loop here
that isn't just "call function A, then function B", that logic probably
belongs in one of the other files instead.

Run with:
    python main.py
"""

import os
import sys
from datetime import date

from dotenv import load_dotenv

from format_digest import build_digest_html
from morning_api import get_morning_briefing
from notion_client_wrapper import fetch_tasks, resolve_relation_contexts
from send_email import send_html_email
from transform import COLLEGE_PROPS, PROF_PROPS, shape_tasks

# Load variables from a local .env file into the environment. This lets
# us keep secrets out of the code entirely -- see .env.example.
load_dotenv()


def load_config() -> dict:
    """
    Pull all required settings from environment variables and fail fast
    with a clear message if anything's missing, instead of crashing
    halfway through with a confusing error.
    """
    required = [
        "NOTION_TOKEN",
        "PROF_DB_ID",
        "COLLEGE_DB_ID",
        "EMAIL_FROM",
        "EMAIL_APP_PASSWORD",
    ]
    missing = [var for var in required if not os.environ.get(var)]
    if missing:
        print(f"Missing required .env values: {', '.join(missing)}")
        print("Copy .env.example to .env and fill it in, then re-run.")
        sys.exit(1)

    return {
        "notion_token": os.environ["NOTION_TOKEN"],
        "prof_db_id": os.environ["PROF_DB_ID"],
        "college_db_id": os.environ["COLLEGE_DB_ID"],
        "email_from": os.environ["EMAIL_FROM"],
        "email_to": os.environ.get("EMAIL_TO", os.environ["EMAIL_FROM"]),
        "email_app_password": os.environ["EMAIL_APP_PASSWORD"],
        "smtp_server": os.environ.get("SMTP_SERVER", "smtp.gmail.com"),
        "smtp_port": int(os.environ.get("SMTP_PORT", "587")),
        "lookahead_days": int(os.environ.get("LOOKAHEAD_DAYS", "7")),
    }


def main():
    config = load_config()

    # --- 1. FETCH: get raw data from both Notion databases ---
    print("Fetching Professional Hub tasks...")
    prof_raw = fetch_tasks(config["prof_db_id"], config["notion_token"])

    print("Fetching College/Courses tasks...")
    college_raw = fetch_tasks(config["college_db_id"], config["notion_token"])

    # --- 2. TRANSFORM: filter + reshape into clean task dicts ---
    prof_tasks = shape_tasks(
        prof_raw,
        source_label="Professional",
        lookahead_days=config["lookahead_days"],
        props=PROF_PROPS,
    )
    college_tasks = shape_tasks(
        college_raw,
        source_label="College",
        lookahead_days=config["lookahead_days"],
        props=COLLEGE_PROPS,
    )

    print("Resolving Course relations...")
    resolve_relation_contexts(college_tasks, config["notion_token"])

    all_tasks = prof_tasks + college_tasks
    print(f"Found {len(all_tasks)} relevant tasks (due soon or overdue).")

    # --- 3. FORMAT: build the HTML digest ---
    print("Fetching morning API data...")
    briefing = get_morning_briefing()
    html_body = build_digest_html(all_tasks, briefing)

    # --- 4. SEND: email it ---
    subject = f"Daily Digest — {date.today().strftime('%m/%d')}"

    send_html_email(
        subject=subject,
        html_body=html_body,
        from_addr=config["email_from"],
        to_addr=config["email_to"],
        app_password=config["email_app_password"],
        smtp_server=config["smtp_server"],
        smtp_port=config["smtp_port"],
    )
    print(f"Digest emailed to {config['email_to']}.")


if __name__ == "__main__":
    main()
