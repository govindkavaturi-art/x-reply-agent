"""Main discovery flow: search X, filter, rank, draft replies, email digest."""

import re
import sys
import time
from datetime import datetime, timedelta, timezone

from agent.config import (
    BRAND_EXCLUSIONS,
    DISCOVERY_CUE_TASK,
    MAX_CANDIDATES_TO_SCORE,
    MAX_REPLY_COUNT,
    MIN_ACCOUNT_AGE_DAYS,
    MIN_GOOD_POSTS,
    SEARCH_QUERIES,
    SEARCH_WINDOW_HOURS,
    TOP_N_POSTS,
)
from agent.cueapi import claim_cue, report_outcome
from agent.drafter import draft_reply, score_post_relevance
from agent.emailer import send_digest, send_low_signal_email
from agent.state import (
    add_surfaced,
    load_cooldown,
    load_surfaced,
    pause_flag_exists,
    prune_expired_cooldown,
    save_cooldown,
    save_surfaced,
)
from agent.x_client import search_recent


def run():
    start_time_ms = time.time()

    # Step 1: Check pause state
    if pause_flag_exists():
        print("Pause flag detected. Exiting.")
        try:
            cue = claim_cue(DISCOVERY_CUE_TASK)
            if cue:
                report_outcome(cue["execution_id"], success=True,
                               metadata={"status": "paused"})
        except Exception:
            pass
        return

    # Step 2: Load state
    cooldown = prune_expired_cooldown(load_cooldown())
    save_cooldown(cooldown)
    surfaced = load_surfaced()
    surfaced_set = set(surfaced)
    cooldown_usernames = set(cooldown.keys())

    # Step 3: Claim cue from CueAPI
    execution_id = None
    try:
        cue = claim_cue(DISCOVERY_CUE_TASK)
        if cue:
            execution_id = cue["execution_id"]
            print(f"Claimed cue: {execution_id}")
        else:
            print("No cue to claim. Running without CueAPI tracking.")
    except Exception as e:
        print(f"CueAPI claim failed (continuing anyway): {e}")

    # Step 4: Search X API
    start_time = (
        datetime.now(timezone.utc) - timedelta(hours=SEARCH_WINDOW_HOURS)
    ).strftime("%Y-%m-%dT%H:%M:%SZ")

    all_posts = []
    users_by_id = {}

    for query in SEARCH_QUERIES:
        try:
            data = search_recent(query, start_time, max_results=30)
        except Exception as e:
            print(f"Search query failed: {query[:50]}... -> {e}")
            continue

        tweets = data.get("data", [])
        includes = data.get("includes", {})
        for user in includes.get("users", []):
            users_by_id[user["id"]] = user

        for tweet in tweets:
            all_posts.append(tweet)

    posts_searched = len(all_posts)
    print(f"Raw posts fetched: {posts_searched}")

    # Step 5: Basic filter pass
    now = datetime.now(timezone.utc)
    min_account_date = now - timedelta(days=MIN_ACCOUNT_AGE_DAYS)
    seen_ids = set()
    filtered = []

    for post in all_posts:
        post_id = post["id"]
        if post_id in seen_ids:
            continue
        seen_ids.add(post_id)

        # Language filter
        if post.get("lang", "en") != "en":
            continue

        # Freshness filter
        created_at = post.get("created_at", "")
        if created_at:
            created = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            if (now - created).total_seconds() > SEARCH_WINDOW_HOURS * 3600:
                continue

        # Reply count filter
        metrics = post.get("public_metrics", {})
        if metrics.get("reply_count", 0) > MAX_REPLY_COUNT:
            continue

        # Already surfaced
        if post_id in surfaced_set:
            continue

        # Author checks
        author_id = post.get("author_id", "")
        user = users_by_id.get(author_id, {})
        username = user.get("username", "")

        # Brand exclusion
        if username in BRAND_EXCLUSIONS:
            continue

        # Cooldown check
        if username.lower() in {u.lower() for u in cooldown_usernames}:
            continue

        # Account age check
        user_created = user.get("created_at", "")
        if user_created:
            user_date = datetime.fromisoformat(user_created.replace("Z", "+00:00"))
            if user_date > min_account_date:
                continue

        filtered.append({
            "post_id": post_id,
            "post_text": post.get("text", ""),
            "created_at": created_at,
            "reply_count": metrics.get("reply_count", 0),
            "author_id": author_id,
            "username": username,
            "follower_count": user.get("public_metrics", {}).get("followers_count", 0),
            "_user_data": user,
        })

    posts_after_basic_filter = len(filtered)
    print(f"Posts after basic filter: {posts_after_basic_filter}")

    # Step 6: Cap candidates by freshness for LLM scoring
    filtered.sort(
        key=lambda p: p["created_at"],
        reverse=True,
    )
    candidates = filtered[:MAX_CANDIDATES_TO_SCORE]
    posts_scored = len(candidates)
    print(f"Candidates to score: {posts_scored}")

    # Step 7: LLM relevance scoring via Haiku
    passed = []
    for post in candidates:
        result = score_post_relevance(post, post.get("_user_data", {}))
        verdict = result.get("verdict", "REJECT")
        total = result.get("total", 0)
        print(
            f"  @{post['username']}: {verdict} (score {total}/50) "
            f"- {result.get('reason', '')}"
        )
        if verdict == "PASS":
            post["relevance_score"] = total
            post["suggested_angle"] = result.get("suggested_angle", "")
            passed.append(post)

    posts_passed = len(passed)
    print(f"Posts passed relevance scoring: {posts_passed}")

    # Step 8: Sort by relevance score, take top N
    passed.sort(key=lambda p: p.get("relevance_score", 0), reverse=True)
    top_posts = passed[:TOP_N_POSTS]

    print(f"Top posts selected: {len(top_posts)}")

    # Check minimum threshold
    if len(top_posts) < MIN_GOOD_POSTS:
        print("Low signal run. Sending low-signal email.")
        email_id = None
        try:
            email_id = send_low_signal_email()
        except Exception as e:
            print(f"Failed to send low-signal email: {e}")

        if execution_id:
            try:
                report_outcome(execution_id, success=True, metadata={
                    "status": "low_signal",
                    "posts_searched": posts_searched,
                    "posts_after_basic_filter": posts_after_basic_filter,
                    "posts_scored": posts_scored,
                    "posts_passed": posts_passed,
                    "posts_surfaced": len(top_posts),
                    "email_message_id": email_id,
                })
            except Exception as e:
                print(f"CueAPI report failed: {e}")
        return

    # Step 9: Draft replies (Opus 4.6)
    drafts_ok = []
    for post in top_posts:
        try:
            reply = draft_reply(post["username"], post["post_text"])
            if reply == "SKIP":
                print(f"Drafter returned SKIP for @{post['username']}")
                post["drafted_reply"] = "[SKIP - no good reply found]"
            else:
                post["drafted_reply"] = reply
                drafts_ok.append(post)
            print(f"Drafted reply for @{post['username']}")
        except Exception as e:
            print(f"Failed to draft reply for @{post['username']}: {e}")
            post["drafted_reply"] = "[Draft failed]"

    # Use all top_posts for the email (including failed drafts)
    email_posts = top_posts

    # Step 10: Send email
    email_id = None
    try:
        email_id = send_digest(email_posts)
        print(f"Email sent: {email_id}")
    except Exception as e:
        print(f"Failed to send email: {e}")
        if execution_id:
            report_outcome(execution_id, success=False, error=f"Email send failed: {e}")
        sys.exit(1)

    # Step 11: Update state
    new_ids = [p["post_id"] for p in top_posts]
    surfaced = add_surfaced(surfaced, new_ids)
    save_surfaced(surfaced)
    print(f"State updated. Total surfaced: {len(surfaced)}")

    # Step 12: Report success to CueAPI
    duration_ms = int((time.time() - start_time_ms) * 1000)
    if execution_id:
        try:
            report_outcome(execution_id, success=True, metadata={
                "posts_searched": posts_searched,
                "posts_after_basic_filter": posts_after_basic_filter,
                "posts_scored": posts_scored,
                "posts_passed": posts_passed,
                "posts_surfaced": len(top_posts),
                "email_message_id": email_id,
                "duration_ms": duration_ms,
            })
            print("CueAPI outcome reported.")
        except Exception as e:
            print(f"CueAPI report failed: {e}")


if __name__ == "__main__":
    run()
