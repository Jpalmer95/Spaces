import unittest
from unittest.mock import patch, MagicMock, mock_open
import os
import json
import sys

# Adjust the import path if your project structure requires it
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import space_finder
from space_finder import find_spaces, add_to_favorites, get_favorite_spaces
from huggingface_hub import SpaceInfo # Actual SpaceInfo might be complex, using MagicMock for attributes

# Define a global for the test favorites file to be used in patching
TEST_FAVORITES_FILE_PATH = 'test_favorite_spaces.json'

@patch('space_finder.FAVORITES_FILE', TEST_FAVORITES_FILE_PATH)
class TestSpaceFinder(unittest.TestCase):

    def setUp(self):
        """
        Set up for each test method.
        Ensure the test favorites file is clean before each test.
        """
        # The @patch at class level handles redirecting space_finder.FAVORITES_FILE
        # We just need to ensure the file itself is clean
        if os.path.exists(TEST_FAVORITES_FILE_PATH):
            os.remove(TEST_FAVORITES_FILE_PATH)

    def tearDown(self):
        """
        Tear down after each test method.
        If the test favorites file exists, remove it.
        """
        if os.path.exists(TEST_FAVORITES_FILE_PATH):
            os.remove(TEST_FAVORITES_FILE_PATH)

    @patch('space_finder.HfApi')
    def test_find_spaces_success(self, mock_hf_api_constructor):
        """Test find_spaces successfully retrieves and returns space information."""
        mock_api_instance = mock_hf_api_constructor.return_value

        # Create sample SpaceInfo-like objects using MagicMock
        # These need to have the attributes that find_spaces accesses (if any for printing/returning)
        # For now, find_spaces just returns them, so they can be simple MagicMocks
        sample_space_info_1 = MagicMock(spec=SpaceInfo, id='user/space1', author='user1', likes=100, cardData={'tags': ['tag1']})
        sample_space_info_2 = MagicMock(spec=SpaceInfo, id='user/space2', author='user2', likes=200, cardData={'tags': ['tag2']})
        mock_api_instance.list_spaces.return_value = [sample_space_info_1, sample_space_info_2]

        result = find_spaces(task_description='test task', sort_by='updatedAt', limit=5)

        mock_api_instance.list_spaces.assert_called_once_with(
            search='test task',
            sort='updatedAt',
            direction=-1,
            limit=5
        )
        self.assertEqual(result, [sample_space_info_1, sample_space_info_2])

    @patch('space_finder.HfApi')
    def test_find_spaces_api_error(self, mock_hf_api_constructor):
        """Test find_spaces handles API errors by re-raising them (current behavior)."""
        mock_api_instance = mock_hf_api_constructor.return_value
        mock_api_instance.list_spaces.side_effect = Exception("API Error")

        with self.assertRaisesRegex(Exception, "API Error"):
            find_spaces(task_description='test task')
        
        mock_api_instance.list_spaces.assert_called_once_with(
            search='test task',
            sort='likes', # Default sort
            direction=-1,
            limit=10      # Default limit
        )

    def test_add_to_favorites_new(self):
        """Test adding a new space to favorites."""
        add_to_favorites('user/space1')
        self.assertTrue(os.path.exists(TEST_FAVORITES_FILE_PATH))
        with open(TEST_FAVORITES_FILE_PATH, 'r') as f:
            favorites = json.load(f)
        self.assertEqual(favorites, ['user/space1'])

    def test_add_to_favorites_existing_and_duplicate(self):
        """Test adding multiple spaces and handling duplicates."""
        add_to_favorites('user/space1')
        add_to_favorites('user/space2')
        add_to_favorites('user/space1')  # Duplicate

        with open(TEST_FAVORITES_FILE_PATH, 'r') as f:
            favorites = json.load(f)
        self.assertEqual(favorites, ['user/space1', 'user/space2'])

    def test_get_favorite_spaces_empty(self):
        """Test getting favorites when the file doesn't exist."""
        favorites = get_favorite_spaces()
        self.assertEqual(favorites, [])

    def test_get_favorite_spaces_with_data(self):
        """Test getting favorites from an existing file."""
        expected_favorites = ['user/space1', 'user/space3']
        with open(TEST_FAVORITES_FILE_PATH, 'w') as f:
            json.dump(expected_favorites, f)

        favorites = get_favorite_spaces()
        self.assertEqual(favorites, expected_favorites)

    def test_get_favorite_spaces_invalid_json(self):
        """Test getting favorites from a file with invalid JSON."""
        with open(TEST_FAVORITES_FILE_PATH, 'w') as f:
            f.write("this is not json")
        
        # The current implementation prints a warning and returns an empty list
        with patch('builtins.print') as mock_print: # Suppress print warning during test
            favorites = get_favorite_spaces()
            self.assertEqual(favorites, [])
            mock_print.assert_any_call(f"Warning: Could not decode JSON from {TEST_FAVORITES_FILE_PATH}. Returning empty list.")


    @patch('builtins.open', new_callable=mock_open)
    def test_add_to_favorites_io_error_write(self, mock_file_open):
        """Test add_to_favorites handles IOError gracefully during write."""
        # Make open raise IOError only on write ('w' or 'a' mode)
        def open_side_effect(path, mode='r', *args, **kwargs):
            if 'w' in mode or 'a' in mode : # For write or append
                raise IOError("Mocked file write error")
            # For read, return a valid mock file object (though not strictly needed for this add_to_favorites test)
            return mock_open(read_data='[]')(path, mode, *args, **kwargs)

        mock_file_open.side_effect = open_side_effect
        
        # We expect add_to_favorites to print an error message
        with patch('builtins.print') as mock_print:
            add_to_favorites('user/space1')
            # Check if an error message was printed
            mock_print.assert_any_call(f"Error: Could not write to {TEST_FAVORITES_FILE_PATH}.")
            # Ensure the file was not created or is empty if create was attempted before error
            self.assertFalse(os.path.exists(TEST_FAVORITES_FILE_PATH) or os.path.getsize(TEST_FAVORITES_FILE_PATH) == 0)


    @patch('builtins.open', side_effect=IOError("Mocked file read error"))
    def test_get_favorite_spaces_io_error_read(self, mock_file_open_error):
        """Test get_favorite_spaces handles IOError gracefully during read."""
        # Ensure a file exists so 'open' is attempted
        with open(TEST_FAVORITES_FILE_PATH, 'w') as f:
            json.dump(['user/dummy'], f)

        # We expect get_favorite_spaces to print an error and return an empty list
        with patch('builtins.print') as mock_print:
            favorites = get_favorite_spaces()
            self.assertEqual(favorites, [])
            mock_print.assert_any_call(f"Error: Could not read from {TEST_FAVORITES_FILE_PATH}. Returning empty list.")


if __name__ == '__main__':
    unittest.main()
