// Slot and day tables shared by the diet screen's modules.
// `server/scripts/diet_view_strings.py` reads SLOT_LABEL and the day tables
// for the translation keys, so keep them literal.

import {
  Sun, Coffee, UtensilsCrossed, Soup, Apple,
} from 'lucide-react'

export const DIET_MEAL_ICONS = {
  breakfast: Coffee,
  lunch:     Soup,
  snack:     Apple,
  dinner:    UtensilsCrossed,
}

export const DIET_DAY_LABELS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
// Display names, translated; the English names above are the plan's own keys.
export const SLOT_LABEL = { breakfast: 'Breakfast', lunch: 'Lunch', snack: 'Snack', dinner: 'Dinner', special_drink: 'Daily drink' }

export const DIET_DAY_FULL   = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
