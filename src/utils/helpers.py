"""공통 유틸리티 함수"""

import uuid
from datetime import datetime


def generate_id():
    """고유 ID 생성"""
    return str(uuid.uuid4())


def now_iso():
    """현재 시각 ISO 형식 문자열"""
    return datetime.now().isoformat()


def format_currency(amount):
    """금액 포맷팅: 1234567 → '1,234,567원'"""
    if amount is None:
        return "0원"
    return f"{int(amount):,}원"


def parse_date(date_str):
    """날짜 문자열을 datetime으로 변환"""
    if isinstance(date_str, datetime):
        return date_str
    if isinstance(date_str, str):
        for fmt in ['%Y-%m-%d', '%Y.%m.%d', '%Y/%m/%d', '%Y-%m-%dT%H:%M:%S']:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        try:
            return datetime.fromisoformat(date_str)
        except ValueError:
            pass
    return None
