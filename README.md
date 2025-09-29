# Face-Based Photo Search & Management System

A professional photo organization system using advanced face recognition technology with support for both local storage and Google Drive integration.

## 🌟 Features

### Current (Local Version)
- **Face Detection & Recognition**: Automatically detect and recognize faces in photos
- **Smart Search**: Find similar faces across your photo collection with 55%+ similarity threshold
- **Folder Management**: Visual folder browser with single-directory selection
- **Web Interface**: Modern, responsive web-based interface
- **Batch Operations**: Copy, move, or delete multiple photos at once
- **Statistics Dashboard**: View database statistics and performance metrics
- **Real-time Progress**: Live indexing progress tracking

### 🚀 Google Drive Integration (Roadmap)
- **Cloud Storage Access**: Browse and search photos stored in Google Drive
- **Automatic Sync**: Keep local database in sync with Google Drive changes
- **Hybrid Search**: Search across both local and cloud storage
- **Batch Cloud Operations**: Manage Google Drive photos directly from the interface

## 📋 Requirements

### Local Version
- Python 3.8+
- SQLite3
- Face Recognition Library
- Flask (for web interface)
- PIL/Pillow for image processing

### Google Drive Integration
- Google Drive API v3
- Google Photos API (optional)
- OAuth 2.0 credentials
- Additional Python packages (see Google Drive Setup)

## 🛠️ Installation

### Local Setup
```bash
# Clone the repository
git clone https://github.com/MohanRaja-tech/VanithaPhotoGraph-Management.git
cd VanithaPhotoGraph-Management

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the web application
python web_app.py
```

### Google Drive Setup

#### 1. Google Cloud Console Setup
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable the following APIs:
   - **Google Drive API v3**
   - **Google Photos Library API** (optional)

#### 2. Create OAuth 2.0 Credentials
1. Go to **APIs & Services > Credentials**
2. Click **Create Credentials > OAuth 2.0 Client IDs**
3. Configure OAuth consent screen:
   - Application type: Web application
   - Authorized redirect URIs: `http://localhost:5000/oauth/callback`
4. Download the credentials JSON file as `credentials.json`

#### 3. Required Google APIs

##### Google Drive API v3
```python
# Scopes needed:
SCOPES = [
    'https://www.googleapis.com/auth/drive.readonly',  # Read files
    'https://www.googleapis.com/auth/drive.file',     # Manage files
    'https://www.googleapis.com/auth/drive.metadata.readonly'  # Read metadata
]
```

##### Google Photos API (Optional)
```python
# Additional scope for Google Photos:
PHOTOS_SCOPE = 'https://www.googleapis.com/auth/photoslibrary.readonly'
```

#### 4. Install Additional Dependencies
```bash
pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client
```

#### 5. Environment Configuration
Create a `.env` file:
```env
# Google Drive Configuration
GOOGLE_CLIENT_ID=your_client_id_here
GOOGLE_CLIENT_SECRET=your_client_secret_here
GOOGLE_REDIRECT_URI=http://localhost:5000/oauth/callback

# Application Configuration
FLASK_SECRET_KEY=your_secret_key_here
DATABASE_PATH=face_database.db
UPLOAD_FOLDER=uploads
```

## 🔧 Google Drive Integration Implementation

### Required API Endpoints

#### 1. Authentication
- **GET** `/auth/google` - Initiate Google OAuth flow
- **GET** `/oauth/callback` - Handle OAuth callback
- **POST** `/auth/logout` - Logout and revoke tokens

#### 2. Drive Operations
- **GET** `/api/drive/folders` - List Google Drive folders
- **GET** `/api/drive/files` - List files in a folder
- **POST** `/api/drive/download` - Download file for processing
- **GET** `/api/drive/search` - Search files by name/type

#### 3. Sync Operations
- **POST** `/api/sync/start` - Start syncing with Google Drive
- **GET** `/api/sync/status` - Get sync progress
- **POST** `/api/sync/folder` - Sync specific folder

### Implementation Steps

#### Step 1: OAuth Authentication
```python
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

def authenticate_google_drive():
    """Authenticate with Google Drive API"""
    flow = Flow.from_client_secrets_file(
        'credentials.json',
        scopes=SCOPES,
        redirect_uri='http://localhost:5000/oauth/callback'
    )
    return flow
```

