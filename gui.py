import sys
import os
import json
import re # For parsing API details (though less used with structured API)

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QTabWidget, QGroupBox,
    QLabel, QLineEdit, QComboBox, QSpinBox, QPushButton, QTableWidget,
    QTableWidgetItem, QListWidget, QListWidgetItem, QHBoxLayout, QMessageBox, QHeaderView,
    QSplitter, QScrollArea, QFormLayout, QFileDialog, QCheckBox, QInputDialog,
    QMenu, QStackedWidget, QTextEdit, QDoubleSpinBox, QSlider, QColorDialog
)
from PyQt6.QtGui import QPalette, QColor, QAction, QDesktopServices, QPixmap
from PyQt6.QtCore import Qt, pyqtSignal, QUrl, QSettings

# Assuming space_finder.py, space_runner.py, and results_manager.py are in the same directory or accessible
import space_finder
import space_runner # For Space Execution tab
import results_manager # For saving results to DB
from huggingface_hub import SpaceInfo # For type hinting if needed
from gradio_client import handle_file # For file parameters

def get_contrasting_text_color(background_color: QColor) -> QColor:
    # Calculate luminance (simplified formula)
    # Y = 0.299*R + 0.587*G + 0.114*B
    luminance = 0.299 * background_color.redF() + \
                0.587 * background_color.greenF() + \
                0.114 * background_color.blueF()
    return QColor(0, 0, 0) if luminance > 0.5 else QColor(255, 255, 255)

class SpacesUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Spaces UI")
        self.setGeometry(100, 100, 1000, 800) # Increased size for more content

        self.settings = QSettings("MyCompany", "SpacesUI") # Or your preferred organization/app name
        default_primary_color_hex = "#2a82da" # The original blue
        saved_color_hex = self.settings.value("theme/primaryColor", default_primary_color_hex)
        current_primary_color = QColor(saved_color_hex)
        self._apply_theme_to_palette(current_primary_color)

        # Central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # Common attributes (initialize before tab methods that might use them)
        self.current_selected_space_id = None # From Discovery tab search result
        self.current_results_page = 0
        self.results_per_page = 15
        self.selected_content_id_in_library = None

        # Attributes for Space Execution Tab
        self.dynamic_input_widgets = {} # Stores {'param_name': {'widget': QWidget, 'type': str, 'label': str, 'component': str}}
        self.current_loaded_space_id_exec = None
        self.current_loaded_api_details_exec = None
        self.current_selected_endpoint_name_exec = None
        self.current_exec_output_data = None
        self.current_exec_output_type = None

        # Tab widget for main sections
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)

        # --- Space Discovery Tab ---
        self.space_discovery_gb = QGroupBox("Space Discovery")
        self.tab_widget.addTab(self.space_discovery_gb, "Space Discovery")
        self.init_space_discovery_tab()

        # --- Space Execution Tab ---
        self.space_execution_gb = QGroupBox("Space Execution")
        self.tab_widget.addTab(self.space_execution_gb, "Space Execution")
        self.init_space_execution_tab()

        # --- Results Library Tab ---
        self.results_library_gb = QGroupBox("Results Library")
        self.tab_widget.addTab(self.results_library_gb, "Results Library")
        self.init_results_library_tab()

        # Add "Settings" menu
        menu_bar = self.menuBar()
        settings_menu = menu_bar.addMenu("&Settings")

        change_theme_action = QAction("&Change Theme Color...", self)
        change_theme_action.triggered.connect(self.handle_change_theme)
        settings_menu.addAction(change_theme_action)

    def _apply_theme_to_palette(self, primary_color: QColor):
        palette = QPalette()
        
        # Define base dark theme colors
        dark_window_bg = QColor(53, 53, 53)
        dark_base_bg = QColor(35, 35, 35) # Darker for inputs/lists
        dark_text_color = get_contrasting_text_color(dark_window_bg)

        palette.setColor(QPalette.ColorRole.Window, dark_window_bg)
        palette.setColor(QPalette.ColorRole.WindowText, dark_text_color)
        palette.setColor(QPalette.ColorRole.Base, dark_base_bg)
        palette.setColor(QPalette.ColorRole.AlternateBase, dark_window_bg) # Or a slightly different dark gray
        palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(255, 255, 220)) # Light yellow for tooltips
        palette.setColor(QPalette.ColorRole.ToolTipText, QColor(0,0,0)) # Black text for tooltips
        palette.setColor(QPalette.ColorRole.Text, dark_text_color)
        
        # Use primary_color for actionable items
        button_text_color = get_contrasting_text_color(primary_color)
        palette.setColor(QPalette.ColorRole.Button, primary_color)
        palette.setColor(QPalette.ColorRole.ButtonText, button_text_color)
        
        palette.setColor(QPalette.ColorRole.BrightText, QColor(255, 0, 0)) # Keep for errors or important alerts
        palette.setColor(QPalette.ColorRole.Link, primary_color)
        
        palette.setColor(QPalette.ColorRole.Highlight, primary_color)
        palette.setColor(QPalette.ColorRole.HighlightedText, get_contrasting_text_color(primary_color))

        # Ensure disabled states are visible
        disabled_button_color = primary_color.darker(130) # Make it look grayed out a bit
        # Ensure disabled_text_color is QColor
        base_disabled_text_color = get_contrasting_text_color(disabled_button_color) 
        palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Button, disabled_button_color)
        palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, base_disabled_text_color)
        palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, base_disabled_text_color.darker(110) if base_disabled_text_color.lightnessF() > 0.5 else base_disabled_text_color.lighter(110)) # Adjust based on its own lightness
        palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.WindowText, base_disabled_text_color.darker(110) if base_disabled_text_color.lightnessF() > 0.5 else base_disabled_text_color.lighter(110))


        self.setPalette(palette)
        # Also set for the entire application to ensure dialogs, etc., are themed
        app = QApplication.instance()
        if app:
            app.setPalette(palette)

    def handle_change_theme(self):
        current_color_hex = self.settings.value("theme/primaryColor", "#2a82da")
        initial_color = QColor(current_color_hex)
        
        new_color = QColorDialog.getColor(initial_color, self, "Select Primary Theme Color")
        
        if new_color.isValid():
            self.settings.setValue("theme/primaryColor", new_color.name())
            self._apply_theme_to_palette(new_color)

    def init_space_discovery_tab(self):
        discovery_layout = QVBoxLayout(self.space_discovery_gb)

        # Search Section
        self.task_input = QLineEdit()
        self.task_input.setPlaceholderText("e.g., text generation, image classification")
        self.sort_combo = QComboBox()
        self.sort_combo.addItems(["likes", "updatedAt", "downloads"])
        self.limit_spinbox = QSpinBox()
        self.limit_spinbox.setRange(1, 100)
        self.limit_spinbox.setValue(10)
        self.search_button = QPushButton("Search Spaces")
        
        search_section_gb = QGroupBox("Find Spaces")
        search_form_layout = QFormLayout()
        search_section_gb.setLayout(search_form_layout)
        search_form_layout.addRow(QLabel("Task Description:"), self.task_input)
        search_form_layout.addRow(QLabel("Sort by:"), self.sort_combo)
        search_form_layout.addRow(QLabel("Limit:"), self.limit_spinbox)
        search_form_layout.addRow(self.search_button)
        self.search_button.clicked.connect(self.handle_search_spaces)
        discovery_layout.addWidget(search_section_gb)

        # Search Results Section
        results_section_gb = QGroupBox("Search Results")
        results_layout = QVBoxLayout(results_section_gb) # Corrected: Set layout on the GroupBox
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(4)
        self.results_table.setHorizontalHeaderLabels(["Space ID", "Author", "Likes", "Task"])
        self.results_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.results_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.results_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.results_table.itemSelectionChanged.connect(self.handle_search_result_selection)
        self.results_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.results_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive) # Allow Space ID to be resized
        results_layout.addWidget(self.results_table)
        discovery_layout.addWidget(results_section_gb)

        # Favorites Section
        self.favorites_list_widget = QListWidget()
        self.add_to_fav_button = QPushButton("Add Search Result to Favorites")
        self.add_to_fav_button.setEnabled(False)
        self.remove_fav_button = QPushButton("Remove Selected Favorite") # Renamed for clarity
        self.refresh_fav_button = QPushButton("Refresh Favorites List")

        favorites_section_gb = QGroupBox("Favorite Spaces")
        favorites_layout = QVBoxLayout(favorites_section_gb)
        favorites_layout.addWidget(self.favorites_list_widget)
        fav_buttons_layout = QHBoxLayout()
        fav_buttons_layout.addWidget(self.add_to_fav_button)
        fav_buttons_layout.addWidget(self.remove_fav_button)
        fav_buttons_layout.addWidget(self.refresh_fav_button)
        favorites_layout.addLayout(fav_buttons_layout)
        discovery_layout.addWidget(favorites_section_gb)

        self.add_to_fav_button.clicked.connect(self.handle_add_to_favorites)
        self.remove_fav_button.clicked.connect(self.handle_remove_favorite)
        self.refresh_fav_button.clicked.connect(self.refresh_favorites_list)
        
        self.refresh_favorites_list() # Initial population

    def handle_search_spaces(self):
        task = self.task_input.text().strip()
        sort_by = self.sort_combo.currentText()
        limit = self.limit_spinbox.value()

        if not task:
            QMessageBox.warning(self, "Search Error", "Task description cannot be empty.")
            return

        try:
            self.search_button.setEnabled(False)
            self.search_button.setText("Searching...")
            QApplication.processEvents() 

            spaces = space_finder.find_spaces(task_description=task, sort_by=sort_by, limit=limit)
            self.results_table.setRowCount(0) 

            if not spaces:
                QMessageBox.information(self, "No Results", "No spaces found for your query.")
                return

            for row, space_info in enumerate(spaces):
                self.results_table.insertRow(row)
                space_id = getattr(space_info, 'id', 'N/A')
                author = getattr(space_info, 'author', 'N/A')
                likes = getattr(space_info, 'likes', 0)
                
                task_tags_list = []
                if hasattr(space_info, 'pipeline_tag') and space_info.pipeline_tag:
                    task_tags_list.append(str(space_info.pipeline_tag))
                
                if hasattr(space_info, 'cardData') and isinstance(space_info.cardData, dict):
                    card_tags = space_info.cardData.get('tags', [])
                    if isinstance(card_tags, list):
                        task_tags_list.extend([str(t) for t in card_tags if t]) # Ensure t is not None
                
                task_tags_str = ", ".join(list(set(task_tags_list))) if task_tags_list else "N/A"

                self.results_table.setItem(row, 0, QTableWidgetItem(str(space_id)))
                self.results_table.setItem(row, 1, QTableWidgetItem(str(author)))
                self.results_table.setItem(row, 2, QTableWidgetItem(str(likes)))
                self.results_table.setItem(row, 3, QTableWidgetItem(task_tags_str))
            
            self.results_table.resizeColumnsToContents()
            self.results_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)


        except Exception as e:
            QMessageBox.critical(self, "Search Failed", f"An error occurred during search: {e}")
        finally:
            self.search_button.setEnabled(True)
            self.search_button.setText("Search Spaces")

    def handle_search_result_selection(self):
        selected_rows = self.results_table.selectionModel().selectedRows()
        if selected_rows:
            self.current_selected_space_id = self.results_table.item(selected_rows[0].row(), 0).text()
            self.add_to_fav_button.setEnabled(True)
        else:
            self.current_selected_space_id = None
            self.add_to_fav_button.setEnabled(False)

    def refresh_favorites_list(self):
        self.favorites_list_widget.clear()
        try:
            fav_ids = space_finder.get_favorite_spaces()
            if fav_ids:
                self.favorites_list_widget.addItems(fav_ids)
            else:
                placeholder_item = QListWidgetItem("No favorites yet.")
                placeholder_item.setData(Qt.ItemDataRole.UserRole, "placeholder")
                self.favorites_list_widget.addItem(placeholder_item)
        except Exception as e:
            QMessageBox.warning(self, "Favorites Error", f"Could not load favorites: {e}")
            error_item = QListWidgetItem("Error loading favorites.")
            error_item.setData(Qt.ItemDataRole.UserRole, "placeholder")
            self.favorites_list_widget.addItem(error_item)

    def handle_add_to_favorites(self):
        if not self.current_selected_space_id:
            QMessageBox.warning(self, "Add Favorite Error", "No space selected from search results.")
            return
        
        try:
            space_finder.add_to_favorites(self.current_selected_space_id)
            self.refresh_favorites_list() 
            if hasattr(self, 'exec_load_fav_button'): # Check if exec tab is initialized
                 self.exec_load_fav_button.setToolTip("Favorites updated. Click to refresh list in dialog.")
        except Exception as e:
            QMessageBox.critical(self, "Add Favorite Failed", f"Could not add favorite: {e}")

    def handle_remove_favorite(self):
        selected_item = self.favorites_list_widget.currentItem()
        if not selected_item or selected_item.data(Qt.ItemDataRole.UserRole) == "placeholder":
            QMessageBox.warning(self, "Remove Favorite Error", "Please select a valid favorite to remove.")
            return
        
        space_id_to_remove = selected_item.text()
        confirm = QMessageBox.question(self, "Confirm Removal", 
                                       f"Are you sure you want to remove '{space_id_to_remove}' from favorites?",
                                       QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if confirm == QMessageBox.StandardButton.Yes:
            try:
                space_finder.remove_from_favorites(space_id_to_remove)
                self.refresh_favorites_list() 
                if hasattr(self, 'exec_load_fav_button'):
                    self.exec_load_fav_button.setToolTip("Favorites updated. Click to refresh list in dialog.")
            except Exception as e:
                QMessageBox.critical(self, "Remove Favorite Failed", f"Could not remove favorite: {e}")

    # --- Space Execution Tab ---
    def init_space_execution_tab(self):
        layout = QVBoxLayout(self.space_execution_gb)

        # Top Section: Space ID Input and API Loading
        top_section_gb = QGroupBox("Load Space for Execution")
        top_layout = QFormLayout(top_section_gb)

        self.exec_space_id_input = QLineEdit()
        self.exec_space_id_input.setPlaceholderText("e.g., author_name/space_name")
        top_layout.addRow("Space ID:", self.exec_space_id_input)

        buttons_layout = QHBoxLayout()
        self.exec_load_fav_button = QPushButton("Load from Favorites")
        self.exec_load_fav_button.clicked.connect(self.handle_exec_load_favorite)
        buttons_layout.addWidget(self.exec_load_fav_button)

        self.exec_fetch_api_button = QPushButton("Fetch API Details")
        self.exec_fetch_api_button.clicked.connect(self.handle_exec_fetch_api)
        buttons_layout.addWidget(self.exec_fetch_api_button)
        top_layout.addRow(buttons_layout)
        
        self.exec_api_endpoint_label = QLabel("API Endpoint: Not loaded")
        top_layout.addRow(self.exec_api_endpoint_label)
        layout.addWidget(top_section_gb)

        # Middle Section: Dynamic Parameters
        params_gb = QGroupBox("Input Parameters")
        params_main_layout = QVBoxLayout(params_gb)
        
        self.exec_params_scroll_area = QScrollArea()
        self.exec_params_scroll_area.setWidgetResizable(True)
        self.exec_params_widget = QWidget() # Container for form layout
        self.exec_params_form_layout = QFormLayout(self.exec_params_widget)
        self.exec_params_scroll_area.setWidget(self.exec_params_widget)
        params_main_layout.addWidget(self.exec_params_scroll_area)

        self.exec_clear_inputs_button = QPushButton("Clear Inputs")
        self.exec_clear_inputs_button.clicked.connect(self.handle_exec_clear_inputs)
        params_main_layout.addWidget(self.exec_clear_inputs_button, alignment=Qt.AlignmentFlag.AlignRight)
        layout.addWidget(params_gb)

        # Execution and Saving Section
        execution_controls_gb = QGroupBox("Execution & Saving")
        execution_controls_layout = QFormLayout(execution_controls_gb)

        self.exec_run_button = QPushButton("Execute Space")
        self.exec_run_button.clicked.connect(self.handle_exec_run_space)
        self.exec_run_button.setEnabled(False) # Enabled after API is loaded
        execution_controls_layout.addRow(self.exec_run_button)
        
        self.exec_task_desc_input = QTextEdit()
        self.exec_task_desc_input.setPlaceholderText("Describe the task or purpose of this execution (for library).")
        self.exec_task_desc_input.setMaximumHeight(60)
        execution_controls_layout.addRow("Task Description (for saving):", self.exec_task_desc_input)

        self.exec_save_result_checkbox = QCheckBox("Save result to library upon successful execution")
        self.exec_save_result_checkbox.setChecked(True)
        execution_controls_layout.addRow(self.exec_save_result_checkbox)
        
        layout.addWidget(execution_controls_gb)

        # Output Section
        output_gb = QGroupBox("Execution Output")
        output_main_layout = QVBoxLayout(output_gb)
        self.exec_output_stack = QStackedWidget()

        # Page 0: Placeholder
        exec_placeholder_label = QLabel("Output will appear here.")
        exec_placeholder_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.exec_output_stack.addWidget(exec_placeholder_label)
        # Page 1: Text
        self.exec_output_text_view = QTextEdit()
        self.exec_output_text_view.setReadOnly(True)
        self.exec_output_stack.addWidget(self.exec_output_text_view)
        # Page 2: Image
        self.exec_output_image_scroll = QScrollArea()
        self.exec_output_image_scroll.setWidgetResizable(True)
        self.exec_output_image_label = QLabel()
        self.exec_output_image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.exec_output_image_scroll.setWidget(self.exec_output_image_label)
        self.exec_output_stack.addWidget(self.exec_output_image_scroll)
        # Page 3: Media/File Button
        self.exec_output_file_button_widget = QWidget()
        exec_file_button_layout = QVBoxLayout(self.exec_output_file_button_widget)
        self.exec_output_file_button = QPushButton("Open File/Media")
        exec_file_button_layout.addWidget(self.exec_output_file_button)
        exec_file_button_layout.addStretch()
        self.exec_output_stack.addWidget(self.exec_output_file_button_widget)
        
        output_main_layout.addWidget(self.exec_output_stack)

        self.exec_clear_output_button = QPushButton("Clear Output")
        self.exec_clear_output_button.clicked.connect(self.handle_exec_clear_output)
        output_main_layout.addWidget(self.exec_clear_output_button, alignment=Qt.AlignmentFlag.AlignRight)
        layout.addWidget(output_gb)

        layout.addStretch() # Push everything up

    def handle_exec_load_favorite(self):
        fav_ids = space_finder.get_favorite_spaces()
        if not fav_ids:
            QMessageBox.information(self, "No Favorites", "You have no saved favorites.")
            return

        space_id, ok = QInputDialog.getItem(self, "Select Favorite Space", 
                                            "Favorite Spaces:", fav_ids, 0, False)
        if ok and space_id:
            self.exec_space_id_input.setText(space_id)
            self.handle_exec_fetch_api() # Optionally auto-fetch

    def handle_exec_fetch_api(self):
        space_id = self.exec_space_id_input.text().strip()
        if not space_id:
            QMessageBox.warning(self, "API Load Error", "Please enter a Space ID.")
            return

        self.exec_fetch_api_button.setText("Fetching...")
        self.exec_fetch_api_button.setEnabled(False)
        QApplication.processEvents()

        try:
            # This function needs to be implemented in space_runner.py
            # It should return a dict similar to what gradio_client.Client.view_api() provides
            api_details = space_runner.get_space_api_details(space_id) 
            if api_details:
                self.current_loaded_space_id_exec = space_id
                self.current_loaded_api_details_exec = api_details
                self.populate_execution_inputs(api_details)
                self.exec_run_button.setEnabled(True)
                # Update task description based on space (e.g. from cardData if available)
                # For simplicity, this is manual for now via self.exec_task_desc_input
            else:
                QMessageBox.critical(self, "API Load Failed", f"Could not fetch API details for '{space_id}'. Check Space ID and network.")
                self.current_loaded_api_details_exec = None
                self.exec_run_button.setEnabled(False)
                self.exec_api_endpoint_label.setText("API Endpoint: Load failed")
        except Exception as e:
            QMessageBox.critical(self, "API Load Error", f"An error occurred: {e}")
            self.current_loaded_api_details_exec = None
            self.exec_run_button.setEnabled(False)
            self.exec_api_endpoint_label.setText("API Endpoint: Error")
        finally:
            self.exec_fetch_api_button.setText("Fetch API Details")
            self.exec_fetch_api_button.setEnabled(True)
            
    def _clear_layout(self, layout):
        if layout is not None:
            while layout.count():
                item = layout.takeAt(0)
                widget = item.widget()
                if widget is not None:
                    widget.deleteLater()
                else:
                    sub_layout = item.layout()
                    if sub_layout is not None:
                        self._clear_layout(sub_layout)
                        sub_layout.deleteLater()


    def populate_execution_inputs(self, api_details):
        self._clear_layout(self.exec_params_form_layout) # Clear previous dynamic widgets
        self.dynamic_input_widgets.clear()

        if not api_details or not api_details.get("named_endpoints"):
            self.exec_api_endpoint_label.setText("API Endpoint: No named endpoints found.")
            return

        # For simplicity, use the first named endpoint.
        # A more robust solution might involve a QComboBox to select an endpoint.
        endpoint_name = list(api_details["named_endpoints"].keys())[0]
        self.current_selected_endpoint_name_exec = endpoint_name
        self.exec_api_endpoint_label.setText(f"API Endpoint: {endpoint_name}")
        
        endpoint_info = api_details["named_endpoints"][endpoint_name]
        parameters = endpoint_info.get("parameters", [])

        for i, param in enumerate(parameters):
            label_text = param.get("label", f"param_{i}")
            param_name = param.get("name", label_text) # Gradio often uses 'label' as key in practice for older versions
            component_type = param.get("component", "").lower()
            # gradio_client view_api returns 'type' (e.g. 'textbox'), and 'python_type' (e.g. {'type': 'str'})
            # 'component' is also available. Let's prioritize 'component' then 'type'.
            actual_type = param.get("type", "textbox").lower() # e.g. "textbox", "number", "checkbox"
            
            widget = None
            param_info = {'widget': None, 'type': actual_type, 'label': label_text, 'component': component_type, 'name': param_name}

            if component_type in ["textbox", "text"] or actual_type in ["textbox", "text"]:
                # Check for multiline text
                if param.get("lines", 1) > 1:
                    widget = QTextEdit()
                    widget.setPlaceholderText(param.get("info", label_text))
                    widget.setMaximumHeight(80)
                else:
                    widget = QLineEdit()
                    widget.setPlaceholderText(param.get("info", label_text))
                default_value = param.get("value")
                if default_value is not None:
                    if isinstance(widget, QTextEdit): widget.setPlainText(str(default_value))
                    else: widget.setText(str(default_value))

            elif component_type == "number" or actual_type == "number":
                widget = QDoubleSpinBox()
                py_type = param.get("python_type", {}).get("type", "float")
                if py_type == "int":
                    widget = QSpinBox() # Use QSpinBox for integers
                    widget.setRange(int(param.get("minimum", -1000000)), int(param.get("maximum", 1000000)))
                else: # float
                    widget.setRange(param.get("minimum", -1000000.0), param.get("maximum", 1000000.0))
                    widget.setDecimals(param.get("precision", 2))
                
                default_value = param.get("value")
                if default_value is not None: widget.setValue(float(default_value))


            elif component_type == "slider" or actual_type == "slider":
                widget = QSlider(Qt.Orientation.Horizontal)
                widget.setRange(int(param.get("minimum", 0)), int(param.get("maximum", 100)))
                widget.setValue(int(param.get("value", param.get("minimum", 0))))
                # TODO: Add a QLabel to show current slider value if desired

            elif component_type == "checkbox" or actual_type == "checkbox":
                widget = QCheckBox(label_text) # Label is part of checkbox
                label_text = "" # No separate label needed for QFormLayout
                default_value = param.get("value")
                if default_value is not None: widget.setChecked(bool(default_value))
            
            elif component_type in ["dropdown", "radio"] or actual_type in ["dropdown", "radio"]:
                widget = QComboBox()
                choices = param.get("choices", [])
                if choices: widget.addItems([str(c) for c in choices])
                default_value = param.get("value")
                if default_value is not None: widget.setCurrentText(str(default_value))

            elif component_type in ["image", "audio", "video", "file", "uploadbutton"] or \
                 actual_type in ["image", "audio", "video", "file", "uploadbutton"]:
                file_input_widget = QWidget()
                file_input_layout = QHBoxLayout(file_input_widget)
                file_input_layout.setContentsMargins(0,0,0,0)
                
                file_label = QLabel("No file selected.")
                file_button = QPushButton("Browse...")
                
                # Use a unique object name for the label to retrieve it later
                file_label_obj_name = f"file_label_for_{param_name}"
                file_label.setObjectName(file_label_obj_name)

                file_button.clicked.connect(lambda checked=False, p_name=param_name, lbl_obj_name=file_label_obj_name: self.handle_exec_browse_file(p_name, lbl_obj_name))
                
                file_input_layout.addWidget(file_label, 1) # Give label more space
                file_input_layout.addWidget(file_button)
                widget = file_input_widget
                param_info['type'] = 'filepath' # Special handling for file types
                param_info['file_label_obj_name'] = file_label_obj_name # Store for value retrieval

            else: # Fallback for unknown types
                widget = QLineEdit()
                widget.setPlaceholderText(f"Unsupported type: {component_type} / {actual_type}")
                widget.setEnabled(False)

            if widget:
                param_info['widget'] = widget
                self.dynamic_input_widgets[param_name] = param_info
                if label_text: # Don't add label for checkbox as it's part of the widget
                    self.exec_params_form_layout.addRow(QLabel(label_text + ":"), widget)
                else:
                    self.exec_params_form_layout.addRow(widget)
        
        self.exec_params_widget.adjustSize() # Adjust size of container for scrollbar if needed

    def handle_exec_browse_file(self, param_name_key, file_label_obj_name):
        # Find the QLabel associated with this file input
        file_label_widget = self.exec_params_widget.findChild(QLabel, file_label_obj_name)
        if not file_label_widget:
            print(f"Error: Could not find file label for {param_name_key}")
            return

        # TODO: Determine file type filter based on param.get("file_types") if available
        file_dialog = QFileDialog(self)
        # Example: if param.get("file_types") == ["image"], set name filter "Images (*.png *.jpg)"
        file_path, _ = file_dialog.getOpenFileName(self, f"Select File for {param_name_key}")
        
        if file_path:
            file_label_widget.setText(os.path.basename(file_path))
            # Store the full path in the dynamic_input_widgets, associated with the label or a hidden field
            # For simplicity, we'll retrieve from label's tooltip or a dedicated attribute if needed.
            # Here, we assume the label's text is enough for display, and we store the actual path.
            self.dynamic_input_widgets[param_name_key]['selected_file_path'] = file_path 
        else:
            file_label_widget.setText("No file selected.")
            if 'selected_file_path' in self.dynamic_input_widgets[param_name_key]:
                del self.dynamic_input_widgets[param_name_key]['selected_file_path']


    def handle_exec_clear_inputs(self):
        # This will clear and re-populate with defaults if API is loaded
        if self.current_loaded_api_details_exec:
            self.populate_execution_inputs(self.current_loaded_api_details_exec)
        else: # If no API loaded, just clear the form layout
            self._clear_layout(self.exec_params_form_layout)
            self.dynamic_input_widgets.clear()

    def handle_exec_run_space(self):
        if not self.current_loaded_api_details_exec or not self.current_selected_endpoint_name_exec:
            QMessageBox.warning(self, "Execution Error", "API details not loaded or endpoint not selected.")
            return

        collected_params = [] # Gradio client expects a list of args
        param_names_ordered = [] # To match the order of parameters in API details

        # Ensure we iterate in the order defined by the API
        endpoint_info = self.current_loaded_api_details_exec["named_endpoints"][self.current_selected_endpoint_name_exec]
        api_parameters = endpoint_info.get("parameters", [])

        try:
            for api_param_info in api_parameters:
                param_name = api_param_info.get("name", api_param_info.get("label"))
                stored_param_info = self.dynamic_input_widgets.get(param_name)

                if not stored_param_info:
                    # This might happen if a parameter was optional and not rendered, or an error.
                    # Gradio often requires all args, so send None or default.
                    # For simplicity, we'll try to send None.
                    # Check api_param_info for 'default' or if it's optional.
                    # This part needs more robust handling of optional/default params from Gradio API spec.
                    print(f"Warning: No widget found for API parameter '{param_name}'. Sending None.")
                    collected_params.append(None) 
                    continue

                widget = stored_param_info['widget']
                param_type = stored_param_info['type']

                value = None
                if param_type == 'filepath':
                    value = stored_param_info.get('selected_file_path')
                    if value:
                        value = handle_file(value) # Prepare for Gradio client
                    # If no file selected, Gradio might expect None for optional files
                elif isinstance(widget, QLineEdit):
                    value = widget.text()
                elif isinstance(widget, QTextEdit):
                    value = widget.toPlainText()
                elif isinstance(widget, (QSpinBox, QDoubleSpinBox)):
                    value = widget.value()
                elif isinstance(widget, QCheckBox):
                    value = widget.isChecked()
                elif isinstance(widget, QComboBox):
                    value = widget.currentText() # Or .currentData() if set
                elif isinstance(widget, QSlider):
                    value = widget.value()
                # Add other widget types as needed
                collected_params.append(value)

            self.exec_run_button.setText("Executing...")
            self.exec_run_button.setEnabled(False)
            QApplication.processEvents()

            # This function needs to be implemented in space_runner.py
            # It should return a tuple: (result_data, output_type_string, error_string_if_any)
            # output_type_string: 'text', 'image_path', 'json_data', 'file_path', 'url', 'error'
            result_data, output_type, error_msg = space_runner.execute_space_endpoint(
                self.current_loaded_space_id_exec,
                self.current_selected_endpoint_name_exec,
                *collected_params # Unpack as positional arguments
            )
            
            self.current_exec_output_data = result_data
            self.current_exec_output_type = output_type

            if error_msg:
                 self.display_execution_output(f"Error: {error_msg}", "error")
            else:
                self.display_execution_output(result_data, output_type)
                if self.exec_save_result_checkbox.isChecked() and output_type != 'error':
                    self.handle_exec_save_current_result_to_library()

        except Exception as e:
            QMessageBox.critical(self, "Execution Failed", f"An error occurred during execution: {e}")
            self.display_execution_output(f"Client-side error: {e}", "error")
            self.current_exec_output_data = None
            self.current_exec_output_type = None
        finally:
            self.exec_run_button.setText("Execute Space")
            self.exec_run_button.setEnabled(True)

    def display_execution_output(self, data, output_type_str):
        self.exec_output_file_button.disconnect() # Disconnect previous signals for file button

        if output_type_str == 'text' or output_type_str == 'json_data' or output_type_str == 'error':
            if output_type_str == 'json_data' and isinstance(data, (dict, list)):
                try:
                    self.exec_output_text_view.setText(json.dumps(data, indent=2))
                except Exception: # If data is not directly serializable, show as string
                    self.exec_output_text_view.setText(str(data))
            else:
                self.exec_output_text_view.setText(str(data))
            self.exec_output_stack.setCurrentWidget(self.exec_output_text_view)
        
        elif output_type_str == 'image_path':
            if data and os.path.exists(str(data)):
                pixmap = QPixmap(str(data))
                if pixmap.isNull():
                    self.exec_output_image_label.setText(f"Error loading image (or not an image):\n{data}")
                else:
                    max_h = self.exec_output_image_scroll.height() - 20 # Max height for image preview
                    if pixmap.height() > max_h and max_h > 0 :
                         pixmap = pixmap.scaledToHeight(max_h, Qt.TransformationMode.SmoothTransformation)
                    self.exec_output_image_label.setPixmap(pixmap)
                self.exec_output_stack.setCurrentWidget(self.exec_output_image_scroll)
            else:
                self.exec_output_image_label.setText(f"Image file not found or path is invalid:\n{data}")
                self.exec_output_stack.setCurrentWidget(self.exec_output_image_scroll)
        
        elif output_type_str in ['audio_path', 'video_path', 'file_path', 'url']:
            self.exec_output_file_button.setText(f"Open {output_type_str.replace('_path','').capitalize()}: {os.path.basename(str(data)) if data else 'N/A'}")
            if data:
                 self.exec_output_file_button.clicked.connect(lambda: self.handle_rl_open_output_file(str(data), is_url=(output_type_str=='url')))
            self.exec_output_stack.setCurrentWidget(self.exec_output_file_button_widget)
        
        else: # Fallback or unknown type
            self.exec_output_text_view.setText(f"Output type '{output_type_str}' received.\nData: {str(data)}")
            self.exec_output_stack.setCurrentWidget(self.exec_output_text_view) # Show as text

    def handle_exec_clear_output(self):
        self.exec_output_stack.setCurrentIndex(0) # Placeholder
        self.exec_output_text_view.clear()
        self.exec_output_image_label.clear()
        self.exec_output_file_button.setText("Open File/Media")
        self.exec_output_file_button.disconnect()
        self.current_exec_output_data = None
        self.current_exec_output_type = None

    def handle_exec_save_current_result_to_library(self):
        if self.current_exec_output_data is None or self.current_exec_output_type is None:
            QMessageBox.information(self, "Save Error", "No valid execution result to save.")
            return

        space_id = self.current_loaded_space_id_exec
        task_desc = self.exec_task_desc_input.toPlainText().strip()
        if not task_desc:
            task_desc = f"Execution of {space_id}" # Default task description

        parameters_dict = {}
        endpoint_info = self.current_loaded_api_details_exec["named_endpoints"][self.current_selected_endpoint_name_exec]
        api_parameters = endpoint_info.get("parameters", [])

        for api_param_info in api_parameters:
            param_name = api_param_info.get("name", api_param_info.get("label"))
            stored_param_info = self.dynamic_input_widgets.get(param_name)
            if stored_param_info:
                widget = stored_param_info['widget']
                param_type = stored_param_info['type']
                value = None
                if param_type == 'filepath':
                    value = stored_param_info.get('selected_file_path', "Not provided")
                elif isinstance(widget, QLineEdit): value = widget.text()
                elif isinstance(widget, QTextEdit): value = widget.toPlainText()
                elif isinstance(widget, (QSpinBox, QDoubleSpinBox)): value = widget.value()
                elif isinstance(widget, QCheckBox): value = widget.isChecked()
                elif isinstance(widget, QComboBox): value = widget.currentText()
                elif isinstance(widget, QSlider): value = widget.value()
                parameters_dict[param_name] = value
        
        try:
            parameters_json = json.dumps(parameters_dict, indent=2)
        except TypeError: # Handle non-serializable if any (should be rare with basic types)
            parameters_json = json.dumps({k: str(v) for k, v in parameters_dict.items()}, indent=2)


        # Ensure output_data is serializable or a path string
        output_data_to_save = self.current_exec_output_data
        if self.current_exec_output_type == 'json_data' and not isinstance(output_data_to_save, str):
            try:
                output_data_to_save = json.dumps(output_data_to_save)
            except TypeError:
                output_data_to_save = str(output_data_to_save)
        elif not isinstance(output_data_to_save, (str, int, float, bool)) and output_data_to_save is not None:
            # For file paths, it's already a string. For other complex types, convert to string.
             if self.current_exec_output_type not in ['image_path', 'audio_path', 'video_path', 'file_path', 'url']:
                output_data_to_save = str(output_data_to_save)


        try:
            # results_manager.save_content should handle copying files if output_type is a path
            # and the path is temporary. For now, we assume it saves the path as is.
            results_manager.save_content(
                space_id=space_id,
                task_description=task_desc,
                parameters_json=parameters_json,
                output_data=output_data_to_save,
                output_type=self.current_exec_output_type,
                notes="" # Initially no notes from execution tab
            )
            QMessageBox.information(self, "Result Saved", f"Execution result for '{space_id}' saved to library.")
            self.load_results_from_db() # Refresh library view if it's visible
        except Exception as e:
            QMessageBox.critical(self, "Save to Library Failed", f"Could not save result: {e}")
            print(f"Error saving to library: {e}")


    # --- Methods for Results Library Tab ---
    def init_results_library_tab(self):
        rl_main_layout = QHBoxLayout(self.results_library_gb)

        # Left Side: Filters and Table
        left_panel_widget = QWidget()
        left_panel_layout = QVBoxLayout(left_panel_widget)

        filter_gb = QGroupBox("Filter Results")
        filter_layout = QFormLayout(filter_gb)
        self.rl_space_id_filter = QLineEdit()
        self.rl_space_id_filter.setPlaceholderText("Optional: author_name/space_name")
        filter_layout.addRow("Space ID:", self.rl_space_id_filter)
        self.rl_task_keyword_filter = QLineEdit()
        self.rl_task_keyword_filter.setPlaceholderText("Optional: keyword in task description")
        filter_layout.addRow("Task Keyword:", self.rl_task_keyword_filter)
        self.rl_output_type_filter = QComboBox()
        self.rl_output_type_filter.addItems(["Any", 'text', 'image_path', 'audio_path', 'video_path', 'json_data', 'file_path', 'url', 'error', 'other'])
        filter_layout.addRow("Output Type:", self.rl_output_type_filter)
        self.rl_filter_button = QPushButton("Filter Results")
        self.rl_filter_button.clicked.connect(self.handle_rl_filter_results)
        filter_layout.addRow(self.rl_filter_button)
        left_panel_layout.addWidget(filter_gb)

        results_table_gb = QGroupBox("Stored Results")
        results_table_layout = QVBoxLayout(results_table_gb)
        self.results_table_viewer = QTableWidget()
        self.results_table_viewer.setColumnCount(5)
        self.results_table_viewer.setHorizontalHeaderLabels(["ID", "Space ID", "Task (Summary)", "Output Type", "Timestamp"])
        self.results_table_viewer.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.results_table_viewer.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.results_table_viewer.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.results_table_viewer.itemSelectionChanged.connect(self.handle_results_table_selection)
        self.results_table_viewer.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.results_table_viewer.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents) # ID
        self.results_table_viewer.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents) # Output Type
        results_table_layout.addWidget(self.results_table_viewer)
        
        pagination_layout = QHBoxLayout()
        self.rl_prev_page_button = QPushButton("<< Previous")
        self.rl_prev_page_button.clicked.connect(self.handle_rl_prev_page)
        self.rl_page_label = QLabel(f"Page: {self.current_results_page + 1}")
        self.rl_next_page_button = QPushButton("Next >>")
        self.rl_next_page_button.clicked.connect(self.handle_rl_next_page)
        self.rl_limit_spinbox = QSpinBox()
        self.rl_limit_spinbox.setRange(5, 100)
        self.rl_limit_spinbox.setValue(self.results_per_page)
        self.rl_limit_spinbox.setToolTip("Results per page")
        self.rl_limit_spinbox.valueChanged.connect(self.handle_rl_limit_changed)
        pagination_layout.addWidget(self.rl_prev_page_button)
        pagination_layout.addStretch()
        pagination_layout.addWidget(self.rl_page_label)
        pagination_layout.addStretch()
        pagination_layout.addWidget(self.rl_next_page_button)
        pagination_layout.addWidget(QLabel("Per Page:"))
        pagination_layout.addWidget(self.rl_limit_spinbox)
        results_table_layout.addLayout(pagination_layout)
        left_panel_layout.addWidget(results_table_gb)

        # Right Side: Result Detail View
        self.rl_detail_area_group = QGroupBox("Selected Result Details")
        detail_view_main_layout = QVBoxLayout(self.rl_detail_area_group)
        self.rl_detail_area_group.setVisible(False)

        details_form_layout = QFormLayout()
        self.rl_id_label = QLabel()
        details_form_layout.addRow("ID:", self.rl_id_label)
        self.rl_space_id_label = QLabel()
        details_form_layout.addRow("Space ID:", self.rl_space_id_label)
        self.rl_timestamp_label = QLabel()
        details_form_layout.addRow("Timestamp:", self.rl_timestamp_label)
        self.rl_output_type_label = QLabel()
        details_form_layout.addRow("Output Type:", self.rl_output_type_label)
        self.rl_task_desc_text_viewer = QTextEdit()
        self.rl_task_desc_text_viewer.setReadOnly(True)
        self.rl_task_desc_text_viewer.setMaximumHeight(100)
        details_form_layout.addRow("Task Description:", self.rl_task_desc_text_viewer)
        self.rl_parameters_text_viewer = QTextEdit()
        self.rl_parameters_text_viewer.setReadOnly(True)
        self.rl_parameters_text_viewer.setMaximumHeight(100)
        details_form_layout.addRow("Parameters (JSON):", self.rl_parameters_text_viewer)
        detail_view_main_layout.addLayout(details_form_layout)

        output_data_gb = QGroupBox("Output Data")
        output_data_layout = QVBoxLayout(output_data_gb)
        self.rl_output_data_display_stack = QStackedWidget()
        # Page 0: Placeholder
        placeholder_label = QLabel("Select a result to view its content, or content type not displayable here.")
        placeholder_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.rl_output_data_display_stack.addWidget(placeholder_label)
        # Page 1: Text
        self.rl_output_text_view = QTextEdit()
        self.rl_output_text_view.setReadOnly(True)
        self.rl_output_data_display_stack.addWidget(self.rl_output_text_view)
        # Page 2: Image
        self.rl_output_image_view_scroll = QScrollArea()
        self.rl_output_image_view_scroll.setWidgetResizable(True)
        self.rl_output_image_label = QLabel()
        self.rl_output_image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.rl_output_image_view_scroll.setWidget(self.rl_output_image_label)
        self.rl_output_data_display_stack.addWidget(self.rl_output_image_view_scroll)
        # Page 3: Media/File Button
        self.rl_open_file_button_widget = QWidget()
        button_layout = QVBoxLayout(self.rl_open_file_button_widget)
        self.rl_open_file_button = QPushButton("Open File/Media")
        button_layout.addWidget(self.rl_open_file_button)
        button_layout.addStretch()
        self.rl_output_data_display_stack.addWidget(self.rl_open_file_button_widget)
        output_data_layout.addWidget(self.rl_output_data_display_stack)
        detail_view_main_layout.addWidget(output_data_gb)

        notes_gb = QGroupBox("Notes")
        notes_layout = QVBoxLayout(notes_gb)
        self.rl_notes_edit_area = QTextEdit()
        self.rl_notes_edit_area.setPlaceholderText("Add or edit notes here...")
        notes_layout.addWidget(self.rl_notes_edit_area)
        self.rl_save_notes_button = QPushButton("Save Notes")
        self.rl_save_notes_button.clicked.connect(self.handle_rl_save_notes)
        notes_layout.addWidget(self.rl_save_notes_button)
        detail_view_main_layout.addWidget(notes_gb)

        self.rl_delete_result_button = QPushButton("Delete Selected Result")
        self.rl_delete_result_button.setStyleSheet("background-color: #d32f2f; color: white;")
        self.rl_delete_result_button.clicked.connect(self.handle_rl_delete_result)
        detail_view_main_layout.addWidget(self.rl_delete_result_button)
        detail_view_main_layout.addStretch()

        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        main_splitter.addWidget(left_panel_widget)
        main_splitter.addWidget(self.rl_detail_area_group)
        main_splitter.setSizes([450, 550])
        rl_main_layout.addWidget(main_splitter)

        self.load_results_from_db()

    def load_results_from_db(self, page_to_load=None):
        if page_to_load is not None:
            self.current_results_page = page_to_load
        
        offset = self.current_results_page * self.results_per_page
        limit = self.results_per_page

        space_id = self.rl_space_id_filter.text().strip() or None
        task_keyword = self.rl_task_keyword_filter.text().strip() or None
        output_type = self.rl_output_type_filter.currentText()
        if output_type == "Any":
            output_type = None

        try:
            records = results_manager.filter_content(
                output_type=output_type,
                space_id=space_id,
                task_keyword=task_keyword,
                limit=limit,
                offset=offset
            )
            self.results_table_viewer.setRowCount(0)

            if not records:
                if self.current_results_page > 0: 
                    self.current_results_page -=1 
                    # self.load_results_from_db() # Avoid potential infinite loop if last page is empty
                    self.rl_page_label.setText(f"Page: {self.current_results_page + 1}") # Update label
                    QMessageBox.information(self, "No More Results", "You have reached the last page of results for the current filter.")
                    self.rl_next_page_button.setEnabled(False)
                    return
                else:
                    QMessageBox.information(self, "No Results", "No results found for the current filters.")
            
            for row, record in enumerate(records):
                self.results_table_viewer.insertRow(row)
                self.results_table_viewer.setItem(row, 0, QTableWidgetItem(str(record.get('id', 'N/A'))))
                self.results_table_viewer.setItem(row, 1, QTableWidgetItem(str(record.get('space_id', 'N/A'))))
                
                task_desc_full = str(record.get('task_description', 'N/A'))
                task_desc_summary = (task_desc_full[:75] + '...') if len(task_desc_full) > 75 else task_desc_full
                self.results_table_viewer.setItem(row, 2, QTableWidgetItem(task_desc_summary))
                
                self.results_table_viewer.setItem(row, 3, QTableWidgetItem(str(record.get('output_type', 'N/A'))))
                self.results_table_viewer.setItem(row, 4, QTableWidgetItem(str(record.get('timestamp', 'N/A'))))
            
            self.results_table_viewer.resizeColumnsToContents()
            self.results_table_viewer.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)

            self.rl_page_label.setText(f"Page: {self.current_results_page + 1}")
            self.rl_prev_page_button.setEnabled(self.current_results_page > 0)
            self.rl_next_page_button.setEnabled(len(records) == limit)

        except Exception as e:
            QMessageBox.critical(self, "Database Error", f"Error loading results: {e}")
            print(f"Error loading results: {e}")

    def handle_rl_filter_results(self):
        self.load_results_from_db(page_to_load=0)

    def handle_rl_next_page(self):
        self.load_results_from_db(page_to_load=self.current_results_page + 1)

    def handle_rl_prev_page(self):
        if self.current_results_page > 0:
            self.load_results_from_db(page_to_load=self.current_results_page - 1)
            
    def handle_rl_limit_changed(self, value):
        self.results_per_page = value
        self.load_results_from_db(page_to_load=0)

    def handle_results_table_selection(self):
        selected_rows = self.results_table_viewer.selectionModel().selectedRows()
        if not selected_rows:
            self.rl_detail_area_group.setVisible(False)
            self.selected_content_id_in_library = None
            return

        selected_row_index = selected_rows[0].row()
        try:
            self.selected_content_id_in_library = int(self.results_table_viewer.item(selected_row_index, 0).text())
        except (ValueError, TypeError):
            QMessageBox.warning(self, "Selection Error", "Invalid ID for selected row.")
            self.selected_content_id_in_library = None
            return

        record = results_manager.get_content_by_id(self.selected_content_id_in_library)

        if record:
            self.rl_id_label.setText(str(record.get('id', 'N/A')))
            self.rl_space_id_label.setText(record.get('space_id', 'N/A'))
            self.rl_task_desc_text_viewer.setText(record.get('task_description', 'N/A'))
            self.rl_timestamp_label.setText(record.get('timestamp', 'N/A'))
            self.rl_output_type_label.setText(record.get('output_type', 'N/A'))
            
            params_data = record.get('parameters')
            if isinstance(params_data, str): # If stored as JSON string
                try:
                    params_dict = json.loads(params_data)
                    self.rl_parameters_text_viewer.setText(json.dumps(params_dict, indent=2))
                except json.JSONDecodeError:
                    self.rl_parameters_text_viewer.setText(params_data) # Show as is
            elif isinstance(params_data, dict): # If already a dict (e.g. from older saves)
                 self.rl_parameters_text_viewer.setText(json.dumps(params_data, indent=2))
            else:
                 self.rl_parameters_text_viewer.setText(str(params_data))

            self.rl_notes_edit_area.setText(record.get('notes', ''))
            self.update_output_data_display(record)
            self.rl_detail_area_group.setVisible(True)
        else:
            QMessageBox.warning(self, "Error", f"Could not retrieve details for ID {self.selected_content_id_in_library}.")
            self.rl_detail_area_group.setVisible(False)
            self.selected_content_id_in_library = None

    def update_output_data_display(self, record):
        output_type = record.get('output_type', 'other').lower()
        output_data = record.get('output_data', '')

        self.rl_open_file_button.disconnect() 
        
        if output_type == 'text' or output_type == 'error':
            self.rl_output_text_view.setText(str(output_data))
            self.rl_output_data_display_stack.setCurrentWidget(self.rl_output_text_view)
        elif output_type == 'json_data':
            try:
                # Assuming output_data is a string that needs parsing for pretty print
                # Or it could already be a dict/list if not stored as string
                if isinstance(output_data, str):
                    parsed_json = json.loads(output_data)
                    self.rl_output_text_view.setText(json.dumps(parsed_json, indent=2))
                elif isinstance(output_data, (dict, list)): # If it was already structured
                     self.rl_output_text_view.setText(json.dumps(output_data, indent=2))
                else:
                    self.rl_output_text_view.setText(str(output_data)) # Fallback
            except (json.JSONDecodeError, TypeError):
                self.rl_output_text_view.setText(str(output_data)) # Show as is if not valid JSON string or error
            self.rl_output_data_display_stack.setCurrentWidget(self.rl_output_text_view)

        elif output_type == 'image_path':
            if output_data and os.path.exists(str(output_data)):
                pixmap = QPixmap(str(output_data))
                if pixmap.isNull():
                    self.rl_output_image_label.setText(f"Error loading image (or not an image):\n{output_data}")
                else:
                    max_h = self.rl_output_image_view_scroll.height() - 20
                    if pixmap.height() > max_h and max_h > 0:
                        pixmap = pixmap.scaledToHeight(max_h, Qt.TransformationMode.SmoothTransformation)
                    self.rl_output_image_label.setPixmap(pixmap)
                self.rl_output_data_display_stack.setCurrentWidget(self.rl_output_image_view_scroll)
            else:
                self.rl_output_image_label.setText(f"Image file not found:\n{output_data}")
                self.rl_output_data_display_stack.setCurrentWidget(self.rl_output_image_view_scroll)
        
        elif output_type in ['audio_path', 'video_path', 'file_path', 'url']:
            base_name = os.path.basename(str(output_data)) if output_data else "N/A"
            self.rl_open_file_button.setText(f"Open {output_type.replace('_path','').capitalize()}: {base_name}")
            if output_data:
                self.rl_open_file_button.clicked.connect(lambda checked=False, path=str(output_data), url=(output_type=='url'): self.handle_rl_open_output_file(path, is_url=url))
            self.rl_output_data_display_stack.setCurrentWidget(self.rl_open_file_button_widget)
        else: # Fallback to placeholder
            self.rl_output_data_display_stack.setCurrentIndex(0) 

    def handle_rl_open_output_file(self, file_path_or_url: str, is_url=False):
        if not file_path_or_url:
            QMessageBox.warning(self, "No Path", "No file path or URL provided.")
            return
        
        if is_url:
            qurl = QUrl(file_path_or_url)
            if not qurl.isValid() or qurl.scheme() not in ['http', 'https']:
                 # Try adding scheme if missing
                 qurl = QUrl("http://" + file_path_or_url)
                 if not qurl.isValid():
                     QMessageBox.warning(self, "Invalid URL", f"The URL '{file_path_or_url}' is not valid.")
                     return
        else:
            if not os.path.exists(file_path_or_url):
                QMessageBox.warning(self, "File Not Found", f"The file\n{file_path_or_url}\nwas not found.")
                return
            qurl = QUrl.fromLocalFile(file_path_or_url)
        
        if not QDesktopServices.openUrl(qurl):
            QMessageBox.warning(self, "Open Failed", f"Could not open file/URL:\n{file_path_or_url}")

    def handle_rl_save_notes(self):
        if self.selected_content_id_in_library is None:
            QMessageBox.warning(self, "No Result Selected", "Please select a result to save notes for.")
            return
        
        notes = self.rl_notes_edit_area.toPlainText()
        if results_manager.update_content_notes(self.selected_content_id_in_library, notes):
            QMessageBox.information(self, "Success", "Notes updated successfully.")
            # Re-select to refresh the view, which includes notes
            current_selection = self.results_table_viewer.selectionModel().selectedRows()
            self.handle_results_table_selection() # This will re-load and re-populate
            if current_selection: # Try to restore selection if possible (might not be exact if list changes)
                # This simple re-selection might not work perfectly if the table order changes.
                # A more robust way would be to find the item by ID after reload.
                self.results_table_viewer.selectRow(current_selection[0].row())

        else:
            QMessageBox.critical(self, "Error", "Failed to update notes.")

    def handle_rl_delete_result(self):
        if self.selected_content_id_in_library is None:
            QMessageBox.warning(self, "No Result Selected", "Please select a result to delete.")
            return

        confirm = QMessageBox.question(self, "Confirm Deletion",
                                       f"Are you sure you want to delete result ID {self.selected_content_id_in_library}?",
                                       QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if confirm == QMessageBox.StandardButton.Yes:
            if results_manager.delete_content(self.selected_content_id_in_library):
                QMessageBox.information(self, "Success", f"Result ID {self.selected_content_id_in_library} deleted.")
                self.selected_content_id_in_library = None
                self.rl_detail_area_group.setVisible(False)
                self.load_results_from_db(page_to_load=self.current_results_page)
            else:
                QMessageBox.critical(self, "Error", "Failed to delete result.")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    results_manager.init_db() # Initialize database schema if not exists
    main_window = SpacesUI()
    main_window.show()
    sys.exit(app.exec())
