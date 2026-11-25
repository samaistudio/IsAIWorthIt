"""Rule-based baseline classifiers. An LLM classifier replaces these later and is
evaluated against hand labels. Text is only read in memory, never stored."""
import re

TASK_RULES = [
    ("code", r"\b(bug|fix|code|function|repo|commit|build|compile|deploy|api|test|refactor|script|plugin|swift|python|typescript|react|css|html)\b"),
    ("media", r"\b(video|audio|podcast|mix|master|obs|stream|thumbnail|overlay|song|music|edit)\b"),
    ("data", r"\b(excel|sql|csv|data|dashboard|chart|metric|analy[sz])"),
    ("research", r"\b(research|find|search|look up|compare|best|recommend|which|what is)\b"),
    ("writing", r"\b(write|letter|cv|lebenslauf|anschreiben|email|text|translate|summar|draft)"),
    ("admin", r"\b(calendar|appointment|termin|file|folder|rename|install|settings|login|form)\b"),
]

# English, German, Persian (Latin and script) signals that a prompt corrects the AI.
CORRECTION = re.compile(
    r"(^\s*(no|nope|nein|not|na)\b|\bthat'?s (wrong|not)|\bwrong\b|\bfalsch\b|\bdoesn'?t work|"
    r"\bfunktioniert nicht|\bstill (broken|not)|\bagain\b|\bundo\b|\brevert\b|\binstead\b|"
    r"\bi said\b|\bnicht so\b|نه\b|اشتباه|درست نیست)",
    re.IGNORECASE,
)


def task_type(first_prompt: str) -> str:
    text = first_prompt.lower()
    for label, pattern in TASK_RULES:
        if re.search(pattern, text):
            return label
    return "other"


def is_correction(prompt: str) -> bool:
    return bool(CORRECTION.search(prompt[:400]))
