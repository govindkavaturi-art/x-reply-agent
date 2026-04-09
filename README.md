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
2. Filter: English, <6h old, <=15 replies, not a brand, not on cooldown, not already surfaced
3. Rank by specificity, freshness, and crowd inverse
4. Draft top 5 replies via Anthropic API in Govind's voice
5. Email digest to govind@vector.build
6. Report outcome to CueAPI

**Cooldown flow** (every 2 hours, offset by 1h):
1. Fetch Govind's recent replies from X API
2. Match against surfaced posts
3. Add replied-to users to 48-hour cooldown

## Setup

### 1. GitHub Secrets

Add these secrets to the repo (Settings > Secrets and variables > Actions):

| Secret | Description |
|--------|-------------|
| `X_API_BEARER_TOKEN` | X API v2 bearer token (Basic tier or higher) |
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

## Voice Prompt

The drafting prompt lives in `agent/drafter.py`. Update the `SYSTEM_PROMPT` constant to change Govind's voice rules, thesis, or examples.

## State Files

- `data/cooldown.json` - Users on cooldown with UTC expiry timestamps
- `data/surfaced_posts.json` - Post IDs already surfaced (permanent dedup)

These are committed back to the repo after each run by GitHub Actions.

## License

MIT
