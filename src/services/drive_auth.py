"""
Google Drive 인증 모듈 (OAuth 2.0)
- 로컬: config/oauth_credentials.json + config/token.json 사용
- Streamlit Cloud: st.secrets에서 인증 정보 로드
"""

import os
import json
from pathlib import Path
from dotenv import load_dotenv
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
load_dotenv()

SCOPES = ['https://www.googleapis.com/auth/drive']
PROJECT_ROOT = Path(__file__).parent.parent.parent
CONFIG_DIR = PROJECT_ROOT / 'config'
OAUTH_CREDENTIALS_PATH = CONFIG_DIR / 'oauth_credentials.json'
TOKEN_PATH = CONFIG_DIR / 'token.json'


def _is_streamlit_cloud():
    """Streamlit Cloud 환경인지 감지"""
    try:
        import streamlit as st
        return hasattr(st, 'secrets') and 'token' in st.secrets
    except Exception:
        return False


def _get_folder_id():
    """폴더 ID를 환경에 따라 가져오기"""
    # 1순위: Streamlit Cloud Secrets
    try:
        import streamlit as st
        if 'gdrive' in st.secrets and 'folder_id' in st.secrets['gdrive']:
            return st.secrets['gdrive']['folder_id']
    except Exception:
        pass
    
    # 2순위: 환경변수 (.env)
    return os.getenv('GDRIVE_FOLDER_ID')


GDRIVE_FOLDER_ID = _get_folder_id()


def _credentials_from_secrets():
    """Streamlit Cloud Secrets에서 인증정보 로드"""
    import streamlit as st
    
    token_data = {
        'token': st.secrets['token']['token'],
        'refresh_token': st.secrets['token']['refresh_token'],
        'token_uri': st.secrets['token']['token_uri'],
        'client_id': st.secrets['oauth']['client_id'],
        'client_secret': st.secrets['oauth']['client_secret'],
        'scopes': SCOPES,
    }
    
    return Credentials.from_authorized_user_info(token_data, SCOPES)


def get_credentials():
    """OAuth 자격증명 로드"""
    creds = None
    
    # Streamlit Cloud 환경
    if _is_streamlit_cloud():
        creds = _credentials_from_secrets()
        # 토큰 만료시 자동 갱신
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
        return creds
    
    # 로컬 환경 (Codespace 포함)
    if TOKEN_PATH.exists():
        try:
            creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)
        except Exception:
            creds = None
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("🔄 토큰 자동 갱신 중...")
            try:
                creds.refresh(Request())
                _save_token(creds)
                print("✅ 토큰 갱신 완료")
                return creds
            except Exception:
                creds = None
        
        if not OAUTH_CREDENTIALS_PATH.exists():
            raise FileNotFoundError(
                f"❌ oauth_credentials.json 파일을 찾을 수 없습니다: {OAUTH_CREDENTIALS_PATH}"
            )
        
        print("\n" + "=" * 60)
        print("🔐 최초 OAuth 인증을 시작합니다.")
        print("=" * 60)
        
        flow = InstalledAppFlow.from_client_secrets_file(
            str(OAUTH_CREDENTIALS_PATH),
            SCOPES,
            redirect_uri='http://localhost:8501/'
        )
        
        auth_url, _ = flow.authorization_url(
            access_type='offline',
            prompt='consent',
            include_granted_scopes='true'
        )
        
        print("\n" + "=" * 60)
        print("🌐 아래 URL을 브라우저에 복사 붙여넣기:")
        print("=" * 60)
        print(auth_url)
        print("=" * 60)
        print("\n📋 진행 방법:")
        print("1. 위 URL을 새 브라우저 탭에 붙여넣고 이동")
        print("2. Google 계정 로그인 + 권한 허용")
        print("3. localhost:8501로 리디렉션 (연결 에러 정상!)")
        print("4. 주소창의 URL 전체를 복사해서 아래에 붙여넣기\n")
        
        redirect_url = input("📋 리디렉션된 URL 전체를 붙여넣고 엔터: ").strip()
        flow.fetch_token(authorization_response=redirect_url)
        creds = flow.credentials
        
        _save_token(creds)
        print(f"\n✅ 인증 완료! 토큰 저장됨: {TOKEN_PATH}")
    
    return creds


def _save_token(creds):
    CONFIG_DIR.mkdir(exist_ok=True)
    with open(TOKEN_PATH, 'w') as f:
        f.write(creds.to_json())


def get_drive_service():
    creds = get_credentials()
    return build('drive', 'v3', credentials=creds)


def test_connection():
    print("=" * 60)
    print("🔐 Google Drive 연결 테스트 (OAuth)")
    print("=" * 60)
    
    try:
        service = get_drive_service()
        about = service.about().get(fields="user, storageQuota").execute()
        user = about.get('user', {})
        quota = about.get('storageQuota', {})
        
        print(f"\n✅ Google Drive 연결 성공!")
        print(f"   사용자: {user.get('displayName', 'Unknown')}")
        print(f"   이메일: {user.get('emailAddress', 'Unknown')}")
        
        if quota:
            limit = int(quota.get('limit', 0))
            usage = int(quota.get('usage', 0))
            if limit > 0:
                print(f"   저장공간: {usage / 1024**3:.2f}GB / {limit / 1024**3:.2f}GB")
        
        if GDRIVE_FOLDER_ID:
            print(f"\n📁 폴더 접근 테스트...")
            folder = service.files().get(fileId=GDRIVE_FOLDER_ID, fields='id, name').execute()
            print(f"✅ 폴더 접근 성공: {folder.get('name')}")
        
        print("\n" + "=" * 60)
        print("🎉 모든 테스트 통과!")
        print("=" * 60)
        return True
    except Exception as e:
        print(f"\n❌ 에러: {e}")
        return False


if __name__ == '__main__':
    test_connection()
