# Personal Notion Daily Digest - Automated Notion Database Emails

A serverless Python application deployed on AWS Lambda that transforms Notion task databases into a fully automated, custom style morning email digest. I made this with the anticipation of a heavy course workload as well as professional responsibilities; I'm someone who never has an unread email, so seeing a brief overview of my day and the days looking ahead is incredibly helpful for me.

## Features

*   **Multi-Database Aggregation:** Pulls and filters active tasks from distinct Notion databases (e.g., Professional/Personal and Coursework) via the official Notion API.
*   **Intelligent Workload Calculator:** Parses string-based time estimates (e.g., `"<30min"`, `"1-2hrs"`) into integers to calculate and display a daily total workload summary.
*   - It is very important to strictly adhere to the time estimate nomenclature for the database that has these properties for tasks, as it is somewhat hardcoded.
*   **Morning Briefing API:** Integrates with the ZenQuotes REST API to fetch a daily philosophical or motivational quote.
*   **Custom Styling:** Programmatically generates a rich HTML email; for me, it is utilizing classic serif typography, deep burgundy accents, and a parchment-style layout.
*   **Serverless Cloud Architecture:** Fully migrated to AWS Lambda and triggered daily at 6:00 AM ET via Amazon EventBridge. 

---

## Project Architecture

The codebase is strictly modular, adhering to the principle of single responsibility:

*   **`main.py`**: The central orchestrator and AWS Lambda handler. Passes data between the modules.
*   **`notion_client_wrapper.py`**: Handles secure authentication and recursive pagination for the Notion API.
*   **`transform.py`**: The translation layer. Converts complex Notion property JSONs into clean, predictable Python dictionaries, filtering out completed or distant future tasks.
*   **`morning_api.py`**: Lightweight handler for fetching external API data (ZenQuotes) using native Python libraries.
*   **`format_digest.py`**: Ingests the cleaned task dictionaries and renders the final Dark Academia HTML structure.
*   **`send_email.py`**: A generic, reusable SMTP wrapper for transmitting the HTML payload via a secure Gmail connection.

---
Created by MNaccaratto, 2026.