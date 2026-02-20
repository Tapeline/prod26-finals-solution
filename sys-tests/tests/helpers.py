import pytest
import httpx
from tests.client import iap_login
from tests.config import app_url
from tests.conftest import DEFAULT_EXPERIMENTER_LOGIN, DEFAULT_ADMIN_LOGIN


def create_flag(
    login: dict[str, str] = DEFAULT_EXPERIMENTER_LOGIN,
    **override_params
):
    payload = {
        "key": "test_flag",
        "description": "Test flag",
        "type": "boolean",
        "default": "true",
        **override_params
    }
    response = httpx.post(
        f"{app_url}/api/v1/flags/create",
        json=payload,
        headers=login
    ).raise_for_status()
    return response.json()


def create_experiment(
    login: dict[str, str] = DEFAULT_EXPERIMENTER_LOGIN,
    **override_params,
):
    payload = {
        "name": "Test Experiment",
        "flag_key": "test_flag",
        "audience": 100,
        "variants": [
            {
                "name": "control", "value": "off", "audience": 50,
                "is_control": True
            },
            {
                "name": "treatment", "value": "on", "audience": 50,
                "is_control": False
            }
        ],
        "metrics": {
            "primary": "clicks",
            "secondary": [],
            "guarding": []
        },
        **override_params,
    }

    response = httpx.post(
        f"{app_url}/api/v1/experiments/create",
        json=payload,
        headers=login
    ).raise_for_status()
    return response.json()


def set_approver_group(
    experimenter_id, approver_ids, threshold,
    login=DEFAULT_ADMIN_LOGIN
):
    payload = {
        "approver_ids": approver_ids,
        "threshold": threshold
    }
    httpx.put(
        f"{app_url}/api/v1/accounts/experimenter/{experimenter_id}/approver-group",
        json=payload,
        headers=login
    ).raise_for_status()


def send_to_review(
    exp_id, login=DEFAULT_EXPERIMENTER_LOGIN
):
    httpx.post(
        f"{app_url}/api/v1/experiments/{exp_id}/send-to-review",
        headers=login
    ).raise_for_status()


def get_experiment(exp_id, login=DEFAULT_EXPERIMENTER_LOGIN):
    return httpx.get(
        f"{app_url}/api/v1/experiments/{exp_id}",
        headers=login
    ).raise_for_status().json()


def approve_experiment(exp_id, login=DEFAULT_ADMIN_LOGIN):
    httpx.post(
        f"{app_url}/api/v1/experiments/{exp_id}/approve",
        headers=login
    ).raise_for_status()


def start_experiment(exp_id: str, login=DEFAULT_EXPERIMENTER_LOGIN):
    """Переводит эксперимент из approved в started."""
    response = httpx.post(
        f"{app_url}/api/v1/experiments/{exp_id}/start",
        headers=login
    )
    response.raise_for_status()
    return response.json()


def get_flags(subject_id: str, flag_keys: list[str], attributes: dict = None):
    """Вызывает API принятия решений."""
    if attributes is None:
        attributes = {}

    payload = {
        "subject_id": subject_id,
        "flags": flag_keys,
        "attributes": attributes
    }

    response = httpx.post(
        f"{app_url}/api/v1/decisions/get-flags",
        json=payload
    )
    response.raise_for_status()
    return response.json()["flags"]


def get_flag_decision(
    subject_id: str,
    flag_key: str,
    attributes: dict | None = None,
):
    """Возвращает решение по одному флагу."""
    return get_flags(
        subject_id=subject_id,
        flag_keys=[flag_key],
        attributes=attributes,
    )[flag_key]


def decision_variant_name(decision_id: str) -> str:
    """Достаёт имя варианта (control/treatment/...) из decision_id."""
    return decision_id.split(":")[-1]


def find_subject_for_variant_name(
    flag_key: str,
    desired_variant_name: str,
    *,
    prefix: str = "subj",
    max_tries: int = 500,
):
    """
    Подбирает subject_id, который попадёт в нужный variant_name.

    Важно: используем детерминированность раздачи (B2-4).
    """
    for i in range(max_tries):
        subject_id = f"{prefix}_{desired_variant_name}_{i}"
        decision = get_flag_decision(subject_id, flag_key)
        if decision_variant_name(decision["id"]) == desired_variant_name:
            return subject_id, decision
    raise AssertionError(
        f"Could not find subject for variant '{desired_variant_name}' "
        f"for flag '{flag_key}' in {max_tries} tries"
    )


def finish_experiment(
    exp_id: str,
    login: dict[str, str] = DEFAULT_EXPERIMENTER_LOGIN,
):
    """Останавливает running эксперимент переводом в finished."""
    response = httpx.post(
        f"{app_url}/api/v1/experiments/{exp_id}/manage-running",
        json={"new_state": "finished"},
        headers=login,
        timeout=10.0,
    )
    response.raise_for_status()
    return response.json()


def setup_active_experiment(
    flag_key: str,
    variants: list = None,
    targeting: str | None = None,
    audience: int = 100,
    **kwargs,
):
    if variants is None:
        variants = [
            {
                "name": "control",
                "value": "A",
                "audience": 50,
                "is_control": True
            },
            {
                "name": "treatment",
                "value": "B",
                "audience": 50,
                "is_control": False
            }
        ]

    exp_params = {
        "flag_key": flag_key,
        "variants": variants,
        "audience": audience,
        **kwargs
    }

    if targeting:
        exp_params["targeting"] = targeting

    exp = create_experiment(**exp_params)
    send_to_review(exp["id"])
    approve_experiment(exp["id"])
    start_experiment(exp["id"])

    return exp


def create_event_type(
    login: dict[str, str] = DEFAULT_EXPERIMENTER_LOGIN,
    **override_params
):
    payload = {
        "id": "test_event",
        "name": "Test Event",
        "schema": {
            "type": "object",
            "properties": {}
        },
        **override_params
    }
    response = httpx.post(
        f"{app_url}/api/v1/events/types/create",
        json=payload,
        headers=login
    ).raise_for_status()
    return response.json()


def create_event_data(
    event_type: str,
    decision_id: str,
    **override_params
):
    from datetime import datetime, timezone
    payload = {
        "event_id": "evt_1",
        "event_type": event_type,
        "decision_id": decision_id,
        "payload": {},
        "issued_at": datetime.now(timezone.utc).isoformat(),
    }
    payload.update(override_params)
    return payload
