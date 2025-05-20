import unittest
import sqlite3
import os
import json
from datetime import datetime

# Adjust the import path if your project structure requires it
# e.g., from .. import results_manager (if tests is a package)
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import results_manager

class TestResultsManager(unittest.TestCase):
    TEST_DB_NAME = 'test_generated_content.db'
    ORIGINAL_DB_NAME = None # To store the original DB_NAME

    @classmethod
    def setUpClass(cls):
        """
        Set up for all tests in the class.
        Store original DB_NAME and set it to TEST_DB_NAME.
        """
        cls.ORIGINAL_DB_NAME = results_manager.DB_NAME
        results_manager.DB_NAME = cls.TEST_DB_NAME

    @classmethod
    def tearDownClass(cls):
        """
        Tear down after all tests in the class.
        Restore original DB_NAME.
        """
        results_manager.DB_NAME = cls.ORIGINAL_DB_NAME
        if os.path.exists(cls.TEST_DB_NAME):
            os.remove(cls.TEST_DB_NAME) # Clean up at the very end

    def setUp(self):
        """
        Set up for each test method.
        Ensure the database file is deleted and re-initialized for a clean state.
        """
        if os.path.exists(self.TEST_DB_NAME):
            os.remove(self.TEST_DB_NAME)
        results_manager.init_db() # Initialize DB for each test

    def tearDown(self):
        """
        Tear down after each test method.
        Deletes the test database file.
        """
        if os.path.exists(self.TEST_DB_NAME):
            os.remove(self.TEST_DB_NAME)

    def test_01_init_db(self):
        """Test database initialization and table structure."""
        self.assertTrue(os.path.exists(self.TEST_DB_NAME), "Database file should be created.")
        
        try:
            conn = sqlite3.connect(self.TEST_DB_NAME)
            cursor = conn.cursor()
            cursor.execute(f"PRAGMA table_info({results_manager.TABLE_NAME})")
            columns_info = cursor.fetchall()
        finally:
            if conn:
                conn.close()

        self.assertTrue(len(columns_info) > 0, "Table should have columns.")
        
        expected_columns = {
            'id': 'INTEGER',
            'space_id': 'TEXT',
            'task_description': 'TEXT',
            'timestamp': 'DATETIME',
            'output_type': 'TEXT',
            'output_data': 'TEXT',
            'parameters': 'TEXT', # Stored as JSON string
            'notes': 'TEXT'
        }
        
        actual_columns = {col[1]: col[2] for col in columns_info}
        
        for col_name, col_type in expected_columns.items():
            self.assertIn(col_name, actual_columns, f"Column '{col_name}' should exist.")
            self.assertEqual(actual_columns[col_name], col_type, f"Column '{col_name}' should have type '{col_type}'.")
        self.assertIsNotNone(actual_columns.get('id'), "id column should be present")


    def test_02_add_and_get_content(self):
        """Test adding content and retrieving it by ID."""
        params = {"prompt": "test prompt", "size": 256}
        content_id = results_manager.add_content(
            space_id="test/space",
            task_description="Generate test image",
            output_type="image_path",
            output_data="/path/to/test.png",
            parameters=params,
            notes="Initial test content"
        )
        self.assertIsInstance(content_id, int, "add_content should return an integer ID.")
        
        retrieved_content = results_manager.get_content_by_id(content_id)
        self.assertIsNotNone(retrieved_content, "Should retrieve content by ID.")
        
        self.assertEqual(retrieved_content['space_id'], "test/space")
        self.assertEqual(retrieved_content['task_description'], "Generate test image")
        self.assertEqual(retrieved_content['output_type'], "image_path")
        self.assertEqual(retrieved_content['output_data'], "/path/to/test.png")
        self.assertEqual(retrieved_content['parameters'], params, "Parameters should match.")
        self.assertEqual(retrieved_content['notes'], "Initial test content")
        self.assertIn('timestamp', retrieved_content) # Check timestamp exists

        # Test adding content without notes
        content_id_no_notes = results_manager.add_content(
            space_id="test/space2",
            task_description="Another task",
            output_type="text",
            output_data="Some text output",
            parameters={"model": "gpt-basic"}
        )
        self.assertIsInstance(content_id_no_notes, int)
        retrieved_no_notes = results_manager.get_content_by_id(content_id_no_notes)
        self.assertIsNotNone(retrieved_no_notes)
        self.assertIsNone(retrieved_no_notes['notes'], "Notes should be None if not provided.")

    def test_03_get_all_content(self):
        """Test retrieving all content with pagination."""
        params = {"p":1}
        results_manager.add_content("s1", "t1", "text", "d1", params)
        results_manager.add_content("s2", "t2", "image", "d2", params)
        results_manager.add_content("s3", "t3", "audio", "d3", params)
        
        all_content = results_manager.get_all_content()
        self.assertIsInstance(all_content, list)
        self.assertEqual(len(all_content), 3, "Should retrieve all 3 items.")

        # Test limit
        limited_content = results_manager.get_all_content(limit=1)
        self.assertEqual(len(limited_content), 1)
        # Items are ordered by timestamp DESC
        self.assertEqual(limited_content[0]['space_id'], "s3") 

        # Test offset
        offset_content = results_manager.get_all_content(limit=1, offset=1)
        self.assertEqual(len(offset_content), 1)
        self.assertEqual(offset_content[0]['space_id'], "s2")

        # Test limit and offset together
        paginated_content = results_manager.get_all_content(limit=2, offset=1)
        self.assertEqual(len(paginated_content), 2)
        self.assertEqual(paginated_content[0]['space_id'], "s2")
        self.assertEqual(paginated_content[1]['space_id'], "s1")
        
        # Test empty table
        self.tearDown() # Clear DB
        self.setUp()    # Re-init empty DB
        empty_content = results_manager.get_all_content()
        self.assertEqual(len(empty_content), 0)


    def test_04_filter_content(self):
        """Test filtering content by various criteria."""
        p = {"p":1}
        results_manager.add_content("space/images", "Generate cat image", "image_path", "/img/cat.png", p)
        results_manager.add_content("space/images", "Generate dog image", "image_path", "/img/dog.png", p)
        results_manager.add_content("space/text", "Translate English to French", "text", "Bonjour", p)
        results_manager.add_content("space/audio", "Generate speech from text", "audio_path", "/audio/speech.wav", p)

        # Filter by output_type
        image_content = results_manager.filter_content(output_type="image_path")
        self.assertEqual(len(image_content), 2)
        self.assertTrue(all(item['output_type'] == "image_path" for item in image_content))

        # Filter by space_id
        text_space_content = results_manager.filter_content(space_id="space/text")
        self.assertEqual(len(text_space_content), 1)
        self.assertEqual(text_space_content[0]['output_type'], "text")

        # Filter by task_keyword
        cat_content = results_manager.filter_content(task_keyword="cat")
        self.assertEqual(len(cat_content), 1)
        self.assertEqual(cat_content[0]['task_description'], "Generate cat image")
        
        generate_content = results_manager.filter_content(task_keyword="Generate")
        self.assertEqual(len(generate_content), 3) # cat, dog, speech

        # Filter by combination
        image_cat_content = results_manager.filter_content(output_type="image_path", task_keyword="cat")
        self.assertEqual(len(image_cat_content), 1)
        self.assertEqual(image_cat_content[0]['space_id'], "space/images")
        self.assertEqual(image_cat_content[0]['task_description'], "Generate cat image")

        # Filter with limit and offset
        filtered_limited = results_manager.filter_content(task_keyword="Generate", limit=1, offset=1)
        self.assertEqual(len(filtered_limited), 1)
        # Order is DESC by timestamp, so "Generate speech" then "Generate dog" then "Generate cat"
        # The exact item depends on insertion order if timestamps are very close.
        # For this test, we assume they are inserted in the order above.
        # "Generate speech" (s4), "Translate" (s3), "Generate dog" (s2), "Generate cat" (s1)
        # With "Generate" keyword, result is s4, s2, s1. Offset 1, limit 1 -> s2
        self.assertEqual(filtered_limited[0]['task_description'], "Generate dog image")
        
        # No results
        no_match_content = results_manager.filter_content(task_keyword="nonexistent")
        self.assertEqual(len(no_match_content), 0)

    def test_05_update_content_notes(self):
        """Test updating notes for a content item."""
        content_id = results_manager.add_content("s", "t", "text", "d", {}, "Original notes")
        self.assertIsNotNone(content_id)
        
        new_notes = "Updated notes for test."
        update_success = results_manager.update_content_notes(content_id, new_notes)
        self.assertTrue(update_success, "Updating notes should succeed.")
        
        updated_content = results_manager.get_content_by_id(content_id)
        self.assertEqual(updated_content['notes'], new_notes, "Notes should be updated.")

        # Test updating non-existent content
        non_existent_id = 99999
        update_fail = results_manager.update_content_notes(non_existent_id, "some notes")
        self.assertFalse(update_fail, "Updating notes for non-existent ID should fail.")

    def test_06_delete_content(self):
        """Test deleting a content item."""
        content_id = results_manager.add_content("s", "t", "text", "d", {})
        self.assertIsNotNone(content_id)
        
        delete_success = results_manager.delete_content(content_id)
        self.assertTrue(delete_success, "Deleting content should succeed.")
        
        deleted_content = results_manager.get_content_by_id(content_id)
        self.assertIsNone(deleted_content, "Content should be None after deletion.")

        # Test deleting non-existent content
        non_existent_id = 99999
        delete_fail = results_manager.delete_content(non_existent_id)
        self.assertFalse(delete_fail, "Deleting non-existent ID should fail.")

    def test_07_add_content_parameter_handling(self):
        """Test handling of complex parameters (JSON serialization/deserialization)."""
        complex_params = {
            "prompt": "A complex scene",
            "settings": {
                "resolution": "1024x1024",
                "steps": 50,
                "sampler": "Euler a"
            },
            "negative_prompts": ["blurry", "disfigured", "low quality"],
            "model_version": 1.5
        }
        content_id = results_manager.add_content(
            space_id="test/complex_params_space",
            task_description="Generate with complex settings",
            output_type="image_path",
            output_data="/path/to/complex.png",
            parameters=complex_params
        )
        self.assertIsInstance(content_id, int)
        
        retrieved_content = results_manager.get_content_by_id(content_id)
        self.assertIsNotNone(retrieved_content)
        self.assertEqual(retrieved_content['parameters'], complex_params, "Complex parameters should be stored and retrieved correctly.")

        # Test with empty parameters
        content_id_empty_params = results_manager.add_content("s", "t", "text", "d", {})
        retrieved_empty_params = results_manager.get_content_by_id(content_id_empty_params)
        self.assertEqual(retrieved_empty_params['parameters'], {}, "Empty parameters should be handled.")
        
        # Test with parameters being None (should be stored as null in JSON, retrieved as None or empty dict by _dict_factory)
        # Current _dict_factory converts null JSON to None. If it was an empty dict, adjust assertion.
        content_id_none_params = results_manager.add_content("s", "t", "text", "d", None) # type: ignore
        retrieved_none_params = results_manager.get_content_by_id(content_id_none_params)
        # The add_content function json.dumps(parameters), so None becomes "null"
        # The _dict_factory json.loads("null") which becomes None.
        self.assertIsNone(retrieved_none_params['parameters'], "None parameters should be handled and retrieved as None.")


if __name__ == '__main__':
    unittest.main()
