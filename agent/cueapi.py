import requests

from agent.config import CUEAPI_API_KEY, CUEAPI_BASE_URL


def _headers():
    return {"Authorization": f"Bearer {CUEAPI_API_KEY}"}


def claim_cue(task_name: str) -> dict | None:
    """List claimable executions for a task and claim the first one.

    Returns the claimed execution dict (with 'execution_id' and 'payload'),
    or None if nothing to claim.
    """
    resp = requests.get(
        f"{CUEAPI_BASE_URL}/v1/executions/claimable",
        headers=_headers(),
        params={"task": task_name},
    )
    resp.raise_for_status()
    executions = resp.json().get("executions", [])
    if not executions:
        return None

    execution_id = executions[0]["id"]
    claim_resp = requests.post(
        f"{CUEAPI_BASE_URL}/v1/executions/{execution_id}/claim",
        headers=_headers(),
        json={"worker_id": "github-actions"},
    )
    if claim_resp.status_code == 409:
        return None  # already claimed by another worker
    claim_resp.raise_for_status()
    result = claim_resp.json()
    result["execution_id"] = execution_id
    return result


def report_outcome(execution_id: str, success: bool, metadata: dict | None = None,
                   error: str | None = None):
    """Report the outcome of a claimed execution."""
    body = {"success": success}
    if metadata:
        body["metadata"] = metadata
    if success:
        body["result"] = "Completed successfully"
    else:
        body["error"] = error or "Unknown error"

    resp = requests.post(
        f"{CUEAPI_BASE_URL}/v1/executions/{execution_id}/outcome",
        headers=_headers(),
        json=body,
    )
    resp.raise_for_status()
    return resp.json()
