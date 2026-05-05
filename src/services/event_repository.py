"""이벤트 자금 데이터 저장소"""

from typing import List
from src.models.event import FundEvent
from src.services.drive_storage import save_json, load_json
from src.utils.helpers import now_iso


EVENTS_FILE = "fund_events.json"


def get_all_events() -> List[FundEvent]:
    """모든 이벤트 자금 조회 (예상 날짜순)"""
    data = load_json(EVENTS_FILE) or []
    
    events = []
    for d in data:
        try:
            events.append(FundEvent.from_dict(d))
        except Exception as e:
            print(f"⚠️ event 로드 실패: {e}")
    
    # 예상 날짜순 정렬
    events.sort(key=lambda e: e.expected_date)
    
    return events


def get_event_by_id(event_id: str) -> FundEvent:
    """특정 이벤트 조회"""
    for event in get_all_events():
        if event.event_id == event_id:
            return event
    return None


def get_upcoming_events(months_ahead: int = 60) -> List[FundEvent]:
    """향후 N개월 이내 예정된 이벤트 (수령 안 한 것만)"""
    from datetime import datetime, timedelta
    
    all_events = get_all_events()
    
    today = datetime.now()
    cutoff = today + timedelta(days=months_ahead * 30)
    
    upcoming = []
    for e in all_events:
        if e.is_received:
            continue
        
        try:
            expected = datetime.strptime(e.expected_date, "%Y-%m-%d")
            if today.date() <= expected.date() <= cutoff.date():
                upcoming.append(e)
        except:
            continue
    
    return upcoming


def get_received_events() -> List[FundEvent]:
    """이미 수령한 이벤트"""
    return [e for e in get_all_events() if e.is_received]


def add_event(event: FundEvent) -> dict:
    """신규 이벤트 추가"""
    # 검증
    if not event.event_name:
        return {
            'success': False,
            'message': '❌ 이벤트 이름을 입력해주세요.',
            'event': None,
        }
    
    if event.amount <= 0:
        return {
            'success': False,
            'message': '❌ 금액은 0보다 커야 합니다.',
            'event': None,
        }
    
    if not event.expected_date:
        return {
            'success': False,
            'message': '❌ 예상 날짜를 입력해주세요.',
            'event': None,
        }
    
    # 저장
    all_events_data = load_json(EVENTS_FILE) or []
    all_events_data.append(event.to_dict())
    
    try:
        save_json(EVENTS_FILE, all_events_data)
    except Exception as e:
        return {
            'success': False,
            'message': f'❌ 저장 실패: {str(e)}',
            'event': None,
        }
    
    return {
        'success': True,
        'message': f'✅ 이벤트 등록 완료: {event.event_name}',
        'event': event,
    }


def update_event(event_id: str, updates: dict) -> dict:
    """이벤트 정보 수정"""
    all_events_data = load_json(EVENTS_FILE) or []
    
    target_index = None
    for i, e_dict in enumerate(all_events_data):
        if e_dict.get('event_id') == event_id:
            target_index = i
            break
    
    if target_index is None:
        return {
            'success': False,
            'message': '❌ 이벤트를 찾을 수 없습니다.',
            'event': None,
        }
    
    # 업데이트
    for key, value in updates.items():
        all_events_data[target_index][key] = value
    
    all_events_data[target_index]['updated_at'] = now_iso()
    
    try:
        save_json(EVENTS_FILE, all_events_data)
    except Exception as e:
        return {
            'success': False,
            'message': f'❌ 저장 실패: {str(e)}',
            'event': None,
        }
    
    updated_event = FundEvent.from_dict(all_events_data[target_index])
    
    return {
        'success': True,
        'message': '✅ 이벤트 정보 수정 완료',
        'event': updated_event,
    }


def delete_event(event_id: str) -> dict:
    """이벤트 삭제"""
    all_events_data = load_json(EVENTS_FILE) or []
    
    target_index = None
    target_name = ""
    
    for i, e_dict in enumerate(all_events_data):
        if e_dict.get('event_id') == event_id:
            target_index = i
            target_name = e_dict.get('event_name', '알 수 없음')
            break
    
    if target_index is None:
        return {
            'success': False,
            'message': '❌ 이벤트를 찾을 수 없습니다.',
        }
    
    all_events_data.pop(target_index)
    
    try:
        save_json(EVENTS_FILE, all_events_data)
    except Exception as e:
        return {
            'success': False,
            'message': f'❌ 삭제 실패: {str(e)}',
        }
    
    return {
        'success': True,
        'message': f'✅ "{target_name}" 이벤트 삭제 완료',
    }


def get_total_upcoming_amount() -> float:
    """향후 5년 예상 총 가용 자금"""
    upcoming = get_upcoming_events(months_ahead=60)
    return sum(e.amount for e in upcoming)


def mark_as_received(event_id: str, actual_amount: float, actual_date: str) -> dict:
    """이벤트 수령 처리"""
    return update_event(event_id, {
        'is_received': True,
        'actual_amount': actual_amount,
        'actual_date': actual_date,
    })