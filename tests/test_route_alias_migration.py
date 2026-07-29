"""Regression coverage for route source-alias migration."""

from storage.configuration_sync import UnifiedConfigurationService


def test_collapsed_aliases_keep_unique_generated_route_names():
    service = object.__new__(UnifiedConfigurationService)

    candidate = {
        "routing": {
            "generic": {
                "outputs": [
                    {
                        "output": "discord",
                        "target": "default",
                    },
                ],
            },
            "redfish": {
                "outputs": [
                    {
                        "output": "discord",
                        "target": "default",
                    },
                ],
            },
            "home_lab": {
                "outputs": [
                    {
                        "output": "discord",
                        "target": "default",
                    },
                ],
            },
        },
    }

    changed = service._migrate_integration_model(candidate)

    assert changed is True
    assert list(candidate["routing"]) == ["*"]

    entries = candidate["routing"]["*"]["outputs"]
    names = [entry["name"] for entry in entries]

    assert names == [
        "generic to discord default",
        "redfish to discord default",
        "home_lab to discord default",
    ]
    assert len({name.casefold() for name in names}) == 3


def test_explicit_name_survives_source_alias_collapse():
    service = object.__new__(UnifiedConfigurationService)

    candidate = {
        "routing": {
            "redfish": {
                "outputs": [
                    {
                        "name": "Hardware Redfish Alerts",
                        "output": "discord",
                        "target": "default",
                    },
                ],
            },
        },
    }

    changed = service._migrate_integration_model(candidate)

    assert changed is True

    entry = candidate["routing"]["*"]["outputs"][0]

    assert entry["name"] == "Hardware Redfish Alerts"
