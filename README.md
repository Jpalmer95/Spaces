# Hugging Face Spaces Interaction Suite

This project provides tools to interact with Hugging Face Spaces, allowing users to discover, execute, and manage results from these Spaces locally. It offers both a Command-Line Interface (CLI) and a Graphical User Interface (GUI).

## Interfaces

*   **GUI (`gui.py`):** A comprehensive desktop application for a rich, interactive experience.
*   **CLI (`app.py`):** A scriptable interface for terminal-based operations.

## Features

### GUI (`gui.py`)

*   **Space Discovery:**
    *   Search for Hugging Face Spaces by task description.
    *   Sort results by likes, update date, etc.
    *   Manage a local list of favorite Spaces.
*   **Space Execution:**
    *   Load API details for a given Space ID (from manual input or favorites).
    *   Dynamically generates input fields based on parsed API parameters (supports text, numbers, booleans, files).
    *   Fallback to JSON input for complex or unparsable parameter structures.
    *   Run predictions (blocking) or submit jobs (non-blocking).
    *   Optionally save execution results and parameters to a local database.
*   **Results Library:**
    *   Browse and filter saved execution results (by Space ID, task keyword, output type).
    *   View detailed information for each result, including parameters and output.
    *   Supports rendering various output types:
        *   Text and JSON data.
        *   Images (displays common formats like PNG, JPEG).
        *   Opens other files (audio, video, generic files) or URLs using the system's default application.
    *   Add, edit, and save notes for each result.
    *   Delete unwanted results from the local library.
*   **Theme:** Modern, custom dark theme with blue and charcoal grey elements for comfortable usage.

### CLI (`app.py`)

*   (Details about CLI features can be expanded here if `app.py` is further developed or has existing distinct features to highlight beyond basic execution/discovery.)
*   Currently, `app.py` might serve as a basis or complementary tool for specific scripted interactions.

## Setup and Installation

1.  **Clone the Repository:**
    ```bash
    git clone <repository_url>
    cd <repository_directory>
    ```

2.  **Install Python Dependencies:**
    Ensure you have Python 3.10+ installed. Then, install the required packages:
    ```bash
    pip install -r requirements.txt
    ```

3.  **GUI System Dependencies (PyQt6):**
    The GUI application uses `PyQt6`. This requires Qt6 runtime libraries to be installed on your system.
    *   **Windows/macOS:** Typically, `pip install PyQt6` handles the necessary Qt libraries.
    *   **Linux:** You might need to install additional system packages. For Debian/Ubuntu-based systems, if you encounter issues running the GUI (e.g., errors related to Qt platform plugins like "xcb"), try installing the following:
        ```bash
        sudo apt-get update
        sudo apt-get install -y libxcb-cursor0 libxkbcommon-x11-0 libxcb-icccm4 libxcb-keysyms1 libxcb-render0 libxcb-image0 libxcb-shm0 libxcb-xfixes0 libegl1 libopengl0 libgl1
        ```
        In some headless environments or if display errors persist, you might also need a virtual framebuffer:
        ```bash
        sudo apt-get install -y xvfb
        ```
        Then run the GUI with `xvfb-run python gui.py`.

4.  **Database Initialization:**
    The first time you run the GUI or interact with features that use the results library, a local SQLite database file (`generated_content.db`) will be automatically created in the root directory to store your saved results and favorites.

## Running the Application

### GUI (`gui.py`)

To launch the graphical interface:
```bash
python gui.py
```
If on a headless Linux system, you might need:
```bash
xvfb-run python gui.py
```

### CLI (`app.py`)

The CLI provides various functions. Use `--help` to see available commands and options:
```bash
python app.py --help
```
**Example (CLI - assuming relevant functions are implemented in `app.py`):**
```bash
# Example: Find spaces related to 'text generation'
python app.py find-spaces --task "text generation" --limit 5

# Example: Add a space to favorites
python app.py add-favorite --space_id "user/my-cool-space"

# Example: Run a prediction (if app.py supports this directly)
# python app.py run-predict --space_id "user/my-cool-space" --api_name "/predict" --params '{"text": "Hello!"}'
```
*(Note: The CLI functionalities beyond basic `space_finder` and `results_manager` examples might need further implementation in `app.py` to match the GUI's execution capabilities.)*

## GUI Usage Overview

The GUI is organized into three main tabs:

*   **Space Discovery:**
    *   **Find Spaces:** Enter a task description (e.g., "image segmentation"), select sorting criteria, and set a limit for search results. Click "Search Spaces".
    *   **Search Results:** Matching Spaces will appear in the table. Select a row to enable the "Add Search Result to Favorites" button.
    *   **Favorite Spaces:** View your list of saved favorite Space IDs. Select a favorite and click "Remove Selected Favorite from List" to delete it. Use "Refresh Favorites List" to update.

*   **Space Execution:**
    *   **Space ID:** Enter a Space ID directly (e.g., `username/spacename`) or click "Load from Favorites" to choose one.
    *   **Load Space API:** Click this to fetch and display the API details of the Space.
    *   **API Details:** Shows the raw API information provided by the Space.
    *   **Parameters:** Input fields for the Space's API will be dynamically generated here based on the loaded API details. Fill them out. For file inputs, a "Browse" button will appear. If parameters are not parsed correctly, a "Fallback JSON" input field allows you to enter parameters as a JSON string.
    *   **API Name:** Specify the API endpoint to use (e.g., `/predict`, often pre-filled).
    *   **Execution Controls:**
        *   "Run Predict (Blocking)": Executes the Space and waits for the result.
        *   "Run Submit (Non-Blocking)": Submits a job to the Space (useful for long-running tasks).
        *   "Save to DB": Check this to save the execution parameters and output to the local Results Library. You'll need to provide a "DB Task Desc" and select a "DB Output Type".
    *   **Execution Output:** Displays the results from the Space execution or job status.

*   **Results Library:**
    *   **Filter Results:** Narrow down the list of saved results by Space ID, a keyword in the task description, or output type. Click "Filter Results".
    *   **Stored Results Table:** Shows the filtered list of results. Select a row to view its details on the right.
    *   **Pagination:** Use "Previous" and "Next" buttons to navigate through pages of results. Adjust "Per Page" to change how many results are shown.
    *   **Selected Result Details:**
        *   Displays metadata like ID, Space ID, timestamp, task description, and parameters.
        *   The **Output Data** section will attempt to display the content:
            *   Text and JSON are shown directly.
            *   Images are previewed.
            *   Other file types (audio, video, generic files) or URLs will show an "Open File/Media" button to launch them with your system's default application.
        *   **Notes:** Add or edit personal notes for the selected result. Click "Save Notes".
        *   **Delete Selected Result:** Removes the result from your local library (with confirmation).

The application features a dark theme with blue and charcoal grey accents for a visually comfortable experience. It supports a variety of input and output data types, including text, numbers, booleans, and files for Space execution, and can handle diverse outputs in the Results Library.
