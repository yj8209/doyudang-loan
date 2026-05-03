"""
Google Drive 인증 모듈 (Service Account 방식)
- 5년간 자동 인증, 만료 없음
- Codespace, Streamlit Cloud 어디서든 동일하게 작동
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# .env 파일 로드
load_dotenv()

# 권한 범위 (Drive 파일 읽기/쓰기)
SCOPES = ['https://www.googleapis.com/auth/drive']

# 프로젝트 루트 경로
PROJECT_ROOT = Path(__file__).parent.parent.parent

# 환경변수에서 설정 읽기
SERVICE_ACCOUNT_PATH = PROJECT_ROOT / os.getenv(
    'SERVICE_ACCOUNT_PATH', 
    'config/service_account.json'
)
GDRIVE_FOLDER_ID = os.getenv('GDRIVE_FOLDER_ID')


def get_drive_service():
    """
    Service Account로 인증된 Google Drive API 서비스 객체 반환.
    """
    if not SERVICE_ACCOUNT_PATH.exists():
        raise FileNotFoundError(
            f"❌ service_account.json 파일을 찾을 수 없습니다:\n"
            f"   경로: {SERVICE_ACCOUNT_PATH}\n"
            f"   해결: config/ 폴더에 service_account.json 파일을 업로드하세요."
        )
    
    if not GDRIVE_FOLDER_ID:
        raise ValueError(
            "❌ GDRIVE_FOLDER_ID 환경변수가 설정되지 않았습니다.\n"
            "   해결: .env 파일에 GDRIVE_FOLDER_ID=폴더ID 추가하세요."
        )
    
    # Service Account 인증
    credentials = service_account.Credentials.from_service_account_file(
        str(SERVICE_ACCOUNT_PATH),
        scopes=SCOPES
    )
    
    # Drive 서비스 객체 생성
    service = build('drive', 'v3', credentials=credentials)
    return service


def test_connection():
    """연결 테스트: 공유받은 폴더 접근 가능 여부 확인"""
    print("=" * 60)
    print("🔐 Google Drive 연결 테스트")
    print("=" * 60)
    
    try:
        service = get_drive_service()
        print("\n✅ Service Account 인증 성공!")
        
        # 공유받은 폴더에 접근 시도
        print(f"\n📁 폴더 접근 테스트 중... (ID: {GDRIVE_FOLDER_ID[:10]}...)")
        
        folder = service.files().get(
            fileId=GDRIVE_FOLDER_ID,
            fields='id, name, owners'
        ).execute()
        
        print(f"✅ 폴더 접근 성공!")
        print(f"   폴더 이름: {folder.get('name')}")
        
        # 폴더 내 파일 목록 (있다면)
        results = service.files().list(
            q=f"'{GDRIVE_FOLDER_ID}' in parents and trashed=false",
            fields='files(id, name, mimeType)',
            pageSize=10
        ).execute()
        
        files = results.get('files', [])
        if files:
            print(f"\n📋 폴더 내 항목 ({len(files)}개):")
            for f in files:
                icon = "📁" if f['mimeType'] == 'application/vnd.google-apps.folder' else "📄"
                print(f"   {icon} {f['name']}")
        else:
            print(f"\n📋 폴더가 비어있습니다 (정상 - 곧 자동으로 채워집니다)")
        
        print("\n" + "=" * 60)
        print("🎉 모든 테스트 통과! 다음 단계로 진행 가능합니다.")
        print("=" * 60)
        return True
        
    except FileNotFoundError as e:
        print(f"\n{e}")
        return False
    except ValueError as e:
        print(f"\n{e}")
        return False
    except HttpError as e:
        if e.resp.status == 404:
            print(f"\n❌ 폴더를 찾을 수 없습니다.")
            print(f"   폴더 ID 확인 또는 서비스 계정에 폴더 공유 여부를 확인하세요.")
        elif e.resp.status == 403:
            print(f"\n❌ 폴더 접근 권한이 없습니다.")
            print(f"   해결: 남편분 Drive에서 두유당_대출관리 폴더를")
            print(f"        서비스 계정 이메일과 공유했는지 확인하세요.")
        else:
            print(f"\n❌ Google Drive API 에러: {e}")
        return False
    except Exception as e:
        print(f"\n❌ 예상치 못한 에러: {e}")
        return False


if __name__ == '__main__':
    test_connection()