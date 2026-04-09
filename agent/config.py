import os

# --- X API OAuth 1.0a credentials ---
X_CONSUMER_KEY = os.environ["X_CONSUMER_KEY"]
X_CONSUMER_SECRET = os.environ["X_CONSUMER_SECRET"]
X_ACCESS_TOKEN = os.environ["X_ACCESS_TOKEN"]
X_ACCESS_TOKEN_SECRET = os.environ["X_ACCESS_TOKEN_SECRET"]
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
RESEND_API_KEY = os.environ["RESEND_API_KEY"]
CUEAPI_API_KEY = os.environ["CUEAPI_API_KEY"]
GOVIND_X_USER_ID = os.environ["GOVIND_X_USER_ID"]

# --- Paths ---
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
COOLDOWN_FILE = os.path.join(DATA_DIR, "cooldown.json")
SURFACED_FILE = os.path.join(DATA_DIR, "surfaced_posts.json")
PAUSE_FLAG = os.path.join(DATA_DIR, "pause.flag")

# --- Constants ---
SEARCH_WINDOW_HOURS = 6
COOLDOWN_HOURS = 48
MAX_RESULTS_PER_QUERY = 30
TOP_N_POSTS = 5
MIN_GOOD_POSTS = 3

# --- Email ---
EMAIL_FROM = "onboarding@resend.dev"
EMAIL_TO = "govind@vector.build"

# --- CueAPI ---
CUEAPI_BASE_URL = "https://api.cueapi.ai"
DISCOVERY_CUE_TASK = "find-x-replies"
COOLDOWN_CUE_TASK = "update-x-cooldown"

# --- Anthropic ---
DRAFTING_MODEL = "claude-opus-4-6"
SCORING_MODEL = "claude-haiku-4-5-20251001"

# --- Relevance scoring ---
RELEVANCE_MIN_TOTAL = 30
MAX_CANDIDATES_TO_SCORE = 30

# --- Brand accounts to exclude ---
BRAND_EXCLUSIONS = {
    "AnthropicAI", "OpenAI", "cursor_ai", "Cursor", "NVIDIA", "NVIDIAAIDev",
    "expo", "ExpoDev", "GoogleAI", "huggingface", "LangChainAI", "LlamaIndex",
    "vercel", "railway", "supabase", "github",
}

# --- Search queries ---
SEARCH_QUERIES = [
    '"claude code" (help OR broke OR failed OR "how do" OR issue) -is:reply -is:retweet',
    '"ai agent" (production OR staging OR "main branch" OR broke OR failed) -is:reply -is:retweet',
    'cursor (problem OR regression OR "how do you") -is:reply -is:retweet',
    '"vibe coding" (broke OR failed OR production) -is:reply -is:retweet',
    'claude.md (ignored OR "didn\'t work" OR "doesn\'t follow")',
    '"agent" (forgot OR forgotten OR "lost context")',
    '"design system" (claude OR cursor) (drift OR inconsistent OR edge)',
    '"openclaw" (cron OR failing OR broke OR reliability)',
    '"cron" (ai OR agent) (failed OR broke OR silent)',
    '"ci/cd" (agent OR ai) (broke OR bypass OR staging)',
]

# --- Account age filter ---
MIN_ACCOUNT_AGE_DAYS = 30

# --- Reply count filter ---
MAX_REPLY_COUNT = 15
