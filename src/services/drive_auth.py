"""
Google Drive 인증 모듈 (OAuth 2.0 방식)
- 첫 인증: 브라우저로 Google 로그인 → token.json 저장
- 이후: token.json으로 자동 인증 (refresh token으로 영구 갱신)
- 5년 운영 안정적
"""

import os
import json
from pathlib import Path
from dotenv import load_dotenv
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
from googleapiclient.errors import HttpError

# .env 파일 로드
load_dotenv()

# Google Drive 권한 (전체 접근)
SCOPES = ['https://www.googleapis.com/auth/drive']

# 프로젝트 루트
PROJECT_ROOT = Path(__file__).parent.parent.parent

# 파일 경로
CONFIG_DIR = PROJECT_ROOT / 'config'
OAUTH_CREDENTIALS_PATH = CONFIG_DIR / 'oauth_credentials.json'
TOKEN_PATH = CONFIG_DIR / 'token.json'

# 환경변수에서 폴더 ID
GDRIVE_FOLDER_ID = os.getenv('GDRIVE_FOLDER_ID')


def get_credentials():
    """OAuth 자격증명 로드 또는 새로 발급"""
    creds = None
    
    # 1. 기존 토큰 있으면 로드
    if TOKEN_PATH.exists():
        try:
            creds = Credentials.from_authorized_user_file(
                str(TOKEN_PATH), SCOPES
            )
        except Exception as e:
            print(f"⚠️  토큰 로드 실패 (재인증 필요): {e}")
            creds = None
    
    # 2. 토큰이 없거나 만료됐으면
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("🔄 토큰 자동 갱신 중...")
            try:
                creds.refresh(Request())
                _save_token(creds)
                print("✅ 토큰 갱신 완료")
                return creds
            except Exception as e:
                print(f"⚠️  자동 갱신 실패, 재인증 필요: {e}")
                creds = None
        
        # 새 인증 필요
        if not OAUTH_CREDENTIALS_PATH.exists():
            raise FileNotFoundError(
                f"❌ oauth_credentials.json 파일을 찾을 수 없습니다:\n"
                f"   경로: {OAUTH_CREDENTIALS_PATH}"
            )
        
        print("\n" + "=" * 60)
        print("🔐 최초 OAuth 인증을 시작합니다.")
        print("=" * 60)
        
        flow = InstalledAppFlow.from_client_secrets_file(
            str(OAUTH_CREDENTIALS_PATH),
            SCOPES,
            redirect_uri='http://localhost:8501/'
        )
        
        # 인증 URL 생성
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
        print("2. 남편분 Google 계정 로그인")
        print("3. '확인되지 않은 앱' 화면 → '계속' 클릭")
        print("4. 권한 요청 → '계속' 클릭")
        print("5. localhost:8501로 리디렉션 (연결 에러 정상!)")
        print("6. 주소창의 URL 전체를 복사해서 아래에 붙여넣기\n")
        
        # 사용자가 리디렉션 URL을 입력
        redirect_url = input("📋 리디렉션된 URL 전체를 붙여넣고 엔터: ").strip()
        
        # URL에서 인증 코드 추출하여 토큰 교환
        flow.fetch_token(authorization_response=redirect_url)
        creds = flow.credentials
        
        # 토큰 저장
        _save_token(creds)
        print(f"\n✅ 인증 완료! 토큰 저장됨: {TOKEN_PATH}")
        print("   다음부터는 자동으로 인증됩니다.\n")
    
    return creds


def _save_token(creds):
    """토큰을 안전하게 저장"""
    CONFIG_DIR.mkdir(exist_ok=True)
    with open(TOKEN_PATH, 'w') as f:
        f.write(creds.to_json())


def get_drive_service():
    """Google Drive API 서비스 객체 반환"""
    creds = get_credentials()
    service = build('drive', 'v3', credentials=creds)
    return service


def test_connection():
    """연결 테스트"""
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
                used_pct = (usage / limit) * 100
                print(f"   저장공간: {usage / 1024**3:.2f}GB / {limit / 1024**3:.2f}GB ({used_pct:.1f}%)")
        
        if GDRIVE_FOLDER_ID:
            print(f"\n📁 폴더 접근 테스트...")
            folder = service.files().get(
                fileId=GDRIVE_FOLDER_ID,
                fields='id, name'
            ).execute()
            print(f"✅ 폴더 접근 성공: {folder.get('name')}")
        
        print("\n" + "=" * 60)
        print("🎉 모든 테스트 통과!")
        print("=" * 60)
        return True
        
    except FileNotFoundError as e:
        print(f"\n{e}")
        return False
    except HttpError as e:
        print(f"\n❌ Google Drive API 에러: {e}")
        return False
    except Exception as e:
        print(f"\n❌ 에러: {e}")
        return False


if __name__ == '__main__':
    test_connection()
