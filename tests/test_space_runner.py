import unittest
from unittest.mock import patch, MagicMock, PropertyMock
import io
import sys
import os

# Adjust the import path if your project structure requires it
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import space_runner # Import the module to be tested
from space_runner import (
    get_space_api_details,
    run_space_predict,
    run_space_submit,
    get_job_status,
    get_job_result
)

# Import Gradio client components with alias if needed, and for type hinting
from gradio_client import Client as GradioClient # Aliased as GradioClient
from gradio_client.client import Job, Status     # For type hinting and creating mock Job instances

class TestSpaceRunner(unittest.TestCase):

    # --- Tests for get_space_api_details ---
    @patch('space_runner.Client') # This targets gradio_client.Client as used in space_runner.py
    @patch('space_runner.io.StringIO')
    def test_get_space_api_details_success(self, mock_string_io, mock_gradio_client_constructor):
        """Test get_space_api_details successfully captures and returns API details."""
        mock_client_instance = mock_gradio_client_constructor.return_value
        mock_string_io_instance = mock_string_io.return_value
        mock_string_io_instance.getvalue.return_value = "Fake API Details"
        
        original_stdout = sys.stdout # Store original stdout

        api_details = get_space_api_details("test/space")

        mock_gradio_client_constructor.assert_called_once_with("test/space")
        mock_client_instance.view_api.assert_called_once_with(all_endpoints=True)
        self.assertEqual(api_details, "Fake API Details")
        self.assertEqual(sys.stdout, original_stdout, "sys.stdout should be restored.")

    @patch('space_runner.Client')
    def test_get_space_api_details_client_error(self, mock_gradio_client_constructor):
        """Test get_space_api_details returns None on Client initialization error."""
        mock_gradio_client_constructor.side_effect = Exception("Client init error")
        
        with patch('builtins.print') as mock_print: # Suppress print
            api_details = get_space_api_details("test/space")
        
        self.assertIsNone(api_details)
        mock_print.assert_any_call("Error initializing client for Space 'test/space': Client init error")

    @patch('space_runner.Client')
    @patch('space_runner.io.StringIO')
    def test_get_space_api_details_view_api_error(self, mock_string_io, mock_gradio_client_constructor):
        """Test get_space_api_details returns None if view_api raises an error."""
        mock_client_instance = mock_gradio_client_constructor.return_value
        mock_client_instance.view_api.side_effect = Exception("view_api error")
        
        original_stdout = sys.stdout
        with patch('builtins.print') as mock_print: # Suppress print
            api_details = get_space_api_details("test/space")
        
        self.assertIsNone(api_details)
        self.assertEqual(sys.stdout, original_stdout, "sys.stdout should be restored even on error.")
        mock_print.assert_any_call("Error fetching API details for Space 'test/space': view_api error")

    # --- Tests for run_space_predict ---
    @patch('space_runner.Client')
    def test_run_space_predict_success(self, mock_gradio_client_constructor):
        """Test run_space_predict successfully calls predict and returns result."""
        mock_client_instance = mock_gradio_client_constructor.return_value
        mock_client_instance.predict.return_value = "Prediction Result"

        result = run_space_predict("test/space", "/predict", "param1", kwarg1="value1")

        mock_gradio_client_constructor.assert_called_once_with("test/space")
        mock_client_instance.predict.assert_called_once_with("param1", kwarg1="value1", api_name="/predict")
        self.assertEqual(result, "Prediction Result")

    @patch('space_runner.Client')
    def test_run_space_predict_api_error(self, mock_gradio_client_constructor):
        """Test run_space_predict returns None on API error during predict."""
        mock_client_instance = mock_gradio_client_constructor.return_value
        mock_client_instance.predict.side_effect = Exception("API Error")

        with patch('builtins.print') as mock_print: # Suppress print
            result = run_space_predict("test/space", "/predict")
        
        self.assertIsNone(result)
        mock_print.assert_any_call("Error during prediction for Space 'test/space', API '/predict': API Error")


    # --- Tests for run_space_submit ---
    @patch('space_runner.Client')
    def test_run_space_submit_success(self, mock_gradio_client_constructor):
        """Test run_space_submit successfully calls submit and returns a Job."""
        mock_client_instance = mock_gradio_client_constructor.return_value
        mock_job_instance = MagicMock(spec=Job) # Create a mock Job object
        mock_client_instance.submit.return_value = mock_job_instance

        job = run_space_submit("test/space", "/submit", "param1", kwarg2="value2")

        mock_gradio_client_constructor.assert_called_once_with("test/space")
        mock_client_instance.submit.assert_called_once_with("param1", kwarg2="value2", api_name="/submit")
        self.assertEqual(job, mock_job_instance)

    @patch('space_runner.Client')
    def test_run_space_submit_api_error(self, mock_gradio_client_constructor):
        """Test run_space_submit returns None on API error during submit."""
        mock_client_instance = mock_gradio_client_constructor.return_value
        mock_client_instance.submit.side_effect = Exception("API Error")

        with patch('builtins.print') as mock_print: # Suppress print
            job = run_space_submit("test/space", "/submit")
        
        self.assertIsNone(job)
        mock_print.assert_any_call("Error submitting job to Space 'test/space', API '/submit': API Error")

    # --- Tests for get_job_status ---
    def test_get_job_status_success(self):
        """Test get_job_status returns status from a Job object."""
        mock_job = MagicMock(spec=Job)
        mock_status_instance = MagicMock(spec=Status)
        # Example: mock_status_instance.code = "PROCESSING" # if your code uses attributes
        mock_job.status.return_value = mock_status_instance

        status_result = get_job_status(mock_job)
        
        mock_job.status.assert_called_once()
        self.assertEqual(status_result, mock_status_instance)

    def test_get_job_status_error(self):
        """Test get_job_status returns None if job.status() raises an error."""
        mock_job = MagicMock(spec=Job)
        mock_job.status.side_effect = Exception("Status Error")

        with patch('builtins.print') as mock_print: # Suppress print
            status_result = get_job_status(mock_job)
        
        self.assertIsNone(status_result)
        mock_print.assert_any_call("Error getting job status: Status Error")

    def test_get_job_status_invalid_job_object(self):
        """Test get_job_status returns None for invalid job object."""
        with patch('builtins.print') as mock_print:
            status = get_job_status("not_a_job_object") # type: ignore
        self.assertIsNone(status)
        mock_print.assert_any_call("Error: Invalid Job object provided.")


    # --- Tests for get_job_result ---
    def test_get_job_result_success(self):
        """Test get_job_result returns output from a Job object."""
        mock_job = MagicMock(spec=Job)
        mock_job.result.return_value = "Job Output"

        result = get_job_result(mock_job)
        mock_job.result.assert_called_once_with(timeout=None)
        self.assertEqual(result, "Job Output")

    def test_get_job_result_success_with_timeout(self):
        """Test get_job_result with timeout parameter."""
        mock_job = MagicMock(spec=Job)
        mock_job.result.return_value = "Job Output With Timeout"

        result = get_job_result(mock_job, timeout=30)
        mock_job.result.assert_called_once_with(timeout=30)
        self.assertEqual(result, "Job Output With Timeout")

    def test_get_job_result_timeout_error(self):
        """Test get_job_result returns None on TimeoutError."""
        mock_job = MagicMock(spec=Job)
        mock_job.result.side_effect = TimeoutError("Timeout")

        with patch('builtins.print') as mock_print: # Suppress print
            result = get_job_result(mock_job)
        
        self.assertIsNone(result)
        mock_print.assert_any_call("Timeout waiting for job result.")

    def test_get_job_result_runtime_error(self):
        """Test get_job_result returns None on RuntimeError (e.g., job failed)."""
        mock_job = MagicMock(spec=Job)
        mock_job.result.side_effect = RuntimeError("Job Failed")

        with patch('builtins.print') as mock_print: # Suppress print
            result = get_job_result(mock_job)
        
        self.assertIsNone(result)
        mock_print.assert_any_call("Runtime error getting job result: Job Failed (Job may have failed)")

    def test_get_job_result_other_error(self):
        """Test get_job_result returns None on other exceptions."""
        mock_job = MagicMock(spec=Job)
        mock_job.result.side_effect = ValueError("Some other error") # Different from Timeout/Runtime

        with patch('builtins.print') as mock_print:
            result = get_job_result(mock_job)
        
        self.assertIsNone(result)
        mock_print.assert_any_call("Error getting job result: Some other error")

    def test_get_job_result_invalid_job_object(self):
        """Test get_job_result returns None for invalid job object."""
        with patch('builtins.print') as mock_print:
            result = get_job_result("not_a_job_object") # type: ignore
        self.assertIsNone(result)
        mock_print.assert_any_call("Error: Invalid Job object provided.")


if __name__ == '__main__':
    unittest.main()
