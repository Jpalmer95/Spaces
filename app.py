import argparse
import json
import sys # For sys.exit
import os # For checking file paths in parse_run_params
from gradio_client import handle_file # For parse_run_params

# Import from project modules
try:
    import space_finder
    import space_runner
    import results_manager
except ModuleNotFoundError:
    print("Error: One or more required modules (space_finder, space_runner, results_manager) not found.")
    print("Ensure they are in the same directory as app.py or in PYTHONPATH.")
    sys.exit(1)

# Helper function to parse parameters for run commands
def parse_run_params(params_list: list[str] | None) -> tuple[list, dict]:
    """
    Parses a list of strings into positional and keyword arguments.
    Handles file paths using gradio_client.handle_file.
    Attempts to JSON decode values, otherwise keeps them as strings.
    """
    args_out = []
    kwargs_out = {}
    if not params_list:
        return args_out, kwargs_out

    for item in params_list:
        if '=' in item:
            key, value = item.split('=', 1)
            # Check if value is a path to a file (basic check)
            # Common extensions, can be expanded
            if isinstance(value, str) and any(value.endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.gif', '.wav', '.mp3', '.txt', '.json', '.csv', '.glb', '.gltf', '.mp4', '.avi', '.mov']):
                if os.path.exists(value):
                    kwargs_out[key] = handle_file(value)
                else:
                    print(f"Warning: File path '{value}' for key '{key}' does not exist. Passing as string.")
                    kwargs_out[key] = value # Pass as string if file not found
            else:
                try:
                    # Try to load as JSON (for numbers, booleans, actual JSON objects/arrays)
                    kwargs_out[key] = json.loads(value)
                except json.JSONDecodeError:
                    # If not JSON, keep as string
                    kwargs_out[key] = value
        else:
            # Positional argument, try to JSON decode, else string
            try:
                args_out.append(json.loads(item))
            except json.JSONDecodeError:
                args_out.append(item)
    return args_out, kwargs_out

def handle_search_spaces(args):
    """Handles the 'search' command."""
    try:
        print(f"Searching for Spaces with task: '{args.task_description}', sort_by: {args.sort_by}, limit: {args.limit}")
        hf_token = os.environ.get("HF_TOKEN")
        spaces = space_finder.find_spaces(
            task_description=args.task_description,
            sort_by=args.sort_by,
            limit=args.limit,
            hf_token=hf_token
        )
        if spaces:
            print("Found Spaces:")
            for space in spaces:
                # Assuming SpaceInfo object has these attributes, adjust if necessary
                print(f"  ID: {space.id}, Author: {space.author}, Likes: {space.likes}, Task: {getattr(space, 'pipeline_tag', 'N/A')}")
        else:
            print("No Spaces found matching your criteria.")
    except Exception as e:
        print(f"Error searching Spaces: {e}")

def handle_favorites_add(args):
    """Handles the 'favorites add' command."""
    try:
        space_finder.add_to_favorites(args.space_id)
        print(f"Space '{args.space_id}' added to favorites (if not already present).")
    except Exception as e:
        print(f"Error adding Space to favorites: {e}")

def handle_favorites_list(args):
    """Handles the 'favorites list' command."""
    try:
        favorites = space_finder.get_favorite_spaces()
        if favorites:
            print("Favorite Spaces:")
            for space_id in favorites:
                print(f"  - {space_id}")
        else:
            print("No favorite Spaces found.")
    except Exception as e:
        print(f"Error listing favorite Spaces: {e}")

def handle_run_info(args):
    """Handles the 'run info' command."""
    try:
        print(f"Fetching API details for Space: {args.space_id}")
        hf_token = os.environ.get("HF_TOKEN")
        api_details = space_runner.get_space_api_details(args.space_id, hf_token=hf_token)
        if api_details:
            print("API Details:")
            print(api_details) # Already formatted string
        else:
            print(f"Could not retrieve API details for Space '{args.space_id}'.")
    except Exception as e:
        print(f"Error fetching API details: {e}")

# --- Run Command Handlers ---
def handle_run_predict(args):
    """Handles the 'run predict' command."""
    try:
        print(f"Preparing to run prediction for Space: {args.space_id}, API: {args.api_name}")
        pos_args, kw_args = parse_run_params(args.params)
        
        print(f"Parsed positional params: {pos_args}")
        print(f"Parsed keyword params: {kw_args}")

        hf_token = os.environ.get("HF_TOKEN")
        prediction_result = space_runner.run_space_predict(args.space_id, args.api_name, *pos_args, **kw_args, hf_token=hf_token)

        if prediction_result is not None:
            print("\nPrediction Result:")
            # If result is a file path (string) and exists, indicate it's a file
            if isinstance(prediction_result, str) and os.path.exists(prediction_result):
                 print(f"Output (file): {prediction_result}")
            else:
                try:
                    # Try to pretty print if it's JSON-like
                    print(json.dumps(prediction_result, indent=2))
                except (TypeError, OverflowError): # Handle non-serializable types if any
                    print(prediction_result)
            
            # Save to results database if output_type_for_db is provided
            if args.output_type_for_db:
                task_desc_for_db = args.task_desc if args.task_desc else args.space_id
                # Determine output_data for DB: if it's a file path string, store that. Otherwise, store the direct result.
                output_data_for_db = prediction_result
                if not (isinstance(prediction_result, str) and os.path.exists(prediction_result)):
                    # If not a file path, try to serialize complex objects to string for DB
                    if not isinstance(prediction_result, (str, int, float, bool)):
                        try:
                            output_data_for_db = json.dumps(prediction_result)
                        except Exception as e:
                            print(f"Warning: Could not serialize prediction result to JSON for DB: {e}. Storing as string.")
                            output_data_for_db = str(prediction_result)
                
                print(f"\nSaving result to database with output type: {args.output_type_for_db}...")
                content_id = results_manager.add_content(
                    space_id=args.space_id,
                    task_description=task_desc_for_db,
                    output_type=args.output_type_for_db,
                    output_data=output_data_for_db,
                    parameters=kw_args if kw_args else dict(zip([f"arg{i}" for i in range(len(pos_args))], pos_args)), # Store params used
                    notes="Generated via CLI 'run predict'"
                )
                if content_id:
                    print(f"Result saved with ID: {content_id}")
                else:
                    print("Failed to save result to database.")
        else:
            print("Prediction failed or returned None.")
    except Exception as e:
        print(f"Error running prediction: {e}")

def handle_run_submit(args):
    """Handles the 'run submit' command."""
    try:
        print(f"Preparing to submit job for Space: {args.space_id}, API: {args.api_name}")
        pos_args, kw_args = parse_run_params(args.params)

        print(f"Parsed positional params: {pos_args}")
        print(f"Parsed keyword params: {kw_args}")

        hf_token = os.environ.get("HF_TOKEN")
        job = space_runner.run_space_submit(args.space_id, args.api_name, *pos_args, **kw_args, hf_token=hf_token)

        if job:
            # Gradio Job object doesn't have a persistent ID string readily available without internal knowledge.
            # We'll just print the job object representation and a note.
            print(f"\nJob submitted successfully: {job}")
            print("Note: Job status and results for submitted jobs need to be handled programmatically using the returned Job object.")
            print("This CLI does not currently support tracking asynchronous jobs across sessions.")
        else:
            print("Job submission failed or returned None.")
    except Exception as e:
        print(f"Error submitting job: {e}")

# --- Results Command Handlers ---
def handle_results_list(args):
    """Handles the 'results list' command."""
    try:
        print(f"Fetching results with limit: {args.limit}, offset: {args.offset}")
        results = results_manager.get_all_content(limit=args.limit, offset=args.offset)
        if results:
            print("Generated Content:")
            for result in results:
                 print(f"  ID: {result['id']}, Space: {result['space_id']}, Type: {result['output_type']}, Task: {result['task_description'][:50]}..., Timestamp: {result['timestamp']}")
        else:
            print("No results found.")
    except Exception as e:
        print(f"Error listing results: {e}")

def handle_results_add(args):
    """Handles the 'results add' command."""
    try:
        params_dict = {}
        if args.params_json:
            try:
                params_dict = json.loads(args.params_json)
            except json.JSONDecodeError:
                print(f"Error: Invalid JSON string for --params_json: {args.params_json}")
                return

        print(f"Adding content: Space ID '{args.space_id}', Task '{args.task}', Type '{args.type}', Data '{args.data[:100]}...'")
        content_id = results_manager.add_content(
            space_id=args.space_id,
            task_description=args.task,
            output_type=args.type,
            output_data=args.data,
            parameters=params_dict,
            notes=args.notes
        )
        if content_id:
            print(f"Content added successfully with ID: {content_id}")
        else:
            print("Failed to add content.")
    except Exception as e:
        print(f"Error adding result: {e}")

def handle_results_view(args):
    """Handles the 'results view' command."""
    try:
        print(f"Fetching result with ID: {args.content_id}")
        result = results_manager.get_content_by_id(args.content_id)
        if result:
            print("Result Details:")
            print(json.dumps(result, indent=2)) # Pretty print the dictionary
        else:
            print(f"No result found with ID: {args.content_id}")
    except Exception as e:
        print(f"Error viewing result: {e}")

def handle_results_filter(args):
    """Handles the 'results filter' command."""
    try:
        print(f"Filtering results by Type: {args.type}, Space ID: {args.space_id}, Task Keyword: {args.task_keyword}, Limit: {args.limit}, Offset: {args.offset}")
        results = results_manager.filter_content(
            output_type=args.type,
            space_id=args.space_id,
            task_keyword=args.task_keyword,
            limit=args.limit,
            offset=args.offset
        )
        if results:
            print("Filtered Results:")
            for res in results:
                print(f"  ID: {res['id']}, Space: {res['space_id']}, Type: {res['output_type']}, Task: {res['task_description'][:50]}..., Timestamp: {res['timestamp']}")
        else:
            print("No results found matching your filter criteria.")
    except Exception as e:
        print(f"Error filtering results: {e}")

def handle_results_update(args):
    """Handles the 'results update' command."""
    try:
        print(f"Updating notes for result ID: {args.content_id}")
        success = results_manager.update_content_notes(args.content_id, args.notes)
        if success:
            print(f"Notes updated successfully for result ID: {args.content_id}")
        else:
            print(f"Failed to update notes for result ID: {args.content_id}. (May not exist or error occurred)")
    except Exception as e:
        print(f"Error updating result notes: {e}")

def handle_results_delete(args):
    """Handles the 'results delete' command."""
    try:
        print(f"Deleting result with ID: {args.content_id}")
        # Confirmation prompt
        confirm = input(f"Are you sure you want to delete result ID {args.content_id}? (yes/no): ")
        if confirm.lower() == 'yes':
            success = results_manager.delete_content(args.content_id)
            if success:
                print(f"Result ID: {args.content_id} deleted successfully.")
            else:
                print(f"Failed to delete result ID: {args.content_id}. (May not exist or error occurred)")
        else:
            print("Deletion cancelled.")
    except Exception as e:
        print(f"Error deleting result: {e}")

def handle_results_initdb(args):
    """Handles the 'results initdb' command."""
    try:
        results_manager.init_db()
        # The init_db function already prints a success message.
    except Exception as e:
        print(f"Error initializing database: {e}")


def main():
    parser = argparse.ArgumentParser(description="CLI tool for interacting with Hugging Face Spaces and managing results.", formatter_class=argparse.RawTextHelpFormatter)
    subparsers = parser.add_subparsers(title="commands", dest="command", required=True, help="Available commands")

    # --- Search Command ---
    search_parser = subparsers.add_parser('search', help='Search for Hugging Face Spaces.')
    search_parser.add_argument('task_description', help='Description of the task to search for.')
    search_parser.add_argument('--sort_by', default='likes', help='Field to sort results by (e.g., likes, updatedAt). Default: likes.')
    search_parser.add_argument('--limit', type=int, default=10, help='Maximum number of results to return. Default: 10.')
    search_parser.set_defaults(func=handle_search_spaces)

    # --- Favorites Command ---
    favorites_parser = subparsers.add_parser('favorites', help='Manage favorite Spaces.')
    fav_subparsers = favorites_parser.add_subparsers(title="subcommands", dest="fav_subcommand", required=True, help="Favorite management actions")

    fav_add_parser = fav_subparsers.add_parser('add', help='Add a Space to favorites.')
    fav_add_parser.add_argument('space_id', help='ID of the Space to add (e.g., author_name/space_name).')
    fav_add_parser.set_defaults(func=handle_favorites_add)

    fav_list_parser = fav_subparsers.add_parser('list', help='List favorite Spaces.')
    fav_list_parser.set_defaults(func=handle_favorites_list)

    # --- Run Command ---
    run_parser = subparsers.add_parser('run', help='Run a Hugging Face Space or get API details.')
    run_subparsers = run_parser.add_subparsers(title="subcommands", dest="run_subcommand", required=True, help="Run actions")

    run_info_parser = run_subparsers.add_parser('info', help='Get API details for a Space.')
    run_info_parser.add_argument('space_id', help='ID of the Space (e.g., author_name/space_name).')
    run_info_parser.set_defaults(func=handle_run_info)

    run_predict_parser = run_subparsers.add_parser('predict', help='Run a Space prediction synchronously.')
    run_predict_parser.add_argument('space_id', help='ID of the Space.')
    run_predict_parser.add_argument('api_name', help='API endpoint name (e.g., /predict or /api/predict).')
    run_predict_parser.add_argument('--params', nargs='+', help="Input parameters for the Space API.\nUse key=value (e.g., text='Hello') or just values if order is known (e.g., 'Hello' 50).\nFor file inputs, use key=filepath.ext (e.g., image=photo.png).")
    run_predict_parser.add_argument('--task_desc', help='Optional task description for saving to results. Defaults to space_id.')
    run_predict_parser.add_argument('--output_type_for_db', help='Optional output type (e.g., text, image_path) for saving the result to the database. If not provided, result is printed but not saved.')
    run_predict_parser.set_defaults(func=handle_run_predict)

    run_submit_parser = run_subparsers.add_parser('submit', help='Submit a job to a Space asynchronously.')
    run_submit_parser.add_argument('space_id', help='ID of the Space.')
    run_submit_parser.add_argument('api_name', help='API endpoint name.')
    run_submit_parser.add_argument('--params', nargs='+', help="Input parameters, same format as 'run predict'.")
    run_submit_parser.set_defaults(func=handle_run_submit)

    # --- Results Command ---
    results_parser = subparsers.add_parser('results', help='Manage generated results from Spaces.')
    res_subparsers = results_parser.add_subparsers(title="subcommands", dest="res_subcommand", required=True, help="Results management actions")

    res_list_parser = res_subparsers.add_parser('list', help='List all generated content (paginated).')
    res_list_parser.add_argument('--limit', type=int, default=20, help='Maximum results per page. Default: 20.')
    res_list_parser.add_argument('--offset', type=int, default=0, help='Offset for pagination. Default: 0.')
    res_list_parser.set_defaults(func=handle_results_list)

    res_add_parser = res_subparsers.add_parser('add', help='Manually add a result to the library.')
    res_add_parser.add_argument('--space_id', required=True, help='Space ID (e.g., author/space_name).')
    res_add_parser.add_argument('--task', required=True, help='Task description.')
    res_add_parser.add_argument('--type', required=True, choices=['text', 'image_path', 'audio_path', 'video_path', 'json_data', 'file', 'other'], help='Type of the output.')
    res_add_parser.add_argument('--data', required=True, help='The generated content or path to it.')
    res_add_parser.add_argument('--params_json', help='Optional: Input parameters used for generation, as a JSON string.')
    res_add_parser.add_argument('--notes', help='Optional: User notes.')
    res_add_parser.set_defaults(func=handle_results_add)

    res_view_parser = res_subparsers.add_parser('view', help='View details of a specific result by ID.')
    res_view_parser.add_argument('content_id', type=int, help='ID of the content to view.')
    res_view_parser.set_defaults(func=handle_results_view)
    
    res_filter_parser = res_subparsers.add_parser('filter', help='Filter results based on criteria.')
    res_filter_parser.add_argument('--type', help='Filter by output type.')
    res_filter_parser.add_argument('--space_id', help='Filter by Space ID.')
    res_filter_parser.add_argument('--task_keyword', help='Filter by a keyword in the task description.')
    res_filter_parser.add_argument('--limit', type=int, default=20, help='Maximum results. Default: 20.')
    res_filter_parser.add_argument('--offset', type=int, default=0, help='Offset for pagination. Default: 0.')
    res_filter_parser.set_defaults(func=handle_results_filter)

    res_update_parser = res_subparsers.add_parser('update', help='Update notes for a specific result.')
    res_update_parser.add_argument('content_id', type=int, help='ID of the content to update.')
    res_update_parser.add_argument('--notes', required=True, help='The new notes to set.')
    res_update_parser.set_defaults(func=handle_results_update)

    res_delete_parser = res_subparsers.add_parser('delete', help='Delete a specific result by ID.')
    res_delete_parser.add_argument('content_id', type=int, help='ID of the content to delete.')
    res_delete_parser.set_defaults(func=handle_results_delete)

    res_init_parser = res_subparsers.add_parser('initdb', help='Initialize the results database (creates table if not exists).')
    res_init_parser.set_defaults(func=handle_results_initdb)

    args = parser.parse_args()
    if hasattr(args, 'func'):
        args.func(args)
    else:
        # If no subcommand is given, but 'command' is (e.g. 'python app.py results')
        # find the relevant subparser and print its help.
        if args.command:
            # Access subparsers action from the main parser
            subparsers_action = [action for action in parser._actions if isinstance(action, argparse._SubParsersAction)][0]
            # Get the subparser for the given command
            subparser = subparsers_action.choices.get(args.command)
            if subparser:
                subparser.print_help()
            else: # Should not happen if command is required
                parser.print_help()
        else: # Should not happen if command is required
            parser.print_help()

if __name__ == '__main__':
    main()
