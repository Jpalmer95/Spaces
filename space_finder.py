import json
import os
from huggingface_hub import HfApi, SpaceInfo # Ensure SpaceInfo is imported

FAVORITES_FILE = 'favorite_spaces.json'

def find_spaces(task_description: str, sort_by: str = 'likes', limit: int = 10) -> list[SpaceInfo]:
    """
    Finds Hugging Face Spaces based on a task description.

    Args:
        task_description: The description of the task to search for.
        sort_by: The field to sort the results by (e.g., 'likes', 'updatedAt'). Defaults to 'likes'.
        limit: The maximum number of results to return. Defaults to 10.

    Returns:
        A list of SpaceInfo objects matching the search criteria.
    """
    api = HfApi()
    spaces = api.list_spaces(
        search=task_description,
        sort=sort_by,
        direction=-1,  # Descending order
        limit=limit
    )
    return spaces

def add_to_favorites(space_id: str):
    """
    Adds a Hugging Face Space to the list of favorites.
    Adds a Hugging Face Space to the list of favorites.

    Args:
        space_id: The ID of the Space to add to favorites.
    """
    favorites = []
    if os.path.exists(FAVORITES_FILE):
        try:
            with open(FAVORITES_FILE, 'r') as f:
                content = f.read()
                if content:
                    favorites = json.loads(content)
        except FileNotFoundError:
            pass  # File not found, will create it later
        except json.JSONDecodeError:
            print(f"Warning: Could not decode JSON from {FAVORITES_FILE}. Starting with an empty list.")
            favorites = []

    if space_id not in favorites:
        favorites.append(space_id)
        try:
            with open(FAVORITES_FILE, 'w') as f:
                json.dump(favorites, f, indent=4)
        except IOError:
            print(f"Error: Could not write to {FAVORITES_FILE}.")
    else:
        print(f"Info: Space '{space_id}' is already in favorites.")

def get_favorite_spaces() -> list[str]:
    """
    Retrieves the list of favorite Hugging Face Space IDs.

    Returns:
        A list of favorite Space IDs. Returns an empty list if the favorites file
        doesn't exist, is empty, or if there's an error reading/parsing it.
    """
    if not os.path.exists(FAVORITES_FILE):
        return []
    try:
        with open(FAVORITES_FILE, 'r') as f:
            content = f.read()
            if not content:
                return []
            favorites = json.loads(content)
            return favorites
    except FileNotFoundError:
        return []
    except json.JSONDecodeError:
        print(f"Warning: Could not decode JSON from {FAVORITES_FILE}. Returning empty list.")
        return []
    except IOError:
        print(f"Error: Could not read from {FAVORITES_FILE}. Returning empty list.")
        return []
