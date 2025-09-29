import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from PIL import Image, ImageTk
import os
import threading
from typing import List, Dict, Optional, Tuple
import logging
from database_manager import DatabaseManager
from photo_manager import PhotoManager
from face_recognition_engine import FaceRecognitionEngine

class PhotoSearchGUI:
    """
    Main GUI application for the face-based photo search system.
    """
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Face-Based Photo Search & Management System")
        self.root.geometry("1200x800")
        self.root.minsize(800, 600)
        
        # Initialize backend components
        self.db_manager = DatabaseManager()
        self.photo_manager = PhotoManager(self.db_manager)
        self.face_engine = FaceRecognitionEngine()
        
        # GUI state variables
        self.selected_image_path = None
        self.detected_faces = []
        self.selected_face_encoding = None
        self.search_results = []
        self.selected_results = []
        
        # Setup logging
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        
        self.setup_gui()
        self.load_search_folders()
        
    def setup_gui(self):
        """
        Setup the main GUI layout.
        """
        # Create main notebook for tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create tabs
        self.setup_search_tab()
        self.setup_manage_tab()
        self.setup_settings_tab()
        
    def setup_search_tab(self):
        """
        Setup the main search tab.
        """
        search_frame = ttk.Frame(self.notebook)
        self.notebook.add(search_frame, text="Face Search")
        
        # Left panel - Image selection and face detection
        left_panel = ttk.LabelFrame(search_frame, text="Select Reference Image", padding=10)
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=False, padx=(0, 5))
        
        # Image selection
        ttk.Button(left_panel, text="Select Image", command=self.select_reference_image).pack(pady=5)
        
        # Image display
        self.image_label = ttk.Label(left_panel, text="No image selected")
        self.image_label.pack(pady=10)
        
        # Face selection frame
        face_frame = ttk.LabelFrame(left_panel, text="Detected Faces", padding=5)
        face_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # Scrollable frame for faces
        self.face_canvas = tk.Canvas(face_frame, height=200)
        face_scrollbar = ttk.Scrollbar(face_frame, orient="vertical", command=self.face_canvas.yview)
        self.face_scrollable_frame = ttk.Frame(self.face_canvas)
        
        self.face_scrollable_frame.bind(
            "<Configure>",
            lambda e: self.face_canvas.configure(scrollregion=self.face_canvas.bbox("all"))
        )
        
        self.face_canvas.create_window((0, 0), window=self.face_scrollable_frame, anchor="nw")
        self.face_canvas.configure(yscrollcommand=face_scrollbar.set)
        
        self.face_canvas.pack(side="left", fill="both", expand=True)
        face_scrollbar.pack(side="right", fill="y")
        
        # Search button
        self.search_button = ttk.Button(left_panel, text="Search Similar Faces", 
                                       command=self.search_similar_faces, state=tk.DISABLED)
        self.search_button.pack(pady=10)
        
        # Right panel - Search results
        right_panel = ttk.LabelFrame(search_frame, text="Search Results", padding=10)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))
        
        # Results toolbar
        results_toolbar = ttk.Frame(right_panel)
        results_toolbar.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Button(results_toolbar, text="Select All", command=self.select_all_results).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(results_toolbar, text="Clear Selection", command=self.clear_selection).pack(side=tk.LEFT, padx=(0, 5))
        
        # File operations
        ttk.Separator(results_toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=10)
        ttk.Button(results_toolbar, text="Copy Selected", command=self.copy_selected_files).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(results_toolbar, text="Move Selected", command=self.move_selected_files).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(results_toolbar, text="Delete Selected", command=self.delete_selected_files).pack(side=tk.LEFT, padx=(0, 5))
        
        # Results display
        self.results_frame = ttk.Frame(right_panel)
        self.results_frame.pack(fill=tk.BOTH, expand=True)
        
        # Results canvas with scrollbar
        self.results_canvas = tk.Canvas(self.results_frame)
        results_scrollbar = ttk.Scrollbar(self.results_frame, orient="vertical", command=self.results_canvas.yview)
        self.results_scrollable_frame = ttk.Frame(self.results_canvas)
        
        self.results_scrollable_frame.bind(
            "<Configure>",
            lambda e: self.results_canvas.configure(scrollregion=self.results_canvas.bbox("all"))
        )
        
        self.results_canvas.create_window((0, 0), window=self.results_scrollable_frame, anchor="nw")
        self.results_canvas.configure(yscrollcommand=results_scrollbar.set)
        
        self.results_canvas.pack(side="left", fill="both", expand=True)
        results_scrollbar.pack(side="right", fill="y")
        
    def setup_manage_tab(self):
        """
        Setup the folder management tab.
        """
        manage_frame = ttk.Frame(self.notebook)
        self.notebook.add(manage_frame, text="Folder Management")
        
        # Folder list
        folder_frame = ttk.LabelFrame(manage_frame, text="Search Folders", padding=10)
        folder_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Folder toolbar
        folder_toolbar = ttk.Frame(folder_frame)
        folder_toolbar.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Button(folder_toolbar, text="Add Folder", command=self.add_search_folder).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(folder_toolbar, text="Remove Selected", command=self.remove_search_folder).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(folder_toolbar, text="Index All Folders", command=self.index_all_folders).pack(side=tk.LEFT, padx=(0, 5))
        
        # Folder listbox
        self.folder_listbox = tk.Listbox(folder_frame, selectmode=tk.SINGLE)
        folder_scrollbar_y = ttk.Scrollbar(folder_frame, orient="vertical", command=self.folder_listbox.yview)
        self.folder_listbox.configure(yscrollcommand=folder_scrollbar_y.set)
        
        self.folder_listbox.pack(side="left", fill="both", expand=True)
        folder_scrollbar_y.pack(side="right", fill="y")
        
        # Progress frame
        progress_frame = ttk.LabelFrame(manage_frame, text="Indexing Progress", padding=10)
        progress_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        self.progress_var = tk.StringVar(value="Ready")
        self.progress_label = ttk.Label(progress_frame, textvariable=self.progress_var)
        self.progress_label.pack()
        
        self.progress_bar = ttk.Progressbar(progress_frame, mode='determinate')
        self.progress_bar.pack(fill=tk.X, pady=5)
        
    def setup_settings_tab(self):
        """
        Setup the settings and statistics tab.
        """
        settings_frame = ttk.Frame(self.notebook)
        self.notebook.add(settings_frame, text="Settings & Stats")
        
        # Statistics frame
        stats_frame = ttk.LabelFrame(settings_frame, text="Database Statistics", padding=10)
        stats_frame.pack(fill=tk.X, padx=10, pady=10)
        
        self.stats_text = scrolledtext.ScrolledText(stats_frame, height=10, state=tk.DISABLED)
        self.stats_text.pack(fill=tk.BOTH, expand=True)
        
        ttk.Button(stats_frame, text="Refresh Stats", command=self.refresh_stats).pack(pady=5)
        
        # Settings frame
        settings_config_frame = ttk.LabelFrame(settings_frame, text="Search Settings", padding=10)
        settings_config_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        # Face similarity tolerance
        ttk.Label(settings_config_frame, text="Face Similarity Tolerance:").pack(anchor=tk.W)
        self.tolerance_var = tk.DoubleVar(value=0.6)
        tolerance_scale = ttk.Scale(settings_config_frame, from_=0.3, to=0.9, 
                                   variable=self.tolerance_var, orient=tk.HORIZONTAL)
        tolerance_scale.pack(fill=tk.X, pady=5)
        
        # Maintenance
        maintenance_frame = ttk.LabelFrame(settings_frame, text="Maintenance", padding=10)
        maintenance_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        ttk.Button(maintenance_frame, text="Cleanup Database", command=self.cleanup_database).pack(pady=2)
        ttk.Button(maintenance_frame, text="Clear All Data", command=self.clear_all_data).pack(pady=2)
        
    def select_reference_image(self):
        """
        Select a reference image for face detection.
        """
        file_path = filedialog.askopenfilename(
            title="Select Reference Image",
            filetypes=[
                ("Image files", "*.jpg *.jpeg *.png *.bmp *.tiff *.tif"),
                ("All files", "*.*")
            ]
        )
        
        if file_path:
            self.selected_image_path = file_path
            self.display_selected_image()
            self.detect_faces_in_image()
    
    def display_selected_image(self):
        """
        Display the selected image in the GUI.
        """
        try:
            # Load and resize image for display
            image = Image.open(self.selected_image_path)
            image.thumbnail((300, 300), Image.Resampling.LANCZOS)
            
            # Convert to PhotoImage
            photo = ImageTk.PhotoImage(image)
            
            # Update label
            self.image_label.configure(image=photo, text="")
            self.image_label.image = photo  # Keep a reference
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load image: {str(e)}")
    
    def detect_faces_in_image(self):
        """
        Detect faces in the selected image and display them.
        """
        if not self.selected_image_path:
            return
        
        try:
            # Clear previous faces
            for widget in self.face_scrollable_frame.winfo_children():
                widget.destroy()
            
            # Get face locations and encodings
            face_locations, face_encodings = self.face_engine.get_face_locations_and_encodings(self.selected_image_path)
            
            if not face_locations:
                ttk.Label(self.face_scrollable_frame, text="No faces detected").pack(pady=10)
                self.search_button.configure(state=tk.DISABLED)
                return
            
            self.detected_faces = list(zip(face_locations, face_encodings))
            
            # Display each detected face
            for i, (location, encoding) in enumerate(self.detected_faces):
                self.create_face_selection_widget(i, location, encoding)
            
            self.search_button.configure(state=tk.NORMAL)
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to detect faces: {str(e)}")
    
    def create_face_selection_widget(self, index: int, location: Tuple, encoding):
        """
        Create a widget for face selection.
        """
        face_frame = ttk.Frame(self.face_scrollable_frame)
        face_frame.pack(fill=tk.X, pady=5)
        
        # Extract face image
        face_image = self.face_engine.extract_face_from_image(self.selected_image_path, location)
        
        if face_image is not None:
            # Convert to PIL Image and resize
            pil_image = Image.fromarray(face_image)
            pil_image.thumbnail((80, 80), Image.Resampling.LANCZOS)
            
            # Convert to PhotoImage
            photo = ImageTk.PhotoImage(pil_image)
            
            # Create button for face selection
            face_button = ttk.Button(
                face_frame, 
                text=f"Face {index + 1}",
                command=lambda idx=index: self.select_face_for_search(idx)
            )
            face_button.pack(side=tk.LEFT, padx=5)
            
            # Display face thumbnail
            face_label = ttk.Label(face_frame, image=photo)
            face_label.image = photo  # Keep reference
            face_label.pack(side=tk.LEFT, padx=5)
    
    def select_face_for_search(self, face_index: int):
        """
        Select a specific face for searching.
        """
        if 0 <= face_index < len(self.detected_faces):
            _, encoding = self.detected_faces[face_index]
            self.selected_face_encoding = encoding
            messagebox.showinfo("Face Selected", f"Face {face_index + 1} selected for search")
    
    def search_similar_faces(self):
        """
        Search for similar faces in the database.
        """
        if self.selected_face_encoding is None:
            messagebox.showwarning("No Face Selected", "Please select a face first")
            return
        
        # Show progress
        self.progress_var.set("Searching for similar faces...")
        self.root.update()
        
        try:
            # Perform search
            tolerance = self.tolerance_var.get()
            results = self.photo_manager.search_similar_faces(self.selected_face_encoding, tolerance)
            
            self.search_results = results
            self.display_search_results()
            
            self.progress_var.set(f"Found {len(results)} similar faces")
            
        except Exception as e:
            messagebox.showerror("Search Error", f"Failed to search: {str(e)}")
            self.progress_var.set("Search failed")
    
    def display_search_results(self):
        """
        Display search results in the results panel.
        """
        # Clear previous results
        for widget in self.results_scrollable_frame.winfo_children():
            widget.destroy()
        
        if not self.search_results:
            ttk.Label(self.results_scrollable_frame, text="No similar faces found").pack(pady=20)
            return
        
        # Display results
        for i, result in enumerate(self.search_results):
            self.create_result_widget(i, result)
    
    def create_result_widget(self, index: int, result: Dict):
        """
        Create a widget for displaying a search result.
        """
        result_frame = ttk.Frame(self.results_scrollable_frame, relief=tk.RIDGE, borderwidth=1)
        result_frame.pack(fill=tk.X, pady=2, padx=5)
        
        # Checkbox for selection
        var = tk.BooleanVar()
        checkbox = ttk.Checkbutton(result_frame, variable=var)
        checkbox.pack(side=tk.LEFT, padx=5)
        
        # Store the variable for later access
        result['selected_var'] = var
        
        # Thumbnail
        try:
            thumbnail_path = self.photo_manager.get_image_thumbnail(result['file_path'])
            if thumbnail_path and os.path.exists(thumbnail_path):
                image = Image.open(thumbnail_path)
                photo = ImageTk.PhotoImage(image)
                
                img_label = ttk.Label(result_frame, image=photo)
                img_label.image = photo
                img_label.pack(side=tk.LEFT, padx=5)
        except:
            pass
        
        # File info
        info_frame = ttk.Frame(result_frame)
        info_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        
        ttk.Label(info_frame, text=result['file_name'], font=('TkDefaultFont', 9, 'bold')).pack(anchor=tk.W)
        ttk.Label(info_frame, text=f"Similarity: {result['similarity']:.2%}", font=('TkDefaultFont', 8)).pack(anchor=tk.W)
        ttk.Label(info_frame, text=result['file_path'], font=('TkDefaultFont', 8)).pack(anchor=tk.W)
    
    def select_all_results(self):
        """
        Select all search results.
        """
        for result in self.search_results:
            if 'selected_var' in result:
                result['selected_var'].set(True)
    
    def clear_selection(self):
        """
        Clear all selections.
        """
        for result in self.search_results:
            if 'selected_var' in result:
                result['selected_var'].set(False)
    
    def get_selected_files(self) -> List[str]:
        """
        Get list of selected file paths.
        """
        selected = []
        for result in self.search_results:
            if 'selected_var' in result and result['selected_var'].get():
                selected.append(result['file_path'])
        return selected
    
    def copy_selected_files(self):
        """
        Copy selected files to a destination folder.
        """
        selected_files = self.get_selected_files()
        if not selected_files:
            messagebox.showwarning("No Selection", "Please select files to copy")
            return
        
        dest_folder = filedialog.askdirectory(title="Select Destination Folder")
        if dest_folder:
            try:
                result = self.photo_manager.copy_files(selected_files, dest_folder)
                messagebox.showinfo("Copy Complete", 
                                  f"Copied {result['successful']} files successfully\n"
                                  f"Failed: {result['failed']}")
            except Exception as e:
                messagebox.showerror("Copy Error", f"Failed to copy files: {str(e)}")
    
    def move_selected_files(self):
        """
        Move selected files to a destination folder.
        """
        selected_files = self.get_selected_files()
        if not selected_files:
            messagebox.showwarning("No Selection", "Please select files to move")
            return
        
        dest_folder = filedialog.askdirectory(title="Select Destination Folder")
        if dest_folder:
            if messagebox.askyesno("Confirm Move", f"Move {len(selected_files)} files?"):
                try:
                    result = self.photo_manager.move_files(selected_files, dest_folder)
                    messagebox.showinfo("Move Complete", 
                                      f"Moved {result['successful']} files successfully\n"
                                      f"Failed: {result['failed']}")
                    # Refresh results
                    self.search_similar_faces()
                except Exception as e:
                    messagebox.showerror("Move Error", f"Failed to move files: {str(e)}")
    
    def delete_selected_files(self):
        """
        Delete selected files.
        """
        selected_files = self.get_selected_files()
        if not selected_files:
            messagebox.showwarning("No Selection", "Please select files to delete")
            return
        
        if messagebox.askyesno("Confirm Delete", 
                              f"Permanently delete {len(selected_files)} files?\n"
                              "This action cannot be undone!"):
            try:
                result = self.photo_manager.delete_files(selected_files)
                messagebox.showinfo("Delete Complete", 
                                  f"Deleted {result['successful']} files successfully\n"
                                  f"Failed: {result['failed']}")
                # Refresh results
                self.search_similar_faces()
            except Exception as e:
                messagebox.showerror("Delete Error", f"Failed to delete files: {str(e)}")
    
    def load_search_folders(self):
        """
        Load search folders into the listbox.
        """
        self.folder_listbox.delete(0, tk.END)
        folders = self.db_manager.get_search_folders()
        for folder in folders:
            self.folder_listbox.insert(tk.END, folder)
    
    def add_search_folder(self):
        """
        Add a new search folder.
        """
        folder = filedialog.askdirectory(title="Select Folder to Add")
        if folder:
            if self.db_manager.add_search_folder(folder):
                self.load_search_folders()
                messagebox.showinfo("Success", f"Added folder: {folder}")
            else:
                messagebox.showerror("Error", "Failed to add folder")
    
    def remove_search_folder(self):
        """
        Remove selected search folder.
        """
        selection = self.folder_listbox.curselection()
        if selection:
            folder = self.folder_listbox.get(selection[0])
            if messagebox.askyesno("Confirm Remove", f"Remove folder from search scope?\n{folder}"):
                if self.db_manager.remove_search_folder(folder):
                    self.load_search_folders()
                    messagebox.showinfo("Success", "Folder removed")
                else:
                    messagebox.showerror("Error", "Failed to remove folder")
    
    def index_all_folders(self):
        """
        Index all images in search folders.
        """
        folders = self.db_manager.get_search_folders()
        if not folders:
            messagebox.showwarning("No Folders", "Please add folders to search scope first")
            return
        
        # Run indexing in background thread
        threading.Thread(target=self._index_folders_background, args=(folders,), daemon=True).start()
    
    def _index_folders_background(self, folders: List[str]):
        """
        Background thread for indexing folders.
        """
        try:
            # Scan for images
            self.progress_var.set("Scanning folders for images...")
            image_files = self.photo_manager.scan_folders_for_images(folders)
            
            if not image_files:
                self.progress_var.set("No images found")
                return
            
            # Index images
            self.progress_var.set(f"Indexing {len(image_files)} images...")
            self.progress_bar.configure(maximum=len(image_files))
            
            # Monitor progress
            def update_progress():
                current, total = self.photo_manager.get_indexing_progress()
                self.progress_bar.configure(value=current)
                self.progress_var.set(f"Indexing: {current}/{total}")
                
                if current < total:
                    self.root.after(1000, update_progress)
                else:
                    self.progress_var.set(f"Indexing complete: {current} images processed")
            
            # Start progress monitoring
            self.root.after(100, update_progress)
            
            # Start indexing
            result = self.photo_manager.index_images_batch(image_files)
            
        except Exception as e:
            self.progress_var.set(f"Indexing failed: {str(e)}")
    
    def refresh_stats(self):
        """
        Refresh database statistics.
        """
        try:
            stats = self.db_manager.get_database_stats()
            
            stats_text = f"""Database Statistics:
            
Total Images: {stats['total_images']:,}
Total Faces: {stats['total_faces']:,}
Active Folders: {stats['active_folders']}
Database Size: {stats['database_size'] / (1024*1024):.2f} MB

Face Detection Rate: {stats['total_faces'] / max(stats['total_images'], 1):.2f} faces per image
"""
            
            self.stats_text.configure(state=tk.NORMAL)
            self.stats_text.delete(1.0, tk.END)
            self.stats_text.insert(1.0, stats_text)
            self.stats_text.configure(state=tk.DISABLED)
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to refresh stats: {str(e)}")
    
    def cleanup_database(self):
        """
        Cleanup orphaned database entries.
        """
        if messagebox.askyesno("Confirm Cleanup", "Remove database entries for deleted files?"):
            try:
                removed = self.photo_manager.cleanup_database()
                messagebox.showinfo("Cleanup Complete", f"Removed {removed} orphaned entries")
                self.refresh_stats()
            except Exception as e:
                messagebox.showerror("Error", f"Cleanup failed: {str(e)}")
    
    def clear_all_data(self):
        """
        Clear all data from database.
        """
        if messagebox.askyesno("Confirm Clear", 
                              "This will delete ALL face data and search folders!\n"
                              "Are you sure you want to continue?"):
            try:
                # Remove database file
                if os.path.exists(self.db_manager.db_path):
                    os.remove(self.db_manager.db_path)
                
                # Reinitialize
                self.db_manager.init_database()
                self.load_search_folders()
                self.refresh_stats()
                
                messagebox.showinfo("Success", "All data cleared")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to clear data: {str(e)}")
    
    def run(self):
        """
        Start the GUI application.
        """
        # Initialize stats
        self.refresh_stats()
        
        # Start main loop
        self.root.mainloop()

if __name__ == "__main__":
    app = PhotoSearchGUI()
    app.run()
