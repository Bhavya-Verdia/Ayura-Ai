from datetime import datetime, timezone


def test_all_client_routes_are_mounted():
    from main import app

    mounted = {
        getattr(route, "path", "")
        for route in app.routes
    }

    expected = {
        "/api/progress/log",
        "/api/progress/summary",
        "/api/export/pdf",
        "/api/export/csv",
        "/api/notifications",
        "/api/reminders",
        "/api/privacy/export",
        "/api/community",
    }

    assert expected.issubset(mounted)



def test_plan_response_accepts_medicines_payload():
    from schemas.plan_schema import PlanResponse

    response = PlanResponse(
        user_summary={"name": "Test User", "dominant_dosha": "vata"},
        medicines=[{"medicine_name": "Example", "warnings": []}],
        health_risks=[],
        safety_checks={},
        generated_at=datetime.now(timezone.utc),
        generation_method="agentic",
        model_used="test",
    )

    assert response.medicines[0]["medicine_name"] == "Example"