#### Step 2: Drive Service Integration
```python
def get_drive_service(credentials):
    """Get authenticated Google Drive service"""
    return build('drive', 'v3', credentials=credentials)

def list_drive_folders(service):
    """List folders in Google Drive"""
    results = service.files().list(
        q="mimeType='application/vnd.google-apps.folder'",
        fields="files(id, name, parents)"
    ).execute()
    return results.get('files', [])
```

#### Step 3: File Processing
```python
def download_and_process_image(service, file_id):
    """Download image from Google Drive and process faces"""
    # Download file
    file_content = service.files().get_media(fileId=file_id).execute()
    
    # Process with face recognition
    # Save to local database with Drive metadata
```

### Database Schema Extensions

#### Additional Tables for Google Drive
```sql
-- Google Drive integration tables
CREATE TABLE drive_files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    drive_file_id TEXT UNIQUE NOT NULL,
    local_image_id INTEGER,
    file_name TEXT NOT NULL,
    mime_type TEXT,
    size INTEGER,
    modified_time TIMESTAMP,
    drive_folder_id TEXT,
    sync_status TEXT DEFAULT 'pending',
    last_synced TIMESTAMP,
    FOREIGN KEY (local_image_id) REFERENCES images (id)
);

CREATE TABLE drive_folders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    drive_folder_id TEXT UNIQUE NOT NULL,
    folder_name TEXT NOT NULL,
    parent_folder_id TEXT,
    is_synced BOOLEAN DEFAULT FALSE,
    last_synced TIMESTAMP
);

CREATE TABLE sync_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT UNIQUE NOT NULL,
    start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    end_time TIMESTAMP,
    status TEXT DEFAULT 'running',
    files_processed INTEGER DEFAULT 0,
    files_total INTEGER DEFAULT 0,
    errors_count INTEGER DEFAULT 0
);
```

## 🚀 Usage

### Local Version
1. **Launch Application**: `python web_app.py`
2. **Access Interface**: Open `http://localhost:5000`
3. **Select Folder**: Use the visual folder browser
4. **Index Photos**: Click "Index Photos" to process images
5. **Search Faces**: Upload reference image and search for similar faces
6. **Manage Results**: Use batch operations (copy, move, delete)

### Google Drive Version (Future)
1. **Authenticate**: Click "Connect Google Drive" and authorize access
2. **Browse Drive**: Navigate through your Google Drive folders
3. **Select Folders**: Choose folders to sync and index
4. **Sync & Index**: Download and process images from selected folders
5. **Hybrid Search**: Search across both local and cloud storage
6. **Cloud Operations**: Manage Google Drive files directly

## 📁 Project Structure

```
VanithaPhotoGraph-Management/
├── web_app.py              # Flask web application
├── face_recognition_engine.py  # Core face recognition logic
├── photo_manager.py        # Photo management and search
├── database_manager.py     # SQLite database operations
├── config.py              # Configuration settings
├── requirements.txt       # Python dependencies
├── .gitignore            # Git ignore rules
├── templates/            # HTML templates
│   └── index.html
├── static/              # CSS, JS, and assets
│   ├── css/style.css
│   └── js/app.js
└── google_drive/        # Google Drive integration (future)
    ├── auth.py          # OAuth authentication
    ├── drive_service.py # Drive API operations
    └── sync_manager.py  # Sync operations
```

## 🔐 Security Considerations

### Local Version
- Database files are excluded from version control
- Uploaded files are stored locally and not tracked
- No external network dependencies

### Google Drive Integration
- OAuth 2.0 for secure authentication
- Credentials stored securely (not in version control)
- Token refresh handling
- Rate limiting for API calls
- Encrypted local storage for sensitive data

## 📊 Performance Optimization

### Current Optimizations
- Thumbnail generation for faster browsing
- Batch processing for multiple images
- SQLite indexing for fast searches
- Asynchronous operations for UI responsiveness

### Google Drive Optimizations
- Incremental sync (only changed files)
- Parallel downloads with rate limiting
- Local caching of Drive metadata
- Background sync operations
- Compression for face encodings

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

MIT License - see LICENSE file for details

## 🆘 Support

For issues and questions:
1. Check the existing issues on GitHub
2. Create a new issue with detailed description
3. Include system information and error logs

## 🔄 Roadmap

- [x] Local face recognition and search
- [x] Web-based interface
- [x] Folder management with visual browser
- [x] Batch operations
- [ ] Google Drive integration
- [ ] Google Photos API support
- [ ] Advanced search filters
- [ ] Machine learning improvements
- [ ] Mobile-responsive design enhancements
- [ ] Multi-user support
- [ ] Cloud deployment options
