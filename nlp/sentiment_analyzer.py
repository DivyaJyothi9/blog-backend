from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import re

# Initialize VADER analyzer
analyzer = SentimentIntensityAnalyzer()

def preprocess_text(content: str) -> str:
    """
    Optional preprocessing step:
    - Lowercase text
    - Remove special characters
    - Can be extended with stopword removal or domain-specific handling
    """
    content = content.lower()
    content = re.sub(r"[^a-zA-Z0-9\s]", "", content)  # remove punctuation/symbols
    return content.strip()

def is_positive(content: str) -> bool:
    """
    Returns True if the content is neutral or positive,
    False if strongly negative.
    Uses VADER compound score.
    """
    cleaned = preprocess_text(content)
    score = analyzer.polarity_scores(cleaned)
    # Allow neutral and positive, block only strongly negative
    return score['compound'] >= -0.05

def analyze_sentiment(content: str) -> dict:
    """
    Returns a structured sentiment analysis result.
    Provides a soft warning if content is negative.
    """
    cleaned = preprocess_text(content)
    score = analyzer.polarity_scores(cleaned)
    compound = score['compound']

    if compound <= -0.05:
        return {
            "status": "warning",
            "message": "Your blog seems negative. Please add more constructive details.",
            "scores": score
        }
    else:
        return {
            "status": "ok",
            "message": "Blog sentiment acceptable.",
            "scores": score
        }