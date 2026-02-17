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
