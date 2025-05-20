import sqlite3
import json
from datetime import datetime

DB_NAME = 'generated_content.db'
TABLE_NAME = 'content_library'

def init_db():
    """
    Initializes the SQLite database.
    Creates the content_library table if it doesn't exist.
    """
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute(f'''
                CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    space_id TEXT NOT NULL,
                    task_description TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    output_type TEXT,
                    output_data TEXT NOT NULL,
                    parameters TEXT,
                    notes TEXT
                )
            ''')
            conn.commit()
            print(f"Database '{DB_NAME}' initialized and table '{TABLE_NAME}' created/ensured.")
    except sqlite3.Error as e:
        print(f"Error initializing database: {e}")

def _dict_factory(cursor, row):
    """Converts a database row to a dictionary."""
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    if 'parameters' in d and d['parameters']:
        try:
            d['parameters'] = json.loads(d['parameters'])
        except json.JSONDecodeError:
            print(f"Warning: Could not decode JSON parameters for row: {d.get('id')}")
            d['parameters'] = None # Or some other default
    return d

def add_content(space_id: str, task_description: str, output_type: str, output_data: str, parameters: dict, notes: str = None) -> int | None:
    """
    Adds a new content record to the database.

    Args:
        space_id: The ID of the Hugging Face Space.
        task_description: Description of the task.
        output_type: Type of the output (e.g., 'text', 'image_path').
        output_data: The generated content or path to it.
        parameters: Input parameters for the generation, stored as JSON.
        notes: Optional user notes.

    Returns:
        The ID of the newly inserted row, or None on error.
    """
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            params_json = json.dumps(parameters)
            cursor.execute(f'''
                INSERT INTO {TABLE_NAME} (space_id, task_description, output_type, output_data, parameters, notes, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (space_id, task_description, output_type, output_data, params_json, notes, datetime.now()))
            conn.commit()
            return cursor.lastrowid
    except sqlite3.Error as e:
        print(f"Error adding content: {e}")
        return None

def get_content_by_id(content_id: int) -> dict | None:
    """
    Fetches a content record by its ID.

    Args:
        content_id: The ID of the content to retrieve.

    Returns:
        A dictionary representing the record, or None if not found or on error.
    """
    try:
        with sqlite3.connect(DB_NAME) as conn:
            conn.row_factory = _dict_factory
            cursor = conn.cursor()
            cursor.execute(f"SELECT * FROM {TABLE_NAME} WHERE id = ?", (content_id,))
            record = cursor.fetchone()
            return record
    except sqlite3.Error as e:
        print(f"Error getting content by ID {content_id}: {e}")
        return None

def get_all_content(limit: int = 20, offset: int = 0) -> list[dict]:
    """
    Fetches all content records with pagination.

    Args:
        limit: Maximum number of records to return.
        offset: Number of records to skip.

    Returns:
        A list of dictionaries, where each dictionary is a record.
    """
    try:
        with sqlite3.connect(DB_NAME) as conn:
            conn.row_factory = _dict_factory
            cursor = conn.cursor()
            cursor.execute(f"SELECT * FROM {TABLE_NAME} ORDER BY timestamp DESC LIMIT ? OFFSET ?", (limit, offset))
            records = cursor.fetchall()
            return records
    except sqlite3.Error as e:
        print(f"Error getting all content: {e}")
        return []

def filter_content(output_type: str = None, space_id: str = None, task_keyword: str = None, limit: int = 20, offset: int = 0) -> list[dict]:
    """
    Filters content records based on criteria with pagination.

    Args:
        output_type: Filter by output type.
        space_id: Filter by Space ID.
        task_keyword: Filter by a keyword in the task description (uses LIKE).
        limit: Maximum number of records to return.
        offset: Number of records to skip.

    Returns:
        A list of matching records as dictionaries.
    """
    try:
        with sqlite3.connect(DB_NAME) as conn:
            conn.row_factory = _dict_factory
            cursor = conn.cursor()
            
            query = f"SELECT * FROM {TABLE_NAME} WHERE 1=1"
            params = []

            if output_type:
                query += " AND output_type = ?"
                params.append(output_type)
            if space_id:
                query += " AND space_id = ?"
                params.append(space_id)
            if task_keyword:
                query += " AND task_description LIKE ?"
                params.append(f"%{task_keyword}%")
            
            query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])
            
            cursor.execute(query, tuple(params))
            records = cursor.fetchall()
            return records
    except sqlite3.Error as e:
        print(f"Error filtering content: {e}")
        return []

def update_content_notes(content_id: int, notes: str) -> bool:
    """
    Updates the notes for a specific content record.

    Args:
        content_id: The ID of the content to update.
        notes: The new notes to set.

    Returns:
        True on success, False on error or if the record doesn't exist.
    """
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute(f"UPDATE {TABLE_NAME} SET notes = ? WHERE id = ?", (notes, content_id))
            conn.commit()
            return cursor.rowcount > 0
    except sqlite3.Error as e:
        print(f"Error updating notes for content ID {content_id}: {e}")
        return False

def delete_content(content_id: int) -> bool:
    """
    Deletes a content record by its ID.

    Args:
        content_id: The ID of the content to delete.

    Returns:
        True on success, False on error or if the record doesn't exist.
    """
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute(f"DELETE FROM {TABLE_NAME} WHERE id = ?", (content_id,))
            conn.commit()
            return cursor.rowcount > 0
    except sqlite3.Error as e:
        print(f"Error deleting content ID {content_id}: {e}")
        return False

if __name__ == '__main__':
    # Example Usage:
    init_db()

    # Add some content
    params1 = {"prompt": "A cat sitting on a mat", "steps": 20}
    content_id1 = add_content("user/cats_space", "Generate image of a cat", "image_path", "/path/to/cat.png", params1, "First attempt")
    if content_id1:
        print(f"Added content with ID: {content_id1}")

    params2 = {"text_input": "Translate this to French: Hello", "model": "t5-base"}
    content_id2 = add_content("org/translation_service", "Translate text to French", "text", "Bonjour", params2)
    if content_id2:
        print(f"Added content with ID: {content_id2}")

    # Get content by ID
    if content_id1:
        retrieved_content = get_content_by_id(content_id1)
        if retrieved_content:
            print(f"Retrieved content: {retrieved_content}")
            assert retrieved_content['parameters'] == params1 # Check JSON conversion

    # Get all content
    all_items = get_all_content(limit=5)
    print(f"All content (first 5): {all_items}")
    if all_items and all_items[0]['parameters']: # Assuming second item added is now first due to DESC order
         assert all_items[0]['parameters'] == params2

    # Filter content
    image_content = filter_content(output_type="image_path")
    print(f"Image content: {image_content}")
    if image_content:
        assert image_content[0]['parameters'] == params1

    french_translations = filter_content(task_keyword="French")
    print(f"French translation content: {french_translations}")
    if french_translations:
        assert french_translations[0]['parameters'] == params2
    
    # Update notes
    if content_id1:
        update_success = update_content_notes(content_id1, "Updated note: a very cute cat.")
        print(f"Note update success: {update_success}")
        if update_success:
            updated_item = get_content_by_id(content_id1)
            print(f"Updated item notes: {updated_item['notes']}")
            assert updated_item['notes'] == "Updated note: a very cute cat."

    # Delete content
    if content_id2:
        delete_success = delete_content(content_id2)
        print(f"Delete success for ID {content_id2}: {delete_success}")
        assert delete_success
        assert get_content_by_id(content_id2) is None
        
    # Clean up test db
    # import os
    # os.remove(DB_NAME)
    # print(f"Cleaned up database {DB_NAME}")
