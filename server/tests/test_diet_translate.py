

def test_vegetarian_never_comes_back_as_vegan():
    """A live Hindi plan turned "timely vegetarian meals" into "वीगन भोजन"."""
    from services.diet_translate import faithful

    english = "This plan steadies Agni with warm, timely vegetarian meals."
    assert not faithful(english, "यह योजना गरम, समय पर लिए गए वीगन भोजन के साथ अग्नि को स्थिर करती है।", "plan_description", "hi")
    assert faithful(english, "यह योजना गरम, समय पर लिए गए शाकाहारी भोजन के साथ अग्नि को स्थिर करती है।", "plan_description", "hi")
    # A vegan plan may say vegan.
    assert faithful("A vegan plan.", "एक वीगन योजना।", "plan_title", "hi")
