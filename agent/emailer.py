import requests
from datetime import datetime, timezone

from agent.config import RESEND_API_KEY, EMAIL_FROM, EMAIL_TO


def _format_age(created_at: str) -> str:
    """Return a human-readable age like '2h ago' or '45m ago'."""
    created = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
    delta = datetime.now(timezone.utc) - created
    hours = int(delta.total_seconds() // 3600)
    minutes = int((delta.total_seconds() % 3600) // 60)
    if hours > 0:
        return f"{hours}h ago"
    return f"{minutes}m ago"


def send_digest(posts: list[dict]) -> str | None:
    """Send the discovery digest email via Resend.

    Each post dict should have:
        username, follower_count, post_text, post_id,
        created_at, reply_count, drafted_reply

    Returns the Resend message ID, or None on failure.
    """
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    n = len(posts)
    subject = f"X reply queue \u2014 {n} posts ({now})"

    lines = [f"{n} posts worth replying to. Links go straight to X.", "", "---", ""]

    for i, p in enumerate(posts, 1):
        age = _format_age(p["created_at"])
        lines.append(
            f'{i}. @{p["username"]} ({p["follower_count"]} followers) '
            f'| {age} | {p["reply_count"]} replies'
        )
        lines.append("")
        lines.append(f'"{p["post_text"]}"')
        lines.append("")
        lines.append("Suggested reply:")
        lines.append(f'"{p["drafted_reply"]}"')
        lines.append("")
        lines.append(f'Link: https://x.com/{p["username"]}/status/{p["post_id"]}')
        lines.append("")
        lines.append("---")
        lines.append("")

    lines.append("To pause the agent, push data/pause.flag to the x-reply-agent repo.")
    lines.append("To resume, delete the flag.")

    body = "\n".join(lines)

    resp = requests.post(
        "https://api.resend.com/emails",
        headers={"Authorization": f"Bearer {RESEND_API_KEY}"},
        json={
            "from": EMAIL_FROM,
            "to": [EMAIL_TO],
            "subject": subject,
            "text": body,
        },
    )
    resp.raise_for_status()
    return resp.json().get("id")


def send_low_signal_email() -> str | None:
    """Send a 'low signal' notification when fewer than MIN_GOOD_POSTS found."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    resp = requests.post(
        "https://api.resend.com/emails",
        headers={"Authorization": f"Bearer {RESEND_API_KEY}"},
        json={
            "from": EMAIL_FROM,
            "to": [EMAIL_TO],
            "subject": f"X reply queue \u2014 low signal run ({now})",
            "text": (
                "Low signal run. Fewer than 3 good posts found this cycle.\n\n"
                "The agent will try again in 2 hours."
            ),
        },
    )
    resp.raise_for_status()
    return resp.json().get("id")
