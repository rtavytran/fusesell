def _team_payload(team_id: str = "team-001", **overrides):
    payload = {
        "team_id": team_id,
        "org_id": "org-123",
        "org_name": "FuseSell Org",
        "plan_id": "plan-456",
        "plan_name": "FuseSell AI",
        "project_code": "proj-001",
        "name": "Outbound Squad",
        "description": "Primary outreach team",
        "avatar": "https://fusesell.test/avatar.png",
    }
    payload.update(overrides)
    return payload


def test_save_and_get_team_roundtrip(data_manager):
    payload = _team_payload()
    data_manager.save_team(**payload)

    stored = data_manager.get_team(payload["team_id"])
    assert stored is not None
    assert stored["team_id"] == payload["team_id"]
    assert stored["name"] == payload["name"]
    assert stored["plan_id"] == payload["plan_id"]


def test_update_team_modifies_selected_fields(data_manager):
    payload = _team_payload()
    data_manager.save_team(**payload)

    updated_name = "Expansion Squad"
    updated_plan = "FuseSell AI Enterprise"
    assert data_manager.update_team(
        payload["team_id"], name=updated_name, plan_name=updated_plan
    )

    stored = data_manager.get_team(payload["team_id"])
    assert stored["name"] == updated_name
    assert stored["plan_name"] == updated_plan


def test_team_status_can_be_toggled(data_manager):
    payload = _team_payload("team-status")
    data_manager.save_team(**payload)

    stored = data_manager.get_team(payload["team_id"])
    assert stored["status"] == "active"

    assert data_manager.update_team_status(payload["team_id"], "inactive")
    assert data_manager.get_team(payload["team_id"])["status"] == "inactive"

    assert data_manager.update_team(payload["team_id"], status="active")
    assert data_manager.get_team(payload["team_id"])["status"] == "active"


def test_list_teams_returns_all_for_org(data_manager):
    first = _team_payload("team-001")
    second = _team_payload("team-002", name="Inbound Squad")
    data_manager.save_team(**first)
    data_manager.save_team(**second)

    teams = data_manager.list_teams(first["org_id"])
    identifiers = {team["team_id"] for team in teams}
    assert identifiers == {first["team_id"], second["team_id"]}


def test_save_and_get_team_settings_roundtrip(data_manager):
    payload = _team_payload()
    data_manager.save_team(**payload)

    data_manager.save_team_settings(
        team_id=payload["team_id"],
        org_id=payload["org_id"],
        plan_id=payload["plan_id"],
        team_name=payload["name"],
        gs_team_organization={"sales_regions": ["NA", "EU"]},
        gs_team_rep=[{"name": "Alex"}],
        gs_team_product=[{"product_id": "prod-001"}],
        gs_team_schedule_time={"timezone": "UTC"},
        gs_team_initial_outreach={"enabled": True},
        gs_team_follow_up={"sequence": 2},
        gs_team_auto_interaction={"mode": "assist"},
        gs_team_followup_schedule_time={"window": "business_hours"},
        gs_team_birthday_email={"enabled": False},
    )

    settings = data_manager.get_team_settings(payload["team_id"])
    assert settings is not None
    assert settings["org_id"] == payload["org_id"]
    assert settings["gs_team_organization"]["sales_regions"] == ["NA", "EU"]
    assert settings["gs_team_rep"][0]["name"] == "Alex"
    assert settings["gs_team_product"][0]["product_id"] == "prod-001"


def test_save_team_settings_updates_existing_record(data_manager):
    payload = _team_payload()
    data_manager.save_team(**payload)

    data_manager.save_team_settings(
        team_id=payload["team_id"],
        org_id=payload["org_id"],
        plan_id=payload["plan_id"],
        team_name=payload["name"],
        gs_team_schedule_time={"timezone": "UTC"},
    )

    data_manager.save_team_settings(
        team_id=payload["team_id"],
        org_id=payload["org_id"],
        plan_id=payload["plan_id"],
        team_name=payload["name"],
        gs_team_schedule_time={"timezone": "America/New_York"},
    )

    settings = data_manager.get_team_settings(payload["team_id"])
    assert settings["gs_team_schedule_time"]["timezone"] == "America/New_York"


def test_get_products_by_team_uses_team_settings(data_manager):
    team = _team_payload()
    data_manager.save_team(**team)

    product_payload = {
        "product_id": "prod-001",
        "org_id": team["org_id"],
        "org_name": team["org_name"],
        "project_code": team["project_code"],
        "productName": "FuseSell Starter",
        "shortDescription": "Entry-level automation",
        "longDescription": "Starter bundle.",
        "category": "Software",
        "targetUsers": ["SMB"],
    }
    data_manager.save_product(product_payload)

    data_manager.save_team_settings(
        team_id=team["team_id"],
        org_id=team["org_id"],
        plan_id=team["plan_id"],
        team_name=team["name"],
        gs_team_product=[{"product_id": product_payload["product_id"]}],
    )

    products = data_manager.get_products_by_team(team["team_id"])
    assert len(products) == 1
    assert products[0]["product_id"] == product_payload["product_id"]
