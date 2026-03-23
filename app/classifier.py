from typing import Dict, List


SECTION_MAP = {
    # Legacy IPC-like references (demo)
    "302": "Murder",
    "379": "Theft",
    "392": "Robbery",
    "354": "Assault / Harassment",
    "363": "Kidnapping",
    "323": "Assault / Hurt",
    "506": "Criminal Intimidation",
    "376": "Sexual Assault",
    "427": "Property Damage",
    "420": "Fraud",
    # You can later map BNS sections here too
}


KEYWORD_RULES = {
    "Murder": ["murder", "killed", "dead body", "homicide", "stabbed to death", "shot dead"],
    "Theft": ["theft", "stolen", "snatched", "chain snatching", "pickpocket", "bike stolen"],
    "Robbery": ["robbery", "loot", "looted", "armed robbery", "weapon point"],
    "Kidnapping": ["kidnapped", "abducted", "missing child", "forcibly taken"],
    "Assault / Harassment": ["harassment", "outrage modesty", "eve teasing", "molestation"],
    "Assault / Hurt": ["fight", "assault", "beaten", "injured", "attack", "hurt"],
    "Fraud": ["fraud", "cheated", "scam", "otp", "bank fraud", "cyber fraud"],
    "Property Damage": ["vandalism", "damage", "burnt vehicle", "property damage"],
    "Criminal Intimidation": ["threat", "threatened", "death threat", "intimidation"],
}


def infer_priority(crime_type: str, text: str) -> str:
    text = (text or "").lower()

    critical_types = {"Murder", "Kidnapping"}
    high_types = {"Robbery", "Sexual Assault", "Assault / Hurt"}

    if crime_type in critical_types:
        return "Critical"
    if crime_type in high_types:
        return "High"

    if any(word in text for word in ["weapon", "gun", "knife", "child victim", "serious injury"]):
        return "High"

    if crime_type in {"Fraud", "Theft", "Criminal Intimidation"}:
        return "Medium"

    return "Low"


def extract_tags(text: str) -> List[str]:
    text = (text or "").lower()
    tags = []

    patterns = {
        "night-crime": ["midnight", "night", "late night"],
        "vehicle": ["car", "bike", "vehicle", "number plate"],
        "weapon": ["knife", "gun", "pistol", "weapon"],
        "public-place": ["market", "road", "bus stand", "station", "junction"],
        "repeat-risk": ["repeat", "again", "habitual"],
    }

    for tag, keys in patterns.items():
        if any(k in text for k in keys):
            tags.append(tag)

    return tags


def classify_crime_type(description: str, legal_section: str = "") -> Dict[str, str]:
    description_lower = (description or "").lower()
    legal_section = legal_section or ""

    # Section-based classification
    for section, crime in SECTION_MAP.items():
        if section in legal_section:
            priority = infer_priority(crime, description_lower)
            tags = extract_tags(description_lower)
            return {
                "crime_type": crime,
                "priority": priority,
                "tags": ", ".join(tags)
            }

    # Keyword-based fallback
    for crime, keywords in KEYWORD_RULES.items():
        if any(keyword in description_lower for keyword in keywords):
            priority = infer_priority(crime, description_lower)
            tags = extract_tags(description_lower)
            return {
                "crime_type": crime,
                "priority": priority,
                "tags": ", ".join(tags)
            }

    # Default
    tags = extract_tags(description_lower)
    return {
        "crime_type": "Other",
        "priority": "Low",
        "tags": ", ".join(tags)
    }