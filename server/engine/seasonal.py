"""
Ayura AI - Ayurvedic Seasonal Engine (Ritucharya)
Maps calendar dates to Ayurvedic seasons (Ritus) and their associated dosha variations.
"""

from datetime import date
from pydantic import BaseModel

class SeasonInfo(BaseModel):
    name: str
    english_name: str
    dominant_dosha: str
    accumulating_dosha: str
    pacifying_dosha: str
    description: str


def get_current_season(current_date: date = None) -> SeasonInfo:
    """Determine the Ayurvedic season (Ritu) based on the date."""
    if current_date is None:
        current_date = date.today()
    
    month = current_date.month
    day = current_date.day
    
    # Simple mapping based on mid-month transitions
    # Note: These are rough approximations for the Northern Hemisphere
    if (month == 1 and day >= 15) or month == 2 or (month == 3 and day < 15):
        # Shishir (Winter)
        return SeasonInfo(
            name="Shishir",
            english_name="Winter",
            dominant_dosha="kapha",
            accumulating_dosha="kapha",
            pacifying_dosha="pitta",
            description="Late winter. Kapha accumulates due to cold. Digestion is strong."
        )
    elif (month == 3 and day >= 15) or month == 4 or (month == 5 and day < 15):
        # Vasant (Spring)
        return SeasonInfo(
            name="Vasant",
            english_name="Spring",
            dominant_dosha="kapha",
            accumulating_dosha="none",
            pacifying_dosha="kapha", # Time to pacify Kapha
            description="Spring. Accumulated Kapha liquefies, potentially causing allergies or sluggishness."
        )
    elif (month == 5 and day >= 15) or month == 6 or (month == 7 and day < 15):
        # Grishma (Summer)
        return SeasonInfo(
            name="Grishma",
            english_name="Summer",
            dominant_dosha="pitta",
            accumulating_dosha="vata",
            pacifying_dosha="kapha",
            description="Summer. Pitta is dominant, Vata begins to accumulate due to dryness."
        )
    elif (month == 7 and day >= 15) or month == 8 or (month == 9 and day < 15):
        # Varsha (Monsoon/Late Summer)
        return SeasonInfo(
            name="Varsha",
            english_name="Monsoon",
            dominant_dosha="vata",
            accumulating_dosha="pitta",
            pacifying_dosha="vata",
            description="Monsoon or late summer. Vata is highly aggravated. Digestion is weak."
        )
    elif (month == 9 and day >= 15) or month == 10 or (month == 11 and day < 15):
        # Sharad (Autumn)
        return SeasonInfo(
            name="Sharad",
            english_name="Autumn",
            dominant_dosha="pitta",
            accumulating_dosha="none",
            pacifying_dosha="pitta",
            description="Autumn. Accumulated Pitta is aggravated by sudden heat after rains."
        )
    else:
        # Hemant (Pre-Winter)
        return SeasonInfo(
            name="Hemant",
            english_name="Pre-Winter",
            dominant_dosha="none",
            accumulating_dosha="kapha",
            pacifying_dosha="vata",
            description="Early winter. Body strength and digestive fire are at their peak."
        )

