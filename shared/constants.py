import os

CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-6")

# Alpha levels for significance testing — named by what they are, not by confidence label.
# Alpha 0.05 corresponds to 95% confidence, 0.01 to 99%, etc.
ALPHA_THRESHOLDS = {
    "strict": 0.01,
    "standard": 0.05,
    "lenient": 0.10,
}

SIGNIFICANCE_THRESHOLD = 0.05
MIN_SAMPLE_SIZE = 100
