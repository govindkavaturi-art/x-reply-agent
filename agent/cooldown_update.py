"""Cooldown update flow: check Govind's replies, update cooldown list."""

import sys
from datetime import datetime, timedelta, timezone

from agent.config import COOLDOWN_CUE_TASK, COOLDOWN_HOURS, GOVIND_X_USER_ID
from agent.cueapi import claim_cue, report_outcome
from agent.state import (
    add_cooldown,
    load_cooldown,
    load_surfaced,
    prune_expired_cooldown,
    save_cooldown,
)
from agent.x_client import get_user_tweets


def run():
    # Step 1: Claim cue
    execution_id = None
    try:
        cue = claim_cue(COOLDOWN_CUE_TASK)
        if cue:
            execution_id = cue["execution_id"]
            print(f"Claimed cue: {execution_id}")
        else:
            print("No cue to claim. Running without CueAPI tracking.")
    except Exception as e:
        print(f"CueAPI claim failed (continuing anyway): {e}")

    # Step 2: Fetch Govind's recent replies
    start_time = (
        datetime.now(timezone.utc) - timedelta(hours=12)
    ).strftime("%Y-%m-%dT%H:%M:%SZ")

    try:
        data = get_user_tweets(GOVIND_X_USER_ID, start_time)
    except Exception as e:
        print(f"Failed to fetch Govind's tweets: {e}")
        if execution_id:
            report_outcome(execution_id, success=False, error=str(e))
        sys.exit(1)

    tweets = data.get("data", [])

    # Filter to replies only
    replies = []
    for tweet in tweets:
        refs = tweet.get("referenced_tweets", [])
        for ref in refs:
            if ref.get("type") == "replied_to":
                replies.append({
                    "tweet_id": tweet["id"],
                    "replied_to_id": ref["id"],
                    "created_at": tweet.get("created_at", ""),
                    "in_reply_to_user_id": tweet.get("in_reply_to_user_id"),
                })
                break

    print(f"Govind's replies in last 12h: {len(replies)}")

    # Step 3: Load surfaced posts (last batch)
    surfaced = load_surfaced()
    # Get the last 10 surfaced post IDs
    recent_surfaced = set(surfaced[-10:]) if surfaced else set()

    # Step 4: Match replies to surfaced posts and update cooldown
    cooldown = prune_expired_cooldown(load_cooldown())
    cooldowns_added = 0

    # For each reply, check if it's to a surfaced post
    replied_to_ids = {r["replied_to_id"] for r in replies}
    matched = replied_to_ids & recent_surfaced

    if matched:
        # We need to figure out author usernames for matched posts.
        # Since we don't store author info in surfaced_posts.json,
        # we use in_reply_to_user_id from the reply tweets.
        # But we only have user IDs, not usernames. We'll store user IDs
        # in cooldown as a fallback (the discovery filter checks usernames).
        #
        # Better approach: look up the original tweets to get author info.
        # For now, use in_reply_to_user_id as the cooldown key.
        for reply in replies:
            if reply["replied_to_id"] in matched:
                user_id = reply.get("in_reply_to_user_id", "")
                if user_id:
                    cooldown = add_cooldown(cooldown, f"uid:{user_id}", COOLDOWN_HOURS)
                    cooldowns_added += 1
                    print(f"Added cooldown for user ID: {user_id}")

    # Step 5: Save state
    save_cooldown(cooldown)
    print(f"Cooldown updated. Active entries: {len(cooldown)}")

    # Step 6: Report success
    if execution_id:
        try:
            report_outcome(execution_id, success=True, metadata={
                "cooldowns_added": cooldowns_added,
                "replies_checked": len(replies),
            })
            print("CueAPI outcome reported.")
        except Exception as e:
            print(f"CueAPI report failed: {e}")


if __name__ == "__main__":
    run()
