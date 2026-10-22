"""The interaction explanation is about what the user entered, nothing else.

Checking ashwagandha against levothyroxine, the explanation said "the suggested home
remedy includes ashwagandha and guggulu for hypothyroid support". No remedy had been
suggested and the user was not hypothyroid: a retrieved knowledge-base remedy had
been pasted in as "MEDICAL CONTEXT" and narrated as the user's own."""

import inspect

import routes.plans as plans


def test_retrieved_text_is_framed_as_background_not_the_users_plan():
    src = inspect.getsource(plans.check_interactions)
    assert "MEDICAL CONTEXT" not in src
    assert "BACKGROUND REFERENCE" in src
    assert "Discuss only the herbs and medications listed above" in src
