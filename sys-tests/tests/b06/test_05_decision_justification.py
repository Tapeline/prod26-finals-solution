import httpx

from tests.config import app_url
from tests.conftest import DEFAULT_EXPERIMENTER_LOGIN
from tests.helpers import (
    create_flag,
    setup_active_experiment,
    finish_experiment,
    get_experiment,
)


def test_b6_5_saves_decision_justification(
    create_default_experimenter_in_db,
    create_default_admin_in_db,
):
    """B6-5: Система должна сохранять обоснование принятого решения."""
    flag_key = "flag_b6_5"
    create_flag(key=flag_key, type="string", default="default")
    experiment = setup_active_experiment(flag_key=flag_key)

    outcome = "rollout_winner"
    comment = "Treatment variant showed 15% improvement in conversion rate with statistical significance p < 0.05. User engagement metrics also improved by 10%."

    # Stop experiment before archiving
    finish_experiment(experiment["id"])

    # Archive experiment with outcome and comment
    archive_resp = httpx.post(
        f"{app_url}/api/v1/experiments/{experiment['id']}/archive",
        json={
            "outcome": outcome,
            "comment": comment,
        },
        headers=DEFAULT_EXPERIMENTER_LOGIN,
        timeout=10.0,
    )
    assert archive_resp.status_code == 200
    archived_exp = archive_resp.json()
    
    # Verify comment is saved
    assert archived_exp["result"] is not None, "Experiment should have result"
    assert archived_exp["result"]["comment"] == comment, (
        f"Expected comment '{comment}', but got '{archived_exp['result']['comment']}'"
    )
    
    # Verify by reading the experiment back
    read_exp = get_experiment(experiment["id"])
    assert read_exp["result"] is not None, "Experiment should have result when read back"
    assert read_exp["result"]["comment"] == comment, (
        f"Expected comment '{comment}' when reading back, but got '{read_exp['result']['comment']}'"
    )
    
    # Verify comment is not empty
    assert len(read_exp["result"]["comment"]) > 0, "Comment should not be empty"
