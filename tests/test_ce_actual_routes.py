from test_platform_api import platform_api, call, login, create_destination, create_route


def test_destination_choices_include_persisted_custom_route_identity_and_enabled_state(platform_api):
    headers = login(platform_api)
    destination = create_destination(platform_api, headers)
    canonical = create_route(platform_api, headers, destination["id"])
    with platform_api["database"].transaction() as connection:
        connection.execute("""INSERT INTO routes (
            id, owner_user_id, name, name_normalized, source, input_type,
            filters_json, priority, enabled, created_at, updated_at
        ) SELECT ?, owner_user_id, ?, ?, source, input_type,
                 filters_json, priority, 0, created_at, updated_at
          FROM routes WHERE id = ?""", ("b" * 32, "Imported custom route", "imported custom route", canonical["id"]))
        connection.execute("INSERT INTO route_destinations(route_id, destination_id, created_at) VALUES (?, ?, 1)", ("b" * 32, destination["id"]))
    response = call(platform_api, "GET", "/api/v2/routes", headers=headers)
    assert response.status == 200
    custom = next(route for route in response.payload["actual_routes"] if route["id"] == "b" * 32)
    assert custom["name"] == "Imported custom route"
    assert custom["enabled"] is False
    assert custom["destination_ids"] == [destination["id"]]
    assert len(response.payload["routes"]) == 1
    destination_response = call(platform_api, "GET", "/api/v2/destinations/" + destination["id"], headers=headers)
    assert set(destination_response.payload["destination"]["actual_route_ids"]) == {canonical["id"], "b" * 32}
    with platform_api["database"].transaction() as connection:
        connection.execute("DELETE FROM route_destinations WHERE destination_id = ? AND route_id = ?", (destination["id"], canonical["id"]))
    destination_response = call(platform_api, "GET", "/api/v2/destinations/" + destination["id"], headers=headers)
    assert destination_response.payload["destination"]["actual_route_ids"] == ["b" * 32]
    saved = call(platform_api, "PATCH", "/api/v2/destinations/" + destination["id"], {"route_ids": destination_response.payload["destination"]["actual_route_ids"]}, headers)
    assert saved.status == 200
    assert saved.payload["destination"]["actual_route_ids"] == ["b" * 32]
    with platform_api["database"].connect() as connection:
        assert [row[0] for row in connection.execute("SELECT route_id FROM route_destinations WHERE destination_id = ?", (destination["id"],))] == ["b" * 32]
        assert connection.execute("SELECT enabled FROM routes WHERE id = ?", ("b" * 32,)).fetchone()[0] == 0
    other_headers = login(platform_api, "owner-user", "owner secure password")
    other = call(platform_api, "GET", "/api/v2/routes", headers=other_headers)
    assert "b" * 32 not in {route["id"] for route in other.payload["actual_routes"]}
