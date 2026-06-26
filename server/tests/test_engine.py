from engine.bmi_calculator import bmi_calculator
from engine.calorie_calculator import calorie_calculator

def test_bmi_calculation():
    result = bmi_calculator.calculate(70, 175)
    assert result["bmi"] == 22.9
    assert result["category"] == "normal"

def test_calorie_calculation():
    result = calorie_calculator.calculate("male", 30, 70, 175, "moderate", "muscle_gain")
    assert "target_calories" in result
    assert result["target_calories"] > 2000
