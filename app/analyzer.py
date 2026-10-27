import math
import re
from dataclasses import dataclass

SENTENCE_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\"'“‘])")
WORD_RE = re.compile(r"[A-Za-z][A-Za-z'\-]*")

STRONG_WORDS = {
    "must", "should", "never", "always", "because", "therefore", "however", "yet", "but",
    "truth", "power", "change", "meaning", "future", "past", "human", "world", "life",
    "death", "freedom", "justice", "memory", "imagine", "create", "reveals", "matters",
    "urgent", "essential", "beautiful", "difficult", "simple", "clear", "risk", "hope"
}

BOILERPLATE_WORDS = {
    "copyright", "references", "appendix", "figure", "table", "doi", "http", "www", "permission",
    "abstract", "keywords", "page"
}

CONTRAST_WORDS = {"but", "yet", "however", "although", "while", "whereas", "instead"}


@dataclass
class RankedSentence:
    text: str
    score: float
    position: int
    is_selected: bool


def normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def split_sentences(text: str) -> list[str]:
    cleaned = normalize_whitespace(text)
    if not cleaned:
        return []
    rough = SENTENCE_RE.split(cleaned)
    sentences: list[str] = []
    for part in rough:
        sentence = part.strip(" \t\n\r")
        if len(sentence) < 12:
            continue
        if not re.search(r"[.!?]$", sentence):
            sentence += "."
        sentences.append(sentence)
    return sentences


def score_sentence(sentence: str, position: int, total: int) -> float:
    words = WORD_RE.findall(sentence)
    word_count = len(words)
    if word_count == 0:
        return 0.0

    lower_words = [w.lower() for w in words]
    unique_ratio = len(set(lower_words)) / word_count

    ideal_length = 24
    length_score = max(0.0, 1.0 - abs(word_count - ideal_length) / 28)
    clarity_score = min(1.0, unique_ratio * 1.15)
    strong_score = min(1.0, sum(1 for w in lower_words if w in STRONG_WORDS) / 3)
    contrast_score = 0.18 if any(w in CONTRAST_WORDS for w in lower_words) else 0.0
    punctuation_score = 0.12 if any(mark in sentence for mark in [":", ";", "—", "-"]) else 0.0
    quote_shape_score = 0.16 if 8 <= word_count <= 38 else -0.18
    boilerplate_penalty = min(0.45, sum(1 for w in lower_words if w in BOILERPLATE_WORDS) * 0.15)
    all_caps_penalty = 0.2 if sentence.isupper() else 0.0

    if total <= 1:
        position_score = 0.05
    else:
        relative = position / max(1, total - 1)
        position_score = 0.08 * (1 - abs(relative - 0.35))

    raw = (
        0.30 * length_score
        + 0.24 * clarity_score
        + 0.22 * strong_score
        + contrast_score
        + punctuation_score
        + quote_shape_score
        + position_score
        - boilerplate_penalty
        - all_caps_penalty
    )
    confidence = 1 / (1 + math.exp(-4.2 * (raw - 0.48)))
    return round(max(0.01, min(0.99, confidence)), 3)


def rank_quotable_sentences(text: str, top_n: int = 10) -> list[RankedSentence]:
    sentences = split_sentences(text)
    total = len(sentences)
    ranked = [
        RankedSentence(text=s, score=score_sentence(s, i, total), position=i, is_selected=False)
        for i, s in enumerate(sentences)
    ]
    ranked.sort(key=lambda item: item.score, reverse=True)
    for item in ranked[:top_n]:
        item.is_selected = True
    return ranked[:top_n]
