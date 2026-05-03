"""
Google Drive 폴더 관리 모듈
- 두유당_대출관리/ 안에 backups/, exports/ 하위 폴더 자동 생성
"""

from src.services.drive_auth import get_drive_service, GDRIVE_FOLDER_ID

# 생성할 하위 폴더들
SUBFOLDERS = ['backups', 'exports']


def find_folder(service, folder_name, parent_id):
    """이름으로 하위 폴더 검색. 있으면 ID 반환, 없으면 None"""
    query = (
        f"name='{folder_name}' and "
        f"mimeType='application/vnd.google-apps.folder' and "
        f"'{parent_id}' in parents and "
        f"trashed=false"
    )
    
    results = service.files().list(
        q=query,
        fields='files(id, name)'
    ).execute()
    
    folders = results.get('files', [])
    return folders[0]['id'] if folders else None


def create_folder(service, folder_name, parent_id):
    """폴더 생성. ID 반환"""
    file_metadata = {
        'name': folder_name,
        'mimeType': 'application/vnd.google-apps.folder',
        'parents': [parent_id]
    }
    
    folder = service.files().create(
        body=file_metadata,
        fields='id'
    ).execute()
    
    return folder.get('id')


def get_or_create_folder(service, folder_name, parent_id):
    """폴더가 있으면 ID 반환, 없으면 생성"""
    folder_id = find_folder(service, folder_name, parent_id)
    if folder_id:
        print(f"   📁 기존 폴더 사용: {folder_name}")
        return folder_id
    
    folder_id = create_folder(service, folder_name, parent_id)
    print(f"   ✨ 새 폴더 생성: {folder_name}")
    return folder_id


def setup_drive_folders():
    """앱에 필요한 모든 폴더 셋업"""
    print("=" * 60)
    print("🗂️  Google Drive 폴더 셋업 시작")
    print("=" * 60)
    
    service = get_drive_service()
    
    # 메인 폴더 ID는 이미 있음 (남편분 Drive에 만든 폴더)
    main_folder_id = GDRIVE_FOLDER_ID
    print(f"\n📁 메인 폴더 ID: {main_folder_id[:10]}...")
    
    # 하위 폴더들 생성/확인
    print("\n📋 하위 폴더 셋업:")
    subfolder_ids = {}
    for subfolder_name in SUBFOLDERS:
        subfolder_id = get_or_create_folder(
            service,
            subfolder_name,
            parent_id=main_folder_id
        )
        subfolder_ids[subfolder_name] = subfolder_id
    
    print("\n" + "=" * 60)
    print("✅ 폴더 셋업 완료!")
    print("=" * 60)
    print(f"\n📋 폴더 정보:")
    print(f"   메인 폴더: {main_folder_id}")
    for name, fid in subfolder_ids.items():
        print(f"   {name}/: {fid}")
    
    return {
        'main_folder_id': main_folder_id,
        **subfolder_ids
    }


if __name__ == '__main__':
    folder_info = setup_drive_folders()