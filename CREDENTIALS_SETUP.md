# Google Drive API Credentials Setup

This file explains how to set up the required credential files for Google Drive integration.

## Required Files (NOT included in repository for security)

1. **credentials.json** - Google Drive API credentials
2. **client_secret_*.json** - OAuth 2.0 client secret file
3. **token.json** - Generated automatically after first authentication

## Setup Instructions

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the Google Drive API
4. Create credentials (OAuth 2.0 Client ID)
5. Download the client secret JSON file
6. Rename it to match the expected filename in config.py
7. Place both credential files in the project root directory

## File Templates

### credentials.json template:
```json
{
  "type": "service_account",
  "project_id": "your-project-id",
  "private_key_id": "your-private-key-id",
  "private_key": "your-private-key",
  "client_email": "your-service-account@your-project.iam.gserviceaccount.com",
  "client_id": "your-client-id",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token"
}
```

### client_secret_*.json template:
```json
{
  "installed": {
    "client_id": "your-client-id.apps.googleusercontent.com",
    "project_id": "your-project-id",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "client_secret": "your-client-secret",
    "redirect_uris": ["urn:ietf:wg:oauth:2.0:oob", "http://localhost"]
  }
}
```

**Note**: Replace all placeholder values with your actual Google Cloud project credentials.