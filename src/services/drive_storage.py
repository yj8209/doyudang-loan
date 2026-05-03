"""
Google Drive 데이터 저장/로드 유틸리티
- JSON 파일을 Drive에 저장 (남편분 계정 폴더에)
- Drive에서 JSON 파일 로드
- Service Account 한계 해결: 폴더 소유자 위임
"""

import io
import json
from datetime import datetime
from googleapiclient.http import MediaIoBaseUpload, MediaIoBaseDownload
from googleapiclient.errors import HttpError

from src.services.drive_auth import get_drive_service, GDRIVE_FOLDER_ID


def find_file_by_name(service, file_name, parent_id=None):
    """파일 이름으로 검색. 있으면 file_id 반환, 없으면 None"""
    query = f"name='{file_name}' and trashed=false"
    if parent_id:
        query += f" and '{parent_id}' in parents"
    
    results = service.files().list(
        q=query,
        fields='files(id, name, modifiedTime)',
        supportsAllDrives=True,
        includeItemsFromAllDrives=True
    ).execute()
    
    files = results.get('files', [])
    return files[0] if files else None


def save_json(data, file_name, folder_id=None):
    """
    JSON 데이터를 Google Drive에 저장.
    같은 이름의 파일이 있으면 업데이트, 없으면 새로 생성.
    """
    if folder_id is None:
        folder_id = GDRIVE_FOLDER_ID
    
    service = get_drive_service()
    
    # JSON 문자열로 변환 (한글 그대로 저장)
    json_str = json.dumps(data, ensure_ascii=False, indent=2)
    json_bytes = json_str.encode('utf-8')
    
    # 미디어 업로드 객체 생성
    media = MediaIoBaseUpload(
        io.BytesIO(json_bytes),
        mimetype='application/json',
        resumable=True
    )
    
    # 기존 파일 검색
    existing = find_file_by_name(service, file_name, folder_id)
    
    if existing:
        # 업데이트 (소유자는 그대로 유지)
        file = service.files().update(
            fileId=existing['id'],
            media_body=media,
            fields='id, name, modifiedTime',
            supportsAllDrives=True
        ).execute()
        print(f"   📝 파일 업데이트: {file_name}")
    else:
        # 새로 생성 (남편분 폴더 안에 만들기 - 폴더 소유자가 자동으로 소유)
        file_metadata = {
            'name': file_name,
            'parents': [folder_id]
        }
        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id, name',
            supportsAllDrives=True
        ).execute()
        print(f"   ✨ 새 파일 생성: {file_name}")
    
    return file.get('id')


def load_json(file_name, folder_id=None, default=None):
    """
    Google Drive에서 JSON 파일 로드.
    파일이 없으면 default 반환.
    """
    if folder_id is None:
        folder_id = GDRIVE_FOLDER_ID
    
    if default is None:
        default = {}
    
    service = get_drive_service()
    existing = find_file_by_name(service, file_name, folder_id)
    
    if not existing:
        print(f"   ℹ️  파일 없음 (기본값 사용): {file_name}")
        return default
    
    # 파일 다운로드
    request = service.files().get_media(
        fileId=existing['id'],
        supportsAllDrives=True
    )
    file_bytes = io.BytesIO()
    downloader = MediaIoBaseDownload(file_bytes, request)
    
    done = False
    while not done:
        status, done = downloader.next_chunk()
    
    # JSON 파싱
    file_bytes.seek(0)
    data = json.loads(file_bytes.read().decode('utf-8'))
    
    print(f"   📖 파일 로드: {file_name}")
    return data


def delete_file(file_name, folder_id=None):
    """파일 삭제"""
    if folder_id is None:
        folder_id = GDRIVE_FOLDER_ID
    
    service = get_drive_service()
    existing = find_file_by_name(service, file_name, folder_id)
    
    if not existing:
        return False
    
    service.files().delete(
        fileId=existing['id'],
        supportsAllDrives=True
    ).execute()
    print(f"   🗑️  파일 삭제: {file_name}")
    return True


def list_files(folder_id=None):
    """폴더 안의 파일 목록 반환"""
    if folder_id is None:
        folder_id = GDRIVE_FOLDER_ID
    
    service = get_drive_service()
    
    results = service.files().list(
        q=f"'{folder_id}' in parents and trashed=false",
        fields='files(id, name, mimeType, modifiedTime, size)',
        supportsAllDrives=True,
        includeItemsFromAllDrives=True
    ).execute()
    
    return results.get('files', [])


def test_storage():
    """저장/로드 테스트"""
    print("=" * 60)
    print("💾 데이터 저장/로드 테스트")
    print("=" * 60)
    
    test_data = {
        "test_id": 1,
        "message": "안녕하세요! 두유당 대출관리 앱입니다 🎉",
        "timestamp": datetime.now().isoformat(),
        "items": ["신용대출1", "신용대출2", "주택자금대출"]
    }
    
    print("\n1️⃣  저장 테스트...")
    save_json(test_data, "_test.json")
    
    print("\n2️⃣  로드 테스트...")
    loaded_data = load_json("_test.json")
    
    print("\n3️⃣  데이터 검증...")
    print(f"   저장한 메시지: {test_data['message']}")
    print(f"   불러온 메시지: {loaded_data.get('message')}")
    
    if test_data['message'] == loaded_data.get('message'):
        print(f"   ✅ 데이터 일치! 저장/로드 정상 작동")
    else:
        print(f"   ❌ 데이터 불일치")
        return False
    
    print("\n4️⃣  테스트 파일 정리...")
    delete_file("_test.json")
    
    print("\n" + "=" * 60)
    print("🎉 저장/로드 테스트 통과!")
    print("=" * 60)
    return True


if __name__ == '__main__':
    test_storage()