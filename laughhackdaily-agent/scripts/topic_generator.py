"""
Topic Generator for LaughHackDaily
Generates viral TikTok topics using layered themes, angles, and hooks.
"""

import random
from typing import List, Dict, Optional


# Core themes for psychology/self-improvement content
CORE_THEMES = [
    "mirroring behavior",
    "silence in conversations",
    "eye contact",
    "body language",
    "first impressions",
    "status signals",
    "confidence tricks",
    "charisma secrets",
    "manipulation detection",
    "social dominance",
    "likability hacks",
    "persuasion techniques",
    "reading people",
    "emotional intelligence",
    "power dynamics",
    "trust building",
    "influence patterns",
    "nonverbal cues",
    "social proof",
    "reputation management",
    "authority signals",
    "attention control",
    "presence building",
    "conversation control",
    "subtle dominance",
]

# Angles that change the framing
ANGLES = [
    "warning",           # "Be careful when someone does X"
    "observation",       # "Notice how successful people always X"
    "self-reflection",   # "If you find yourself doing X..."
    "social pattern",    # "This happens in every conversation"
    "hidden truth",      # "What no one tells you about X"
    "reverse psychology", # "The opposite of what you think"
    "dark psychology",   # "The manipulation tactic called X"
    "elite behavior",    # "What high-status people do differently"
    "subconscious",      # "Your brain does this without you knowing"
    "instant hack",      # "Do this one thing to instantly X"
]

# Hook templates that drive engagement
HOOK_TEMPLATES = [
    "Most people don't realize {theme}",
    "The real reason behind {theme}",
    "What {theme} actually reveals about you",
    "If they do this, {theme}",
    "The {theme} trick that changes everything",
    "Why {theme} makes you instantly more {adjective}",
    "{theme} says more than words ever will",
    "The psychology of {theme}",
    "What high-status people know about {theme}",
    "The hidden meaning behind {theme}",
    "When you understand {theme}, everything changes",
    "The {theme} rule nobody talks about",
]

# Adjectives for hooks
ADJECTIVES = [
    "powerful",
    "attractive",
    "confident",
    "persuasive",
    "likable",
    "memorable",
    "trusted",
    "respected",
    "influential",
    "charismatic",
]


class TopicGenerator:
    """Generates viral TikTok topics using layered system."""

    def __init__(
        self,
        themes: Optional[List[str]] = None,
        angles: Optional[List[str]] = None,
        hooks: Optional[List[str]] = None
    ):
        self.themes = themes or CORE_THEMES
        self.angles = angles or ANGLES
        self.hooks = hooks or HOOK_TEMPLATES

    def generate_single(self) -> Dict[str, str]:
        """Generate a single topic with metadata."""
        theme = random.choice(self.themes)
        angle = random.choice(self.angles)
        hook_template = random.choice(self.hooks)
        adjective = random.choice(ADJECTIVES)

        # Create the hook
        hook = hook_template.format(
            theme=theme,
            adjective=adjective
        )

        return {
            "topic": hook,
            "theme": theme,
            "angle": angle,
            "hook_template": hook_template
        }

    def generate_batch(self, count: int = 20, unique_themes: bool = True) -> List[Dict]:
        """
        Generate multiple topics.

        Args:
            count: Number of topics to generate
            unique_themes: If True, avoid repeating themes
        """
        topics = []
        used_themes = set()

        attempts = 0
        max_attempts = count * 3

        while len(topics) < count and attempts < max_attempts:
            topic = self.generate_single()
            attempts += 1

            if unique_themes:
                if topic["theme"] in used_themes:
                    continue
                used_themes.add(topic["theme"])

            topics.append(topic)

        return topics

    def generate_themed_series(
        self,
        theme: str,
        count: int = 5
    ) -> List[Dict]:
        """Generate multiple topics around a single theme."""
        topics = []

        for angle in random.sample(self.angles, min(count, len(self.angles))):
            hook_template = random.choice(self.hooks)
            adjective = random.choice(ADJECTIVES)

            hook = hook_template.format(
                theme=theme,
                adjective=adjective
            )

            topics.append({
                "topic": hook,
                "theme": theme,
                "angle": angle,
                "hook_template": hook_template
            })

        return topics

    def generate_daily_queue(self, count: int = 20) -> List[str]:
        """Generate a day's worth of topics (just the topic strings)."""
        batch = self.generate_batch(count, unique_themes=True)
        return [t["topic"] for t in batch]


# Keyword library for Pexels (improves footage relevance)
PEXELS_KEYWORD_LIBRARY = {
    "mirroring behavior": ["gesture", "reflection", "imitation", "body language"],
    "silence in conversations": ["pause", "thinking", "listening", "contemplation"],
    "eye contact": ["eyes", "gaze", "stare", "looking"],
    "body language": ["posture", "gesture", "movement", "stance"],
    "first impressions": ["meeting", "handshake", "introduction", "entrance"],
    "status signals": ["success", "luxury", "confidence", "power"],
    "confidence tricks": ["confident person", "power pose", "assertive"],
    "charisma secrets": ["charismatic", "charming", "magnetic", "social"],
    "manipulation detection": ["suspicious", "analyzing", "watching", "alert"],
    "social dominance": ["leader", "authority", "commanding", "dominant"],
    "likability hacks": ["friendly", "approachable", "smiling", "warm"],
    "persuasion techniques": ["convincing", "negotiation", "influence"],
    "reading people": ["observation", "analyzing", "studying", "watching"],
    "emotional intelligence": ["empathy", "understanding", "emotion", "connection"],
    "power dynamics": ["hierarchy", "control", "influence", "dominance"],
    "trust building": ["trust", "reliability", "connection", "bonding"],
    "influence patterns": ["influence", "persuasion", "impact", "effect"],
    "nonverbal cues": ["gesture", "expression", "signal", "movement"],
    "social proof": ["crowd", "followers", "popularity", "validation"],
    "reputation management": ["image", "perception", "impression", "brand"],
    "authority signals": ["expert", "professional", "authority", "respect"],
    "attention control": ["focus", "attention", "engaging", "captivating"],
    "presence building": ["presence", "aura", "commanding", "magnetic"],
    "conversation control": ["speaking", "dialogue", "discussion", "talking"],
    "subtle dominance": ["subtle", "control", "influence", "quiet power"],
}


def get_keywords_for_theme(theme: str) -> List[str]:
    """Get optimized Pexels keywords for a theme."""
    # Direct match
    if theme in PEXELS_KEYWORD_LIBRARY:
        return PEXELS_KEYWORD_LIBRARY[theme]

    # Partial match
    for key, keywords in PEXELS_KEYWORD_LIBRARY.items():
        if key in theme or theme in key:
            return keywords

    # Default fallback
    return ["confident person", "professional", "success", "mindset"]
