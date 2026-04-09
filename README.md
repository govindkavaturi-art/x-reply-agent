# x-reply-agent

Automatically discovers fresh X (Twitter) posts where Govind should reply, drafts replies in his voice, and emails them every 2 hours. Draft-only. Never auto-posts.

## Architecture

```
+----------------+       +------------------+       +-----------+
|  GitHub Actions | ----> |  Python Worker   | ----> |  Resend   |
|  (cron schedule)|       |  (discovery.py)  |       |  (email)  |
+----------------+       +--------+---------+       +-----------+
                                  |
                    +-------------+-------------+
                    |             |              |
              +-----+----+ +-----+-----+ +-----+-----+
              |  X API   | | Anthropic | |  CueAPI   |
              |  v2      | | (drafts)  | | (verify)  |
              +----------+ +-----------+ +-----------+
```

**Discovery flow** (every 2 hours):
1. Search X API for posts matching 10 topic queries
2. **Basic filter**: English, <6h old, <=15 replies, not a brand, not on cooldown, not already surfaced
3. Cap to 30 freshest candidates
4. **LLM relevance scoring** (Claude Haiku): score each post on 5 dimensions, REJECT weak matches
5. Sort passed posts by relevance score, take top 5
6. **Draft replies** (Claude Opus 4.6): draft with self-check constraints and voice enforcement
7. Email digest to govind@vector.build
8. Report outcome to CueAPI

**Cooldown flow** (every 2 hours, offset by 1h):
1. Fetch Govind's recent replies from X API
2. Match against surfaced posts
3. Add replied-to users to 48-hour cooldown

## Setup

### 1. GitHub Secrets

Add these secrets to the repo (Settings > Secrets and variables > Actions):

| Secret | Description |
|--------|-------------|
| `X_CONSUMER_KEY` | X API OAuth 1.0a consumer key |
| `X_CONSUMER_SECRET` | X API OAuth 1.0a consumer secret |
| `X_ACCESS_TOKEN` | X API OAuth 1.0a access token |
| `X_ACCESS_TOKEN_SECRET` | X API OAuth 1.0a access token secret |
| `ANTHROPIC_API_KEY` | Anthropic API key for drafting |
| `RESEND_API_KEY` | Resend API key for sending email |
| `CUEAPI_API_KEY` | CueAPI API key (cue_sk_...) |
| `GOVIND_X_USER_ID` | Govind's numeric X user ID |

### 2. CueAPI Cues

Create two cues in the [CueAPI dashboard](https://dashboard.cueapi.ai):

**Cue 1: find-x-replies**
- Transport: `worker`
- Schedule: every 2 hours, 8am-10pm Pacific
- Payload: `{"task": "find-x-replies"}`

**Cue 2: update-x-cooldown**
- Transport: `worker`
- Schedule: every 2 hours, offset by 1 hour
- Payload: `{"task": "update-x-cooldown"}`

### 3. Resend

Verify the `vector.build` domain in [Resend](https://resend.com).
The agent sends from `x-agent@vector.build`.

## Pause / Resume

**Pause:** Push a file at `data/pause.flag` to the repo. The agent will skip discovery runs.

```bash
touch data/pause.flag
git add data/pause.flag && git commit -m "Pause agent" && git push
```

**Resume:** Delete the flag.

```bash
git rm data/pause.flag && git commit -m "Resume agent" && git push
```

## Manual Trigger

Go to **Actions** > **X Reply Discovery** > **Run workflow** > click **Run workflow**.

Or via CLI:

```bash
gh workflow run discovery.yml
```

## Filtering Funnel

The agent uses a two-stage LLM filtering approach:

### Stage 1: Basic filters (no LLM cost)
Language, freshness, reply count, brand exclusion, cooldown, dedup, account age. Removes obvious non-matches.

### Stage 2: LLM relevance scoring (Claude Haiku)
Each candidate is scored on 5 dimensions (0-10 each, max 50):
- **specific_problem**: Is there a concrete problem described?
- **open_to_discussion**: Is the poster inviting responses?
- **govind_has_experience**: Does this overlap with Govind's expertise?
- **not_crowded_yet**: How many replies already exist?
- **reply_would_add_value**: Would Govind's reply be genuinely useful?

Posts with total < 30, any score at 0, or `govind_has_experience` < 4 are rejected. Tune thresholds in `agent/config.py` (`RELEVANCE_MIN_TOTAL`).

### Stage 3: Drafting (Claude Opus 4.6)
Top 5 posts get replies drafted with self-check constraints: length limits, forbidden phrase detection, em dash removal, opening word enforcement, internal quality scoring, and similarity checks against voice examples.

### Model choices
- **Scoring**: `claude-haiku-4-5-20251001` (fast, cheap, good enough for pass/reject filtering)
- **Drafting**: `claude-opus-4-6` (best voice matching and self-check reasoning)

## Voice Prompt

The drafting prompt lives in `agent/drafter.py`. Update the `SYSTEM_PROMPT` constant to change Govind's voice rules, thesis, or examples.

## State Files

- `data/cooldown.json` - Users on cooldown with UTC expiry timestamps
- `data/surfaced_posts.json` - Post IDs already surfaced (permanent dedup)

These are committed back to the repo after each run by GitHub Actions.

## License

MIT
