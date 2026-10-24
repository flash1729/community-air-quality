"""General category guidance informed by CPCB health breakpoints.

This is public information, not a personal medical recommendation.
"""

from __future__ import annotations

GUIDANCE: dict[str, dict[str, list[str] | str]] = {
    "Good": {
        "summary": "Air quality is good for most people. Usual outdoor activity is fine.",
        "precautions": [
            "Enjoy outdoor activities as usual.",
            "No extra precautions are suggested for this category.",
        ],
    },
    "Satisfactory": {
        "summary": "Air quality is acceptable. Sensitive people may notice mild breathing discomfort.",
        "precautions": [
            "Most people can continue normal activities.",
            "People with asthma or other respiratory conditions can keep reliever medication available.",
        ],
    },
    "Moderate": {
        "summary": "People with lung disease, asthma, or heart disease may feel breathing discomfort.",
        "precautions": [
            "Consider shorter or easier outdoor activity if you have a lung or heart condition.",
            "Most healthy people can continue usual activities.",
        ],
    },
    "Poor": {
        "summary": "Prolonged exposure may cause breathing discomfort for many people.",
        "precautions": [
            "Reduce prolonged or heavy outdoor exertion.",
            "People with asthma, lung disease, or heart disease should limit time outdoors.",
        ],
    },
    "Very Poor": {
        "summary": "Prolonged exposure may cause respiratory illness, including for otherwise healthy people.",
        "precautions": [
            "Avoid prolonged outdoor activity.",
            "Keep windows closed if outdoor air is entering a busy road-facing room.",
            "People with respiratory or heart conditions should stay indoors when they can.",
        ],
    },
    "Severe": {
        "summary": "Air quality may affect healthy people and seriously affect people with existing illness.",
        "precautions": [
            "Avoid outdoor exertion.",
            "Stay indoors where the air is cleaner, if you can.",
            "Follow advice from local health authorities when they issue one.",
        ],
    },
}


def guidance_for(category: str | None) -> dict | None:
    if category is None:
        return None
    content = GUIDANCE.get(category)
    if content is None:
        return None
    return {
        "category": category,
        "summary": content["summary"],
        "precautions": content["precautions"],
        "disclaimer": "General category guidance only. It is not a medical assessment.",
    }
