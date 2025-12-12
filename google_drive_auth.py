#!/usr/bin/env python3
"""
Google Drive API Authentication Module
Implements OAuth 2.0 flow with automatic token refresh and secure credential management

Features:
- OAuth 2.0 authentication flow
- Automatic token refresh
- Secure credential storage
- Error handling and recovery
- Development vs production modes

Setup Instructions:
1. Go to Google Cloud Console (https://console.cloud.google.com/)
2. Create a new project or select existing
3. Enable Google Drive API
4. Create OAuth 2.0 credentials (Desktop application)
5. Download credentials.json and place in project root

Usage:
    auth = GoogleDriveAuth()
    service = auth.get_authenticated_service()
    
Created by: RT Max
"""

import os
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

# Google API imports
try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
except ImportError as e:
    print("❌ Google API libraries not installed.")
    print("Run: pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib")
    raise e

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GoogleDriveAuthError(Exception):
    """Custom exception for Google Drive authentication errors"""
    pass

class GoogleDriveAuth:
    """
    Google Drive API Authentication Manager
    
    Handles OAuth 2.0 flow, token management, and service creation
    with automatic refresh and error recovery.
    """
    
    # OAuth 2.0 scopes
    SCOPES = [
        'https://www.googleapis.com/auth/drive.file',     # Access files created by the app
        'https://www.googleapis.com/auth/drive',          # Full access to Drive
        'https://www.googleapis.com/auth/drive.metadata.readonly'  # Read metadata
    ]
    
    # API configuration
    API_SERVICE_NAME = 'drive'
    API_VERSION = 'v3'
    
    def __init__(self, 
                 credentials_file: str = 'gdrive_credentials.json',
                 token_file: str = None,
                 config_dir: Path = None):
        """
        Initialize Google Drive authentication
        
        Args:
            credentials_file: Path to OAuth 2.0 credentials JSON file
            token_file: Path to store access tokens (optional)
            config_dir: Directory for storing auth data (optional)
        """
        
        # Set up paths
        self.project_root = Path(__file__).parent
        self.config_dir = config_dir or (self.project_root / '.ai_organizer_config')
        self.config_dir.mkdir(exist_ok=True)
        
        # Credential files
        self.credentials_file = self.project_root / credentials_file
        self.token_file = token_file or (self.config_dir / 'google_drive_token.json')
        
        # Authentication state
        self._credentials: Optional[Credentials] = None
        self._service = None
        self._last_auth_time: Optional[datetime] = None
        
        logger.info(f"🔧 GoogleDriveAuth initialized")
        logger.info(f"   📁 Config dir: {self.config_dir}")
        logger.info(f"   🔑 Token file: {self.token_file}")
        
    def authenticate(self) -> bool:
        """
        Perform Google Drive authentication
        
        Returns:
            bool: True if authentication successful, False otherwise
        """
        try:
            logger.info("🔐 Starting Google Drive authentication...")
            
            # Step 1: Load existing credentials
            self._credentials = self._load_existing_credentials()
            
            # Step 2: Refresh if needed
            if self._credentials and self._credentials.expired:
                logger.info("🔄 Refreshing expired credentials...")
                if self._credentials.refresh_token:
                    self._credentials.refresh(Request())
                    logger.info("✅ Credentials refreshed successfully")
                else:
                    logger.warning("⚠️  No refresh token available, need re-authentication")
                    self._credentials = None
            
            # Step 3: Get new credentials if needed
            if not self._credentials or not self._credentials.valid:
                logger.info("🆕 Getting new credentials...")
                self._credentials = self._get_new_credentials()
            
            # Step 4: Save credentials for future use
            if self._credentials:
                self._save_credentials()
                self._last_auth_time = datetime.now()
                logger.info("✅ Google Drive authentication successful")
                return True
            else:
                logger.error("❌ Failed to obtain valid credentials")
                return False
                
        except Exception as e:
            logger.error(f"❌ Authentication error: {e}")
            raise GoogleDriveAuthError(f"Authentication failed: {e}")
    
    def _load_existing_credentials(self) -> Optional[Credentials]:
        """Load existing credentials from token file"""
        
        if not self.token_file.exists():
            logger.info("📄 No existing token file found")
            return None
        
        try:
            logger.info("📖 Loading existing credentials...")
            credentials = Credentials.from_authorized_user_file(
                str(self.token_file), 
                self.SCOPES
            )
            
            if credentials.valid:
                logger.info("✅ Existing credentials are valid")
            elif credentials.expired:
                logger.info("⏰ Existing credentials are expired")
            else:
                logger.info("⚠️  Existing credentials are invalid")
            
            return credentials
            
        except Exception as e:
            logger.warning(f"⚠️  Could not load existing credentials: {e}")
            return None
    
    def _get_new_credentials(self) -> Optional[Credentials]:
        """Get new credentials via OAuth 2.0 flow"""
        
        # Check if credentials file exists
        if not self.credentials_file.exists():
            logger.error(f"❌ Credentials file not found: {self.credentials_file}")
            logger.error("💡 Please download credentials.json from Google Cloud Console")
            logger.error("   1. Go to https://console.cloud.google.com/")
            logger.error("   2. Select your project")
            logger.error("   3. Go to APIs & Services > Credentials")
            logger.error("   4. Create OAuth 2.0 Client ID (Desktop application)")
            logger.error("   5. Download and save as gdrive_credentials.json")
            raise GoogleDriveAuthError(f"Credentials file not found: {self.credentials_file}")
        
        try:
            logger.info("🌐 Starting OAuth 2.0 flow...")
            
            # Create OAuth flow
            flow = InstalledAppFlow.from_client_secrets_file(
                str(self.credentials_file), 
                self.SCOPES
            )
            
            # Run OAuth flow
            # This will open a browser window for user consent
            # Use port=0 to let the system choose an available port
            print("\n" + "="*50)
            print("🔐 OPENING BROWSER FOR GOOGLE LOGIN...")
            print("If browser doesn't open, check these logs for a URL.")
            print("="*50 + "\n")
            
            credentials = flow.run_local_server(
                port=0,
                access_type='offline',
                prompt='consent'
            )
            
            logger.info("✅ OAuth 2.0 flow completed successfully")
            return credentials
            
        except Exception as e:
            logger.error(f"❌ OAuth 2.0 flow failed: {e}")
            raise GoogleDriveAuthError(f"OAuth flow failed: {e}")
    
    def _save_credentials(self):
        """Save credentials to token file for future use"""
        
        if not self._credentials:
            logger.warning("⚠️  No credentials to save")
            return
        
        try:
            # Ensure config directory exists
            self.config_dir.mkdir(exist_ok=True)
            
            # Save credentials
            with open(self.token_file, 'w') as token:
                token.write(self._credentials.to_json())
            
            # Secure the token file (Unix-like systems)
            if hasattr(os, 'chmod'):
                os.chmod(self.token_file, 0o600)
            
            logger.info(f"💾 Credentials saved to: {self.token_file}")
            
        except Exception as e:
            logger.error(f"❌ Failed to save credentials: {e}")
    
    def get_authenticated_service(self):
        """
        Get authenticated Google Drive service
        
        Returns:
            googleapiclient.discovery.Resource: Authenticated Drive service
        """
        
        # Authenticate if not already done
        if not self._credentials or not self._credentials.valid:
            if not self.authenticate():
                raise GoogleDriveAuthError("Could not authenticate with Google Drive")
        
        # Create service if not exists or credentials changed
        if not self._service or self._credentials_changed():
            try:
                logger.info("🔧 Building Google Drive service...")
                self._service = build(
                    self.API_SERVICE_NAME,
                    self.API_VERSION,
                    credentials=self._credentials,
                    cache_discovery=False  # Avoid warnings
                )
                logger.info("✅ Google Drive service created")
                
            except Exception as e:
                logger.error(f"❌ Failed to build service: {e}")
                raise GoogleDriveAuthError(f"Service creation failed: {e}")
        
        return self._service
    
    def _credentials_changed(self) -> bool:
        """Check if credentials have changed since service creation"""
        
        if not self._last_auth_time:
            return True
        
        # Check if token file is newer than last auth
        if self.token_file.exists():
            token_mtime = datetime.fromtimestamp(self.token_file.stat().st_mtime)
            return token_mtime > self._last_auth_time
        
        return False
    
    def test_authentication(self) -> Dict[str, Any]:
        """
        Test Google Drive authentication and return basic info
        
        Returns:
            dict: Test results including user info and quotas
        """
        
        try:
            service = self.get_authenticated_service()
            
            # Test 1: Get user info
            about = service.about().get(fields='user,storageQuota').execute()
            user_info = about.get('user', {})
            quota_info = about.get('storageQuota', {})
            
            # Test 2: List a few files to test API access
            results = service.files().list(
                pageSize=5,
                fields='files(id,name,size,modifiedTime)'
            ).execute()
            files = results.get('files', [])
            
            # Calculate storage usage
            total_bytes = int(quota_info.get('limit', 0))
            used_bytes = int(quota_info.get('usage', 0))
            
            test_results = {
                'success': True,
                'user_email': user_info.get('emailAddress', 'Unknown'),
                'user_name': user_info.get('displayName', 'Unknown'),
                'total_storage_gb': total_bytes / (1024**3) if total_bytes else 0,
                'used_storage_gb': used_bytes / (1024**3) if used_bytes else 0,
                'free_storage_gb': (total_bytes - used_bytes) / (1024**3) if total_bytes else 0,
                'files_accessible': len(files),
                'test_timestamp': datetime.now().isoformat()
            }
            
            logger.info("✅ Google Drive authentication test successful")
            return test_results
            
        except HttpError as e:
            error_details = {
                'success': False,
                'error': 'HTTP Error',
                'status_code': e.resp.status,
                'reason': e.resp.reason,
                'details': str(e)
            }
            logger.error(f"❌ Google Drive API test failed: {error_details}")
            return error_details
            
        except Exception as e:
            error_details = {
                'success': False,
                'error': 'General Error',
                'details': str(e)
            }
            logger.error(f"❌ Authentication test failed: {error_details}")
            return error_details
    
    def revoke_credentials(self):
        """Revoke and remove stored credentials"""
        
        try:
            # Revoke credentials if they exist
            if self._credentials and self._credentials.token:
                logger.info("🔓 Revoking Google Drive credentials...")
                
                # Revoke the token
                revoke_url = 'https://oauth2.googleapis.com/revoke'
                response = Request().post(revoke_url, data={'token': self._credentials.token})
                
                if response.status_code == 200:
                    logger.info("✅ Credentials revoked successfully")
                else:
                    logger.warning(f"⚠️  Credential revocation returned status: {response.status_code}")
            
            # Remove token file
            if self.token_file.exists():
                self.token_file.unlink()
                logger.info("🗑️  Token file removed")
            
            # Reset internal state
            self._credentials = None
            self._service = None
            self._last_auth_time = None
            
        except Exception as e:
            logger.error(f"❌ Error revoking credentials: {e}")
    
    @property
    def is_authenticated(self) -> bool:
        """Check if currently authenticated"""
        return (self._credentials is not None and 
                self._credentials.valid and 
                not self._credentials.expired)
    
    @property
    def user_info(self) -> Dict[str, str]:
        """Get basic user information"""
        if not self.is_authenticated:
            return {}
        
        try:
            service = self.get_authenticated_service()
            about = service.about().get(fields='user').execute()
            user = about.get('user', {})
            
            return {
                'email': user.get('emailAddress', ''),
                'name': user.get('displayName', ''),
                'photo_url': user.get('photoLink', '')
            }
        except:
            return {}

def main():
    """Test the Google Drive authentication"""
    
    print("🔐 Google Drive Authentication Test")
    print("=" * 50)
    
    try:
        # Initialize authenticator
        auth = GoogleDriveAuth()
        
        # Test authentication
        results = auth.test_authentication()
        
        if results['success']:
            print("✅ Authentication successful!")
            print(f"   👤 User: {results['user_name']} ({results['user_email']})")
            print(f"   💾 Total storage: {results['total_storage_gb']:.1f} GB")
            print(f"   📊 Used storage: {results['used_storage_gb']:.1f} GB")
            print(f"   💿 Free storage: {results['free_storage_gb']:.1f} GB")
            print(f"   📁 Files accessible: {results['files_accessible']}")
        else:
            print("❌ Authentication failed!")
            print(f"   Error: {results.get('error', 'Unknown')}")
            print(f"   Details: {results.get('details', 'No details')}")
            
    except Exception as e:
        print(f"❌ Test failed: {e}")

if __name__ == "__main__":
    main()