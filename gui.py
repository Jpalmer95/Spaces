import sys
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QTabWidget, QGroupBox,
    QLabel, QLineEdit, QComboBox, QSpinBox, QPushButton, QTableWidget,
    QTableWidgetItem, QListWidget, QListWidgetItem, QHBoxLayout, QMessageBox, QHeaderView,
    QSplitter, QScrollArea, QFormLayout, QFileDialog, QCheckBox, QInputDialog,
    QMenu, QStackedWidget
)
from PyQt6.QtGui import QPalette, QColor, QAction, QDesktopServices, QPixmap
from PyQt6.QtCore import Qt, pyqtSignal, QUrl

import re # For parsing API details
import json # For parameters if fallback or for DB
# Assuming space_finder.py is in the same directory or accessible in PYTHONPATH
import space_finder
import space_runner # For Space Execution tab
import results_manager # For saving results to DB
from huggingface_hub import SpaceInfo # For type hinting if needed, and accessing attributes
from gradio_client import handle_file # For file parameters

class SpacesUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Spaces UI")
        self.setGeometry(100, 100, 900, 700) # Increased size for more content

        # Apply dark theme (same as before)
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor(53, 53, 53))
        palette.setColor(QPalette.ColorRole.WindowText, QColor(255, 255, 255))
        palette.setColor(QPalette.ColorRole.Base, QColor(25, 25, 25))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor(53, 53, 53))
        palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(255, 255, 255))
        palette.setColor(QPalette.ColorRole.ToolTipText, QColor(255, 255, 255))
        palette.setColor(QPalette.ColorRole.Text, QColor(255, 255, 255))
        palette.setColor(QPalette.ColorRole.Button, QColor(42, 130, 218)) # Blue buttons
        palette.setColor(QPalette.ColorRole.ButtonText, QColor(255, 255, 255))
        palette.setColor(QPalette.ColorRole.BrightText, QColor(255, 0, 0))
        palette.setColor(QPalette.ColorRole.Link, QColor(42, 130, 218))
        palette.setColor(QPalette.ColorRole.Highlight, QColor(42, 130, 218))
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor(0, 0, 0)) # Black text on highlight
        self.setPalette(palette)

        # Central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # Tab widget for main sections
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)

        # --- Space Discovery Tab ---
        self.space_discovery_gb = QGroupBox("Space Discovery") # Changed from QWidget to QGroupBox
        self.tab_widget.addTab(self.space_discovery_gb, "Space Discovery")
        self.init_space_discovery_tab()

        # --- Placeholder for Results Library Tab ---
        self.results_library_tab = QGroupBox("Results Library")
        self.tab_widget.addTab(self.results_library_tab, "Results Library")
        # TODO: Add placeholder content or setup method for Results Library

        # --- Space Execution Tab ---
        self.space_execution_gb = QGroupBox("Space Execution")
        self.tab_widget.addTab(self.space_execution_gb, "Space Execution")
        self.init_space_execution_tab()

        # --- Results Library Tab ---
        self.results_library_gb = QGroupBox("Results Library") # Changed from self.results_library_tab
        self.tab_widget.addTab(self.results_library_gb, "Results Library")
        self.init_results_library_tab()
        
        self.current_selected_space_id = None # To store ID from selected search result in Discovery tab
        self.dynamic_input_widgets = {} # For Space Execution tab
        self.current_loaded_space_api_details = None # Store raw API details for reparsing if needed
        self.current_results_page = 0
        self.results_per_page = 15 # Default, can be changed by spinbox
        self.selected_content_id_in_library = None


    def init_space_discovery_tab(self):
        # Using existing GroupBox from __init__
        discovery_layout = QVBoxLayout(self.space_discovery_gb) 

        # --- Search Section ---
        # Ensure these widgets are class members, initialized in __init__ or here if not already done
        if not hasattr(self, 'task_input'): self.task_input = QLineEdit()
        self.task_input.setPlaceholderText("e.g., text generation, image classification")
        if not hasattr(self, 'sort_combo'): self.sort_combo = QComboBox()
        self.sort_combo.addItems(["likes", "updatedAt", "downloads"]) # Ensure items are not added multiple times
        if not hasattr(self, 'limit_spinbox'): self.limit_spinbox = QSpinBox()
        self.limit_spinbox.setRange(1, 100)
        self.limit_spinbox.setValue(10)
        if not hasattr(self, 'search_button'): self.search_button = QPushButton("Search Spaces")
        
        search_section_gb = QGroupBox("Find Spaces")
        search_form_layout = QFormLayout()
        search_section_gb.setLayout(search_form_layout)
        search_form_layout.addRow(QLabel("Task Description:"), self.task_input)
        search_form_layout.addRow(QLabel("Sort by:"), self.sort_combo)
        search_form_layout.addRow(QLabel("Limit:"), self.limit_spinbox)
        search_form_layout.addRow(self.search_button)
        self.search_button.clicked.connect(self.handle_search_spaces)
        discovery_layout.addWidget(search_section_gb)

        # --- Search Results Section ---
        if not hasattr(self, 'results_table'): self.results_table = QTableWidget()
        results_section_gb = QGroupBox("Search Results")
        results_layout = QVBoxLayout()
        results_section_gb.setLayout(results_layout)
        results_layout.addWidget(self.results_table) # Add table to its layout

        self.results_table = QTableWidget()
        self.results_table.setColumnCount(4)
        self.results_table.setHorizontalHeaderLabels(["Space ID", "Author", "Likes", "Task"])
        self.results_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.results_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.results_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.results_table.itemSelectionChanged.connect(self.handle_search_result_selection)
        self.results_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.results_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        discovery_layout.addWidget(results_section_gb)

        # --- Favorites Section ---
        if not hasattr(self, 'favorites_list_widget'): self.favorites_list_widget = QListWidget()
        if not hasattr(self, 'add_to_fav_button'): self.add_to_fav_button = QPushButton("Add Search Result to Favorites")
        self.add_to_fav_button.setEnabled(False) # Default
        if not hasattr(self, 'remove_fav_button'): self.remove_fav_button = QPushButton("Remove Selected Favorite from List")
        if not hasattr(self, 'refresh_fav_button'): self.refresh_fav_button = QPushButton("Refresh Favorites List")

        favorites_section_gb = QGroupBox("Favorite Spaces")
        favorites_layout = QVBoxLayout()
        favorites_section_gb.setLayout(favorites_layout)
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
    # Ensure methods are defined before they are connected to signals.
    # handle_search_spaces, handle_search_result_selection, etc. are assumed to be defined below this.

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
                # self.search_button.setEnabled(True) # Handled in finally
                # self.search_button.setText("Search Spaces")
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
                        task_tags_list.extend([str(t) for t in card_tags])
                
                task_tags_str = ", ".join(list(set(task_tags_list))) if task_tags_list else "N/A"

                self.results_table.setItem(row, 0, QTableWidgetItem(str(space_id)))
                self.results_table.setItem(row, 1, QTableWidgetItem(str(author)))
                self.results_table.setItem(row, 2, QTableWidgetItem(str(likes)))
                self.results_table.setItem(row, 3, QTableWidgetItem(task_tags_str))
            
            self.results_table.resizeColumnsToContents()

        except Exception as e:
            QMessageBox.critical(self, "Search Failed", f"An error occurred during search: {e}")
        finally:
            self.search_button.setEnabled(True)
            self.search_button.setText("Search Spaces")

    def handle_search_result_selection(self):
        selected_rows = self.results_table.selectionModel().selectedRows()
        if selected_rows:
            # Get item from first column of the selected row
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
                placeholder_item.setData(Qt.ItemDataRole.UserRole, "placeholder") # Mark as placeholder
                self.favorites_list_widget.addItem(placeholder_item)
        except Exception as e:
            QMessageBox.warning(self, "Favorites Error", f"Could not load favorites: {e}")
            error_item = QListWidgetItem("Error loading favorites.")
            error_item.setData(Qt.ItemDataRole.UserRole, "placeholder") # Mark as placeholder
            self.favorites_list_widget.addItem(error_item)

    def handle_add_to_favorites(self):
        if not self.current_selected_space_id:
            QMessageBox.warning(self, "Add Favorite Error", "No space selected from search results.")
            return
        
        try:
            space_finder.add_to_favorites(self.current_selected_space_id)
            # QMessageBox.information(self, "Favorite Added", f"Space '{self.current_selected_space_id}' added to favorites.")
            self.refresh_favorites_list() # Refresh the list in this tab
            # Optionally, refresh the favorites list in the Execution tab if it's already loaded
            if hasattr(self, 'load_favorites_exec_button'):
                 # This is a simple way to indicate a change; more robust would be a signal/slot
                self.load_favorites_exec_button.setToolTip("Favorites updated. Click to see new list.")

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
                if hasattr(self, 'load_favorites_exec_button'):
                    self.load_favorites_exec_button.setToolTip("Favorites updated. Click to see new list.")
            except Exception as e:
                QMessageBox.critical(self, "Remove Favorite Failed", f"Could not remove favorite: {e}")

    # --- Methods for Space Execution Tab ---
    # Ensure all widgets like self.space_id_input_exec, self.load_api_button, etc. are initialized
    # as class members before being used in init_space_execution_tab or connected to signals.
    # This is crucial if they were defined locally in previous versions.
    # For brevity, assuming these are correctly defined as members.
    # ... (Space Execution methods)

    def init_space_execution_tab(self):
        # This method is called after self.space_execution_gb is created and added to the tab widget
        layout = QVBoxLayout(self.space_execution_gb) # Set layout directly on the groupbox
        
        # Placeholder content
        placeholder_label = QLabel("Space Execution Content Placeholder - To be implemented")
        placeholder_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(placeholder_label)
        
        # You can add more specific widgets here if their members (e.g. self.some_button_exec)
        # are already initialized in __init__. For now, a placeholder is sufficient.
        # For example:
        # self.some_specific_widget_for_exec_tab = QLineEdit()
        # layout.addWidget(self.some_specific_widget_for_exec_tab)

        self.space_execution_gb.setLayout(layout) # Ensure the layout is set on the groupbox

    # --- Methods for Results Library Tab ---
    def init_results_library_tab(self):
        rl_main_layout = QHBoxLayout(self.results_library_gb) # Main layout for the tab (changed to QHBox for splitter)

        # --- Left Side: Filters and Table ---
        left_panel_widget = QWidget()
        left_panel_layout = QVBoxLayout(left_panel_widget)

        # Filter Controls
        filter_gb = QGroupBox("Filter Results")
        filter_layout = QFormLayout()
        filter_gb.setLayout(filter_layout)

        self.rl_space_id_filter = QLineEdit()
        self.rl_space_id_filter.setPlaceholderText("Optional: author_name/space_name")
        filter_layout.addRow("Space ID:", self.rl_space_id_filter)

        self.rl_task_keyword_filter = QLineEdit()
        self.rl_task_keyword_filter.setPlaceholderText("Optional: keyword in task description")
        filter_layout.addRow("Task Keyword:", self.rl_task_keyword_filter)

        self.rl_output_type_filter = QComboBox()
        self.rl_output_type_filter.addItems(["Any", 'text', 'image_path', 'audio_path', 'video_path', 'json_data', 'file_path', 'url', 'other'])
        filter_layout.addRow("Output Type:", self.rl_output_type_filter)
        
        self.rl_filter_button = QPushButton("Filter Results")
        self.rl_filter_button.clicked.connect(self.handle_rl_filter_results)
        filter_layout.addRow(self.rl_filter_button)
        left_panel_layout.addWidget(filter_gb)

        # Results Table
        results_table_gb = QGroupBox("Stored Results")
        results_table_layout = QVBoxLayout()
        results_table_gb.setLayout(results_table_layout)

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
        
        # Pagination Controls
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

        # --- Right Side: Result Detail View ---
        self.rl_detail_area_group = QGroupBox("Selected Result Details")
        detail_view_main_layout = QVBoxLayout(self.rl_detail_area_group)
        self.rl_detail_area_group.setVisible(False) # Hide until a result is selected

        # Metadata display using QFormLayout
        details_form_layout = QFormLayout()
        self.rl_id_label = QLabel()
        details_form_layout.addRow("ID:", self.rl_id_label)
        self.rl_space_id_label = QLabel() # Using QLabel for non-editable fields
        details_form_layout.addRow("Space ID:", self.rl_space_id_label)
        self.rl_timestamp_label = QLabel()
        details_form_layout.addRow("Timestamp:", self.rl_timestamp_label)
        self.rl_output_type_label = QLabel()
        details_form_layout.addRow("Output Type:", self.rl_output_type_label)
        
        self.rl_task_desc_text_viewer = QTextEdit() # Renamed to avoid conflict
        self.rl_task_desc_text_viewer.setReadOnly(True)
        self.rl_task_desc_text_viewer.setMaximumHeight(100) # Limit height
        details_form_layout.addRow("Task Description:", self.rl_task_desc_text_viewer)
        
        self.rl_parameters_text_viewer = QTextEdit() # Renamed
        self.rl_parameters_text_viewer.setReadOnly(True)
        self.rl_parameters_text_viewer.setMaximumHeight(100)
        details_form_layout.addRow("Parameters (JSON):", self.rl_parameters_text_viewer)
        detail_view_main_layout.addLayout(details_form_layout)

        # Output Data Display Area
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
        self.rl_output_image_view_scroll = QScrollArea() # Scroll for large images
        self.rl_output_image_view_scroll.setWidgetResizable(True)
        self.rl_output_image_label = QLabel() # Renamed
        self.rl_output_image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.rl_output_image_view_scroll.setWidget(self.rl_output_image_label)
        self.rl_output_data_display_stack.addWidget(self.rl_output_image_view_scroll)
        # Page 3: Media/File Button
        self.rl_open_file_button_widget = QWidget() # Container for the button
        button_layout = QVBoxLayout(self.rl_open_file_button_widget)
        self.rl_open_file_button = QPushButton("Open File/Media") # Renamed
        button_layout.addWidget(self.rl_open_file_button)
        button_layout.addStretch()
        self.rl_output_data_display_stack.addWidget(self.rl_open_file_button_widget)
        output_data_layout.addWidget(self.rl_output_data_display_stack)
        detail_view_main_layout.addWidget(output_data_gb)


        # Notes Area
        notes_gb = QGroupBox("Notes")
        notes_layout = QVBoxLayout(notes_gb)
        self.rl_notes_edit_area = QTextEdit()
        self.rl_notes_edit_area.setPlaceholderText("Add or edit notes here...")
        notes_layout.addWidget(self.rl_notes_edit_area)
        self.rl_save_notes_button = QPushButton("Save Notes")
        self.rl_save_notes_button.clicked.connect(self.handle_rl_save_notes)
        notes_layout.addWidget(self.rl_save_notes_button)
        detail_view_main_layout.addWidget(notes_gb)

        # Delete Button
        self.rl_delete_result_button = QPushButton("Delete Selected Result")
        self.rl_delete_result_button.setStyleSheet("background-color: #d32f2f; color: white;") # Warning color
        self.rl_delete_result_button.clicked.connect(self.handle_rl_delete_result)
        detail_view_main_layout.addWidget(self.rl_delete_result_button)
        detail_view_main_layout.addStretch() # Push content up

        # Splitter
        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        main_splitter.addWidget(left_panel_widget)
        main_splitter.addWidget(self.rl_detail_area_group)
        main_splitter.setSizes([400, 500]) # Initial sizes for left and right panels
        rl_main_layout.addWidget(main_splitter)

        # Initial load
        self.load_results_from_db()


    def load_results_from_db(self, page_to_load=None):
        if page_to_load is not None:
            self.current_results_page = page_to_load
        
        offset = self.current_results_page * self.results_per_page
        limit = self.results_per_page # self.rl_limit_spinbox.value()

        space_id = self.rl_space_id_filter.text().strip() or None
        task_keyword = self.rl_task_keyword_filter.text().strip() or None
        output_type = self.rl_output_type_filter.currentText()
        if output_type == "Any":
            output_type = None

        try:
            # results_manager.init_db() # Ensure DB is available
            records = results_manager.filter_content(
                output_type=output_type,
                space_id=space_id,
                task_keyword=task_keyword,
                limit=limit,
                offset=offset
            )
            self.results_table_viewer.setRowCount(0) # Clear table

            if not records:
                # If not on page 0 and no records, might mean we went past the last page
                if self.current_results_page > 0: 
                    self.current_results_page -=1 # Go back one page
                    self.load_results_from_db() # And reload
                    return
                else: # No records at all for this filter on page 0
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
            self.results_table_viewer.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch) # Task summary stretch

            self.rl_page_label.setText(f"Page: {self.current_results_page + 1}")
            self.rl_prev_page_button.setEnabled(self.current_results_page > 0)
            # Next button enabled if we got a full page of results, implying there might be more
            self.rl_next_page_button.setEnabled(len(records) == limit)


        except Exception as e:
            QMessageBox.critical(self, "Database Error", f"Error loading results: {e}")
            print(f"Error loading results: {e}") # Also print to console

    def handle_rl_filter_results(self):
        self.load_results_from_db(page_to_load=0) # Reset to first page on new filter

    def handle_rl_next_page(self):
        self.load_results_from_db(page_to_load=self.current_results_page + 1)

    def handle_rl_prev_page(self):
        if self.current_results_page > 0:
            self.load_results_from_db(page_to_load=self.current_results_page - 1)
            
    def handle_rl_limit_changed(self, value):
        self.results_per_page = value
        self.load_results_from_db(page_to_load=0) # Reset to first page as limit changed

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

        # results_manager.init_db() # Ensure DB
        record = results_manager.get_content_by_id(self.selected_content_id_in_library)

        if record:
            self.rl_id_label.setText(str(record.get('id', 'N/A')))
            self.rl_space_id_label.setText(record.get('space_id', 'N/A'))
            self.rl_task_desc_text_viewer.setText(record.get('task_description', 'N/A'))
            self.rl_timestamp_label.setText(record.get('timestamp', 'N/A'))
            self.rl_output_type_label.setText(record.get('output_type', 'N/A'))
            
            params = record.get('parameters') # Already a dict from _dict_factory
            if isinstance(params, dict):
                 try:
                    self.rl_parameters_text_viewer.setText(json.dumps(params, indent=2))
                 except TypeError: # handle non-serializable if any (should not happen with json.dumps)
                    self.rl_parameters_text_viewer.setText(str(params))
            elif isinstance(params, str): # If it was stored as a string initially
                 self.rl_parameters_text_viewer.setText(params) # Assume it's pre-formatted or just show as is
            else:
                 self.rl_parameters_text_viewer.setText(str(params))


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

        self.rl_open_file_button.disconnect() # Disconnect previous signals
        
        if output_type == 'text':
            self.rl_output_text_view.setText(output_data)
            self.rl_output_data_display_stack.setCurrentWidget(self.rl_output_text_view)
        elif output_type == 'json_data':
            try:
                # Assuming output_data is a string that needs parsing for pretty print
                parsed_json = json.loads(output_data)
                self.rl_output_text_view.setText(json.dumps(parsed_json, indent=2))
            except json.JSONDecodeError:
                self.rl_output_text_view.setText(output_data) # Show as is if not valid JSON string
            except TypeError: # If output_data was already a dict/list (should be string from DB)
                 self.rl_output_text_view.setText(json.dumps(output_data, indent=2))
            self.rl_output_data_display_stack.setCurrentWidget(self.rl_output_text_view)

        elif output_type == 'image_path':
            if os.path.exists(output_data):
                pixmap = QPixmap(output_data)
                if pixmap.isNull():
                    self.rl_output_image_label.setText(f"Error loading image (or not an image):\n{output_data}")
                else:
                    # Scale pixmap if too large, preserving aspect ratio
                    max_h = 400 # Max height for image preview
                    if pixmap.height() > max_h:
                        pixmap = pixmap.scaledToHeight(max_h, Qt.TransformationMode.SmoothTransformation)
                    self.rl_output_image_label.setPixmap(pixmap)
                self.rl_output_data_display_stack.setCurrentWidget(self.rl_output_image_view_scroll)
            else:
                self.rl_output_image_label.setText(f"Image file not found:\n{output_data}")
                self.rl_output_data_display_stack.setCurrentWidget(self.rl_output_image_view_scroll)
        
        elif output_type in ['audio_path', 'video_path', 'file_path', 'url', 'other']:
            self.rl_open_file_button.setText(f"Open {output_type.replace('_path','').capitalize()}: {os.path.basename(output_data)}")
            self.rl_open_file_button.clicked.connect(lambda: self.handle_rl_open_output_file(output_data, is_url=(output_type=='url')))
            self.rl_output_data_display_stack.setCurrentWidget(self.rl_open_file_button_widget)
        else: # Fallback to placeholder
            self.rl_output_data_display_stack.setCurrentIndex(0) # Placeholder widget

    def handle_rl_open_output_file(self, file_path_or_url: str, is_url=False):
        if not file_path_or_url:
            QMessageBox.warning(self, "No Path", "No file path or URL provided.")
            return
        
        if is_url:
            qurl = QUrl(file_path_or_url)
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
        # results_manager.init_db() # Ensure DB
        if results_manager.update_content_notes(self.selected_content_id_in_library, notes):
            QMessageBox.information(self, "Success", "Notes updated successfully.")
            # Optionally, refresh the currently displayed record's notes if you don't re-fetch all details
            # For simplicity, the user can re-select the item or we can re-fetch.
            # Let's re-fetch to ensure consistency:
            self.handle_results_table_selection() # This will re-load and re-populate
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
            # results_manager.init_db() # Ensure DB
            if results_manager.delete_content(self.selected_content_id_in_library):
                QMessageBox.information(self, "Success", f"Result ID {self.selected_content_id_in_library} deleted.")
                self.selected_content_id_in_library = None
                self.rl_detail_area_group.setVisible(False) # Hide details panel
                self.load_results_from_db(page_to_load=self.current_results_page) # Refresh table
            else:
                QMessageBox.critical(self, "Error", "Failed to delete result.")


if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyle("Fusion") 
    results_manager.init_db()
    main_window = SpacesUI() 
    main_window.show()
    sys.exit(app.exec())

import os # For os.path.exists
# No need for duplicate QGridLayout import
