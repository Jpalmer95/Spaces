import gradio_client
import io
import sys
from gradio_client.client import Job # For type hinting

def get_space_api_details(space_id: str) -> str | None:
    """
    Retrieves the API details of a Hugging Face Space.

    Args:
        space_id: The ID of the Space (e.g., "author_name/space_name").

    Returns:
        A string containing the API information, or None if an error occurs.
    """
    try:
        client = gradio_client.Client(space_id)
    except Exception as e:
        print(f"Error initializing client for Space '{space_id}': {e}")
        return None

    # Redirect stdout to capture the output of view_api()
    old_stdout = sys.stdout
    sys.stdout = captured_output = io.StringIO()
    try:
        client.view_api(all_endpoints=True)
        api_details = captured_output.getvalue()
    except Exception as e:
        print(f"Error fetching API details for Space '{space_id}': {e}")
        api_details = None
    finally:
        sys.stdout = old_stdout # Restore stdout
        captured_output.close()
    return api_details

def run_space_predict(space_id: str, api_name: str, *args) -> any:
    """
    Runs a prediction on a Hugging Face Space.

    Args:
        space_id: The ID of the Space.
        api_name: The API endpoint name (e.g., "/predict").
        *args: Arguments to pass to the Space's prediction function.

    Returns:
        The prediction result, or None if an error occurs.
    """
    try:
        client = gradio_client.Client(space_id)
        result = client.predict(api_name=api_name, *args)
        return result
    except Exception as e:
        print(f"Error during prediction for Space '{space_id}', API '{api_name}': {e}")
        return None

def run_space_submit(space_id: str, api_name: str, *args) -> Job | None:
    """
    Submits a job to a Hugging Face Space asynchronously.

    Args:
        space_id: The ID of the Space.
        api_name: The API endpoint name.
        *args: Arguments to pass to the Space's function.

    Returns:
        A Job object, or None if an error occurs.
    """
    try:
        client = gradio_client.Client(space_id)
        job = client.submit(api_name=api_name, *args)
        return job
    except Exception as e:
        print(f"Error submitting job to Space '{space_id}', API '{api_name}': {e}")
        return None

def get_job_status(job: Job) -> gradio_client.client.Status | None:
    """
    Gets the status of a submitted job.

    Args:
        job: The Job object.

    Returns:
        The job status (e.g., Status.PROCESSING, Status.COMPLETED), or None if an error occurs.
    """
    if not isinstance(job, Job):
        print("Error: Invalid Job object provided.")
        return None
    try:
        status = job.status()
        return status
    except Exception as e:
        print(f"Error getting job status: {e}")
        return None

def get_job_result(job: Job, timeout: int | None = None) -> any:
    """
    Gets the result of a submitted job.

    Args:
        job: The Job object.
        timeout: Optional timeout in seconds to wait for the result.

    Returns:
        The job result, or None if an error or timeout occurs.
    """
    if not isinstance(job, Job):
        print("Error: Invalid Job object provided.")
        return None
    try:
        result = job.result(timeout=timeout)
        return result
    except TimeoutError:
        print(f"Timeout waiting for job result.")
        return None
    except RuntimeError as e:
        print(f"Runtime error getting job result: {e} (Job may have failed)")
        return None
    except Exception as e:
        print(f"Error getting job result: {e}")
        return None
