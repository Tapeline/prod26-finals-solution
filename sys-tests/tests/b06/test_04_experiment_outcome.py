import httpx

from tests.config import app_url
from tests.conftest import DEFAULT_EXPERIMENTER_LOGIN
from tests.helpers import (
    create_flag,
    setup_active_experiment,
    finish_experiment,
    get_experiment,
)


def test_b6_4_supports_experiment_outcome_fixation(
    create_default_experimenter_in_db,
    create_default_admin_in_db,
):
    """B6-4: Система должна поддерживать фиксацию исхода эксперимента (`rollout/rollback/no effect`)."""
    # Test all three outcome types
    outcomes = ["rollout_winner", "rollback_default", "no_effect"]
    
    for outcome in outcomes:
        # Create a new experiment for each outcome test
        flag_key_test = f"flag_b6_4_{outcome}"
        create_flag(key=flag_key_test, type="string", default="default")
        exp_test = setup_active_experiment(flag_key=flag_key_test)
        
        # Stop experiment before archiving
        finish_experiment(exp_test["id"])

        # Archive experiment with specific outcome
        archive_resp = httpx.post(
            f"{app_url}/api/v1/experiments/{exp_test['id']}/archive",
            json={
                "outcome": outcome,
                "comment": f"Test outcome: {outcome}",
            },
            headers=DEFAULT_EXPERIMENTER_LOGIN,
            timeout=10.0,
        )
        assert archive_resp.status_code == 200, (
            f"Failed to archive experiment with outcome {outcome}: {archive_resp.status_code}"
        )
        
        archived_exp = archive_resp.json()
        assert archived_exp["state"] == "archived", (
            f"Experiment should be archived, but state is {archived_exp['state']}"
        )
        assert archived_exp["result"] is not None, "Experiment should have result"
        assert archived_exp["result"]["outcome"] == outcome, (
            f"Expected outcome {outcome}, but got {archived_exp['result']['outcome']}"
        )
        
        # Verify by reading the experiment back
        read_exp = get_experiment(exp_test["id"])
        assert read_exp["result"] is not None, "Experiment should have result when read back"
        assert read_exp["result"]["outcome"] == outcome, (
            f"Expected outcome {outcome} when reading back, but got {read_exp['result']['outcome']}"
        )
