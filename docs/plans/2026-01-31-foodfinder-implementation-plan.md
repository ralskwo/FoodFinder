# FoodFinder 고도화 구현 계획

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 위치/반경/예산/카테고리 기반 음식점 검색 및 메뉴 가격 필터링 기능 구현

**Architecture:** React 프론트엔드 + Flask 백엔드, 네이버 지도 API 통합, 하이브리드 크롤링 시스템 (네이버 플레이스 → 배달앱 → 카카오 → 사용자입력)

**Tech Stack:** React 18, Flask 3.0, SQLAlchemy 2.0, Naver Maps JS API v3, BeautifulSoup, SQLite

---

## Phase 1: Backend 데이터베이스 및 모델

### Task 1: Menu 모델 추가

**Files:**
- Create: `backend/models/menu.py`
- Modify: `backend/models/__init__.py`
- Modify: `backend/database.py` (import 추가)

**Step 1: Menu 모델 파일 생성**

```python
# backend/models/menu.py
from datetime import datetime, timezone
from database import db


class Menu(db.Model):
    """메뉴 정보 모델"""
    __tablename__ = 'menus'

    id = db.Column(db.Integer, primary_key=True)
    restaurant_id = db.Column(db.Integer, db.ForeignKey('restaurants.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Integer)  # 원 단위
    is_representative = db.Column(db.Boolean, default=False)
    source = db.Column(db.String(20))  # 'naver', 'baemin', 'yogiyo', 'kakao', 'user'
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                          onupdate=lambda: datetime.now(timezone.utc))

    # Relationship
    restaurant = db.relationship('Restaurant', backref=db.backref('menus', lazy='dynamic'))

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'price': self.price,
            'is_representative': self.is_representative,
            'source': self.source,
        }

    def __repr__(self):
        return f'<Menu {self.name} - {self.price}원>'
```

**Step 2: Restaurant 모델에 review_count, road_address 필드 추가**

`backend/models/restaurant.py` 수정:
- line 14 뒤에 추가:
```python
    road_address = db.Column(db.String(300))
    review_count = db.Column(db.Integer)
```

**Step 3: models/__init__.py 생성**

```python
# backend/models/__init__.py
from models.restaurant import Restaurant
from models.menu import Menu

__all__ = ['Restaurant', 'Menu']
```

**Step 4: DB 마이그레이션 실행**

```bash
cd backend
python -c "from app import create_app; from database import db; app = create_app(); app.app_context().push(); db.create_all(); print('DB migrated')"
```

**Step 5: Commit**

```bash
git add backend/models/
git commit -m "feat: add Menu model for storing menu/price data

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

### Task 2: UserMenuContribution 모델 추가

**Files:**
- Create: `backend/models/user_contribution.py`
- Modify: `backend/models/__init__.py`

**Step 1: UserMenuContribution 모델 생성**

```python
# backend/models/user_contribution.py
from datetime import datetime, timezone
from database import db


class UserMenuContribution(db.Model):
    """사용자 입력 메뉴 정보"""
    __tablename__ = 'user_menu_contributions'

    id = db.Column(db.Integer, primary_key=True)
    restaurant_id = db.Column(db.Integer, db.ForeignKey('restaurants.id'), nullable=False)
    menu_name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Integer)
    contributed_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    restaurant = db.relationship('Restaurant', backref=db.backref('user_contributions', lazy='dynamic'))

    def to_dict(self):
        return {
            'id': self.id,
            'menu_name': self.menu_name,
            'price': self.price,
            'contributed_at': self.contributed_at.isoformat() if self.contributed_at else None,
        }
```

**Step 2: __init__.py 업데이트**

```python
# backend/models/__init__.py
from models.restaurant import Restaurant
from models.menu import Menu
from models.user_contribution import UserMenuContribution

__all__ = ['Restaurant', 'Menu', 'UserMenuContribution']
```

**Step 3: Commit**

```bash
git add backend/models/
git commit -m "feat: add UserMenuContribution model

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

## Phase 2: Backend 크롤링 서비스

### Task 3: 네이버 플레이스 크롤러 구현

**Files:**
- Create: `backend/crawlers/__init__.py`
- Create: `backend/crawlers/naver_place.py`

**Step 1: crawlers 디렉토리 및 __init__.py 생성**

```python
# backend/crawlers/__init__.py
from crawlers.naver_place import NaverPlaceCrawler

__all__ = ['NaverPlaceCrawler']
```

**Step 2: 네이버 플레이스 크롤러 구현**

```python
# backend/crawlers/naver_place.py
import requests
from bs4 import BeautifulSoup
import re
import time
import logging

logger = logging.getLogger(__name__)


class NaverPlaceCrawler:
    """네이버 플레이스에서 메뉴 정보 크롤링"""

    BASE_URL = "https://pcmap.place.naver.com/restaurant/{place_id}/menu"

    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
    }

    def __init__(self, delay: float = 0.5):
        self.delay = delay
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)

    def get_menus(self, place_id: str) -> list:
        """
        네이버 플레이스에서 메뉴 정보 크롤링

        Args:
            place_id: 네이버 플레이스 ID

        Returns:
            list: [{'name': '메뉴명', 'price': 가격(int), 'is_representative': bool}, ...]
        """
        try:
            url = self.BASE_URL.format(place_id=place_id)
            time.sleep(self.delay)

            response = self.session.get(url, timeout=10)

            if response.status_code != 200:
                logger.warning(f"Naver Place returned {response.status_code} for {place_id}")
                return []

            soup = BeautifulSoup(response.text, 'html.parser')
            menus = []

            # 메뉴 아이템 파싱 (네이버 플레이스 구조에 따라 조정 필요)
            menu_items = soup.select('.menu_item, .item_menu, [class*="menu"]')

            for item in menu_items:
                try:
                    name_elem = item.select_one('.name, .menu_name, [class*="name"]')
                    price_elem = item.select_one('.price, .menu_price, [class*="price"]')

                    if not name_elem:
                        continue

                    name = name_elem.get_text(strip=True)
                    price = None

                    if price_elem:
                        price_text = price_elem.get_text(strip=True)
                        # 숫자만 추출 (예: "8,000원" -> 8000)
                        price_numbers = re.findall(r'[\d,]+', price_text)
                        if price_numbers:
                            price = int(price_numbers[0].replace(',', ''))

                    if name:
                        menus.append({
                            'name': name,
                            'price': price,
                            'is_representative': len(menus) < 2  # 처음 2개를 대표메뉴로
                        })
                except Exception as e:
                    logger.debug(f"Failed to parse menu item: {e}")
                    continue

            logger.info(f"Crawled {len(menus)} menus from Naver Place {place_id}")
            return menus

        except requests.RequestException as e:
            logger.error(f"Naver Place crawl failed for {place_id}: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error crawling {place_id}: {e}")
            return []

    def get_place_id_from_link(self, naver_link: str) -> str:
        """
        네이버 링크에서 place_id 추출

        Args:
            naver_link: 네이버 검색 결과의 link 필드

        Returns:
            place_id 또는 None
        """
        # 예: https://map.naver.com/v5/search/...?placePath=?entry=pll&from=nx&fromNx498...
        # 또는 place/1234567890 형태
        patterns = [
            r'place/(\d+)',
            r'place_id=(\d+)',
            r'/(\d{8,})',  # 8자리 이상 숫자
        ]

        for pattern in patterns:
            match = re.search(pattern, naver_link)
            if match:
                return match.group(1)

        return None
```

**Step 3: requirements.txt에 beautifulsoup4 추가**

`backend/requirements.txt`에 추가:
```
beautifulsoup4==4.12.2
```

**Step 4: Commit**

```bash
git add backend/crawlers/ backend/requirements.txt
git commit -m "feat: add Naver Place crawler for menu data

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

### Task 4: 배달앱 크롤러 구현 (배달의민족/요기요)

**Files:**
- Create: `backend/crawlers/delivery_apps.py`
- Modify: `backend/crawlers/__init__.py`

**Step 1: 배달앱 크롤러 구현**

```python
# backend/crawlers/delivery_apps.py
import requests
import re
import time
import logging

logger = logging.getLogger(__name__)


class DeliveryAppCrawler:
    """배달앱에서 메뉴 정보 크롤링 (배달의민족, 요기요)"""

    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json',
    }

    def __init__(self, delay: float = 0.5):
        self.delay = delay
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)

    def search_baemin(self, restaurant_name: str, address: str) -> list:
        """
        배달의민족에서 음식점 메뉴 검색

        Note: 배달의민족은 공식 API가 없어 웹 스크래핑이 제한적임.
              실제 구현 시 Selenium/Playwright 필요할 수 있음.
        """
        try:
            time.sleep(self.delay)
            # 배달의민족 웹사이트 구조 변경이 잦아 실제 크롤링은 복잡함
            # 여기서는 기본 구조만 제공
            logger.info(f"Baemin search for: {restaurant_name}")
            return []
        except Exception as e:
            logger.error(f"Baemin crawl failed: {e}")
            return []

    def search_yogiyo(self, restaurant_name: str, address: str) -> list:
        """
        요기요에서 음식점 메뉴 검색

        Note: 요기요도 공식 API가 없어 웹 스크래핑이 제한적임.
        """
        try:
            time.sleep(self.delay)
            logger.info(f"Yogiyo search for: {restaurant_name}")
            return []
        except Exception as e:
            logger.error(f"Yogiyo crawl failed: {e}")
            return []

    def get_menus(self, restaurant_name: str, address: str) -> list:
        """
        배달앱에서 메뉴 정보 통합 검색

        Returns:
            list: [{'name': '메뉴명', 'price': 가격(int), 'is_representative': bool}, ...]
        """
        # 배달의민족 먼저 시도
        menus = self.search_baemin(restaurant_name, address)

        # 결과 없으면 요기요 시도
        if not menus:
            menus = self.search_yogiyo(restaurant_name, address)

        return menus
```

**Step 2: __init__.py 업데이트**

```python
# backend/crawlers/__init__.py
from crawlers.naver_place import NaverPlaceCrawler
from crawlers.delivery_apps import DeliveryAppCrawler

__all__ = ['NaverPlaceCrawler', 'DeliveryAppCrawler']
```

**Step 3: Commit**

```bash
git add backend/crawlers/
git commit -m "feat: add delivery app crawler (placeholder for baemin/yogiyo)

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

### Task 5: 카카오맵 API 클라이언트 구현

**Files:**
- Create: `backend/api/kakao_map.py`
- Modify: `backend/config.py` (카카오 API 키 추가)

**Step 1: 카카오맵 API 클라이언트**

```python
# backend/api/kakao_map.py
import requests
import logging

logger = logging.getLogger(__name__)


class KakaoMapClient:
    """카카오맵 API 클라이언트"""

    SEARCH_URL = "https://dapi.kakao.com/v2/local/search/keyword.json"

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.headers = {
            'Authorization': f'KakaoAK {api_key}'
        }

    def search_restaurant(self, query: str, x: float = None, y: float = None, radius: int = 2000) -> dict:
        """
        카카오 로컬 검색 API로 음식점 검색

        Args:
            query: 검색어 (음식점명)
            x: 경도 (longitude)
            y: 위도 (latitude)
            radius: 검색 반경 (미터)
        """
        try:
            params = {
                'query': query,
                'category_group_code': 'FD6',  # 음식점
                'size': 5
            }

            if x and y:
                params['x'] = x
                params['y'] = y
                params['radius'] = radius
                params['sort'] = 'distance'

            response = requests.get(
                self.SEARCH_URL,
                headers=self.headers,
                params=params,
                timeout=5
            )

            if response.status_code == 200:
                data = response.json()
                documents = data.get('documents', [])
                if documents:
                    return documents[0]  # 가장 관련성 높은 결과

            return None

        except Exception as e:
            logger.error(f"Kakao API error: {e}")
            return None

    def get_menu_info(self, restaurant_name: str, address: str) -> list:
        """
        카카오맵에서 메뉴 정보 조회

        Note: 카카오 로컬 API는 기본 정보만 제공하며,
              상세 메뉴 정보는 제한적임.
        """
        # 카카오 로컬 API는 메뉴 정보를 직접 제공하지 않음
        # place_url을 통해 웹페이지 크롤링이 필요할 수 있음
        logger.info(f"Kakao menu search for: {restaurant_name}")
        return []
```

**Step 2: config.py에 카카오 API 키 추가**

`backend/config.py` 수정 - Config 클래스에 추가:
```python
    KAKAO_API_KEY = os.getenv('KAKAO_API_KEY', '')
```

**Step 3: .env.example 업데이트**

```
KAKAO_API_KEY=your-kakao-rest-api-key
```

**Step 4: Commit**

```bash
git add backend/api/kakao_map.py backend/config.py
git commit -m "feat: add Kakao Map API client

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

### Task 6: 메뉴 서비스 (하이브리드 캐싱) 구현

**Files:**
- Create: `backend/services/__init__.py`
- Create: `backend/services/menu_service.py`

**Step 1: services 디렉토리 및 __init__.py 생성**

```python
# backend/services/__init__.py
from services.menu_service import MenuService

__all__ = ['MenuService']
```

**Step 2: 메뉴 서비스 구현**

```python
# backend/services/menu_service.py
from datetime import datetime, timezone, timedelta
from database import db
from models.menu import Menu
from models.restaurant import Restaurant
from crawlers.naver_place import NaverPlaceCrawler
from crawlers.delivery_apps import DeliveryAppCrawler
from api.kakao_map import KakaoMapClient
from config import Config
import logging

logger = logging.getLogger(__name__)


class MenuService:
    """메뉴 정보 조회 서비스 (하이브리드 캐싱)"""

    CACHE_DURATION_HOURS = 24

    def __init__(self):
        self.naver_crawler = NaverPlaceCrawler()
        self.delivery_crawler = DeliveryAppCrawler()
        self.kakao_client = KakaoMapClient(Config.KAKAO_API_KEY) if Config.KAKAO_API_KEY else None

    def get_menus(self, restaurant: Restaurant, naver_link: str = None) -> list:
        """
        메뉴 정보 조회 (캐시 우선, 없으면 크롤링)

        Args:
            restaurant: Restaurant 모델 인스턴스
            naver_link: 네이버 검색 결과의 link (place_id 추출용)

        Returns:
            list: Menu 객체 리스트
        """
        # 1. 캐시 확인
        cached_menus = self._get_cached_menus(restaurant.id)
        if cached_menus:
            logger.info(f"Cache hit for restaurant {restaurant.id}")
            return cached_menus

        # 2. 캐시 없으면 크롤링
        logger.info(f"Cache miss, crawling menus for {restaurant.name}")
        menu_data = self._crawl_menus(restaurant, naver_link)

        # 3. 결과 저장
        if menu_data:
            self._save_menus(restaurant.id, menu_data)
            return self._get_cached_menus(restaurant.id)

        return []

    def _get_cached_menus(self, restaurant_id: int) -> list:
        """캐시된 메뉴 조회 (24시간 이내)"""
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=self.CACHE_DURATION_HOURS)

        menus = Menu.query.filter(
            Menu.restaurant_id == restaurant_id,
            Menu.updated_at >= cutoff_time
        ).all()

        return menus if menus else None

    def _crawl_menus(self, restaurant: Restaurant, naver_link: str = None) -> list:
        """
        크롤링 우선순위에 따라 메뉴 정보 수집
        1순위: 네이버 플레이스
        2순위: 배달앱
        3순위: 카카오맵
        """
        menu_data = []
        source = None

        # 1순위: 네이버 플레이스
        if naver_link:
            place_id = self.naver_crawler.get_place_id_from_link(naver_link)
            if place_id:
                menu_data = self.naver_crawler.get_menus(place_id)
                if menu_data:
                    source = 'naver'

        # 2순위: 배달앱
        if not menu_data:
            menu_data = self.delivery_crawler.get_menus(
                restaurant.name,
                restaurant.address or restaurant.road_address
            )
            if menu_data:
                source = 'delivery'

        # 3순위: 카카오맵
        if not menu_data and self.kakao_client:
            menu_data = self.kakao_client.get_menu_info(
                restaurant.name,
                restaurant.address
            )
            if menu_data:
                source = 'kakao'

        # source 추가
        for item in menu_data:
            item['source'] = source

        return menu_data

    def _save_menus(self, restaurant_id: int, menu_data: list):
        """메뉴 정보 DB 저장"""
        try:
            # 기존 메뉴 삭제 (user 소스 제외)
            Menu.query.filter(
                Menu.restaurant_id == restaurant_id,
                Menu.source != 'user'
            ).delete()

            # 새 메뉴 저장
            for item in menu_data:
                menu = Menu(
                    restaurant_id=restaurant_id,
                    name=item['name'],
                    price=item.get('price'),
                    is_representative=item.get('is_representative', False),
                    source=item.get('source', 'unknown')
                )
                db.session.add(menu)

            db.session.commit()
            logger.info(f"Saved {len(menu_data)} menus for restaurant {restaurant_id}")

        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to save menus: {e}")

    def add_user_contribution(self, restaurant_id: int, menu_name: str, price: int) -> Menu:
        """사용자 입력 메뉴 추가"""
        try:
            menu = Menu(
                restaurant_id=restaurant_id,
                name=menu_name,
                price=price,
                is_representative=False,
                source='user'
            )
            db.session.add(menu)
            db.session.commit()
            return menu
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to add user contribution: {e}")
            return None
```

**Step 3: Commit**

```bash
git add backend/services/
git commit -m "feat: add MenuService with hybrid caching strategy

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

## Phase 3: Backend API 업데이트

### Task 7: Restaurant API 업데이트 (예산 필터링 추가)

**Files:**
- Modify: `backend/api/restaurant.py`

**Step 1: 검색 API에 예산 필터링 추가**

`backend/api/restaurant.py` 전체 재작성:

```python
# backend/api/restaurant.py
from flask import Blueprint, request, jsonify
from api.naver_map import NaverMapClient
from api.naver_geocoding import NaverGeocodingClient
from database import db
from models.restaurant import Restaurant
from models.menu import Menu
from services.menu_service import MenuService
from config import Config
import logging
import math

logger = logging.getLogger(__name__)

restaurant_bp = Blueprint('restaurant', __name__)
menu_service = MenuService()


def haversine_distance(lat1, lon1, lat2, lon2):
    """하버사인 공식으로 두 좌표 간 거리 계산 (미터)"""
    R = 6371000  # 지구 반경 (미터)

    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi/2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

    return R * c


@restaurant_bp.route('/geocode/reverse', methods=['GET'])
def reverse_geocode():
    """좌표를 주소로 변환"""
    latitude = request.args.get('lat', type=float)
    longitude = request.args.get('lng', type=float) or request.args.get('lon', type=float)

    if latitude is None or longitude is None:
        return jsonify({'error': '위도와 경도는 필수입니다'}), 400

    geocoding_client = NaverGeocodingClient(
        Config.NAVER_CLOUD_ID,
        Config.NAVER_CLOUD_SECRET
    )

    address = geocoding_client.coord_to_address(longitude, latitude)

    if address:
        return jsonify({
            'address': address,
            'latitude': latitude,
            'longitude': longitude
        }), 200
    else:
        return jsonify({
            'address': f'위도: {latitude:.4f}, 경도: {longitude:.4f}',
            'latitude': latitude,
            'longitude': longitude
        }), 200


@restaurant_bp.route('/geocode', methods=['GET'])
def geocode_address():
    """주소를 좌표로 변환"""
    query = request.args.get('query')

    if not query:
        return jsonify({'error': '검색어를 입력하세요'}), 400

    geocoding_client = NaverGeocodingClient(
        Config.NAVER_CLOUD_ID,
        Config.NAVER_CLOUD_SECRET
    )

    result = geocoding_client.address_to_coord(query)

    if result:
        return jsonify(result), 200
    else:
        return jsonify({'error': '주소를 찾을 수 없습니다'}), 404


@restaurant_bp.route('/restaurants/search', methods=['POST'])
def search_restaurants():
    """
    맛집 검색 API (예산 필터링 포함)

    Request Body:
    {
        "lat": 37.5665,
        "lng": 126.9780,
        "radius": 2000,
        "budget": 12000,           // optional
        "budget_type": "menu",     // "menu" or "average"
        "categories": ["한식"],    // optional
        "query": "음식점"          // optional
    }
    """
    data = request.get_json()

    # 필수 파라미터 검증
    if not data:
        return jsonify({'error': '요청 데이터가 없습니다'}), 400

    lat = data.get('lat') or data.get('latitude')
    lng = data.get('lng') or data.get('longitude')

    if lat is None or lng is None:
        return jsonify({'error': '위치 정보는 필수입니다'}), 400

    try:
        lat = float(lat)
        lng = float(lng)
        radius = int(data.get('radius', Config.DEFAULT_SEARCH_RADIUS))
        budget = data.get('budget')
        budget_type = data.get('budget_type', 'menu')  # 'menu' or 'average'
        categories = data.get('categories', [])
        query = data.get('query', '음식점')
    except (ValueError, TypeError) as e:
        return jsonify({'error': '잘못된 입력값입니다'}), 400

    logger.info(f"Search: query={query}, lat={lat}, lng={lng}, radius={radius}, budget={budget}")

    # 네이버 API 호출
    naver_client = NaverMapClient(
        Config.NAVER_CLIENT_ID,
        Config.NAVER_CLIENT_SECRET
    )

    raw_results = naver_client.search_local(
        query=query,
        latitude=lat,
        longitude=lng,
        radius=radius
    )

    # 결과 처리
    results = []
    for item in raw_results:
        # 거리 재계산 (하버사인)
        if item.get('latitude') and item.get('longitude'):
            distance = haversine_distance(lat, lng, item['latitude'], item['longitude'])

            # 반경 필터
            if distance > radius:
                continue

            item['distance'] = int(distance)

        # 카테고리 필터
        if categories:
            item_category = item.get('category', '')
            if not any(cat in item_category for cat in categories):
                continue

        # DB에서 음식점 조회 또는 생성
        restaurant = get_or_create_restaurant(item)

        # 메뉴 정보 조회
        menus = menu_service.get_menus(restaurant, item.get('link'))

        # 예산 필터링
        if budget and menus:
            if budget_type == 'menu':
                # 메뉴 기준: 예산 이하 메뉴가 1개 이상
                has_affordable = any(m.price and m.price <= budget for m in menus)
                if not has_affordable:
                    continue
            elif budget_type == 'average':
                # 평균 기준: 전체 메뉴 평균이 예산 이하
                prices = [m.price for m in menus if m.price]
                if prices:
                    avg_price = sum(prices) / len(prices)
                    if avg_price > budget:
                        continue

        # 대표 메뉴 추출
        representative_menus = [
            {'name': m.name, 'price': m.price}
            for m in menus if m.is_representative
        ][:2]

        # 대표 메뉴 없으면 가장 저렴한 2개
        if not representative_menus and menus:
            sorted_menus = sorted([m for m in menus if m.price], key=lambda x: x.price)
            representative_menus = [
                {'name': m.name, 'price': m.price}
                for m in sorted_menus[:2]
            ]

        results.append({
            'place_id': restaurant.place_id,
            'name': item['title'],
            'category': item.get('category', ''),
            'address': item.get('address', ''),
            'road_address': item.get('road_address', ''),
            'latitude': item.get('latitude'),
            'longitude': item.get('longitude'),
            'distance': item.get('distance'),
            'phone': item.get('telephone', ''),
            'rating': restaurant.rating,
            'representative_menus': representative_menus,
            'link': item.get('link', '')
        })

    # 거리순 정렬
    results.sort(key=lambda x: x.get('distance', 999999))

    return jsonify({
        'results': results,
        'total': len(results),
        'filters_applied': {
            'radius': radius,
            'budget': budget,
            'budget_type': budget_type if budget else None,
            'categories': categories
        }
    }), 200


def get_or_create_restaurant(item: dict) -> Restaurant:
    """음식점 DB 조회 또는 생성"""
    # place_id 생성 (link에서 추출 또는 이름+주소 해시)
    place_id = item.get('link', '') or f"{item['title']}_{item.get('address', '')}"
    place_id = str(hash(place_id))[:20]

    restaurant = Restaurant.query.filter_by(place_id=place_id).first()

    if not restaurant:
        restaurant = Restaurant(
            place_id=place_id,
            name=item['title'],
            category=item.get('category', ''),
            address=item.get('address', ''),
            road_address=item.get('road_address', ''),
            latitude=item.get('latitude', 0.0),
            longitude=item.get('longitude', 0.0),
            phone=item.get('telephone', '')
        )
        db.session.add(restaurant)
        try:
            db.session.commit()
        except:
            db.session.rollback()
            restaurant = Restaurant.query.filter_by(place_id=place_id).first()

    return restaurant


@restaurant_bp.route('/restaurants/<place_id>', methods=['GET'])
def get_restaurant_detail(place_id):
    """음식점 상세 정보"""
    restaurant = Restaurant.query.filter_by(place_id=place_id).first()

    if not restaurant:
        return jsonify({'error': '음식점을 찾을 수 없습니다'}), 404

    return jsonify(restaurant.to_dict()), 200


@restaurant_bp.route('/restaurants/<place_id>/menus', methods=['GET'])
def get_restaurant_menus(place_id):
    """음식점 전체 메뉴 목록"""
    restaurant = Restaurant.query.filter_by(place_id=place_id).first()

    if not restaurant:
        return jsonify({'error': '음식점을 찾을 수 없습니다'}), 404

    menus = menu_service.get_menus(restaurant)

    return jsonify({
        'restaurant_id': restaurant.id,
        'restaurant_name': restaurant.name,
        'menus': [m.to_dict() for m in menus]
    }), 200


@restaurant_bp.route('/restaurants/<place_id>/menus/contribute', methods=['POST'])
def contribute_menu(place_id):
    """사용자 메뉴 정보 입력"""
    data = request.get_json()

    if not data or 'menu_name' not in data:
        return jsonify({'error': '메뉴명은 필수입니다'}), 400

    restaurant = Restaurant.query.filter_by(place_id=place_id).first()

    if not restaurant:
        return jsonify({'error': '음식점을 찾을 수 없습니다'}), 404

    menu = menu_service.add_user_contribution(
        restaurant.id,
        data['menu_name'],
        data.get('price')
    )

    if menu:
        return jsonify(menu.to_dict()), 201
    else:
        return jsonify({'error': '메뉴 추가에 실패했습니다'}), 500


@restaurant_bp.route('/restaurants/<place_id>/delivery', methods=['POST'])
def update_delivery_info(place_id):
    """배달 정보 업데이트 (사용자 입력)"""
    data = request.get_json()

    try:
        restaurant = Restaurant.query.filter_by(place_id=place_id).first()

        if not restaurant:
            restaurant = Restaurant(
                place_id=place_id,
                name=data.get('name', 'Unknown'),
                latitude=float(data.get('latitude', 0.0)),
                longitude=float(data.get('longitude', 0.0))
            )
            db.session.add(restaurant)

        if 'delivery_fee' in data:
            restaurant.delivery_fee = data['delivery_fee']
            restaurant.delivery_available = True

        if 'minimum_order' in data:
            restaurant.minimum_order = data['minimum_order']

        db.session.commit()

        return jsonify(restaurant.to_dict()), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f"배달 정보 업데이트 실패: {e}")
        return jsonify({'error': '업데이트에 실패했습니다'}), 500
```

**Step 2: Commit**

```bash
git add backend/api/restaurant.py
git commit -m "feat: update restaurant API with budget filtering and menu service

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

## Phase 4: Frontend 레이아웃 및 컴포넌트

### Task 8: 분할 레이아웃 컴포넌트 구조 설계

**Files:**
- Create: `frontend/src/components/Layout/SplitLayout.js`
- Create: `frontend/src/components/Layout/SplitLayout.css`
- Create: `frontend/src/components/Map/NaverMap.js`
- Create: `frontend/src/components/Map/NaverMap.css`

**Step 1: SplitLayout 컴포넌트 생성**

```jsx
// frontend/src/components/Layout/SplitLayout.js
import React, { useState } from 'react';
import './SplitLayout.css';

const SplitLayout = ({
    leftPanel,
    rightPanel,
    leftWidth = 400,
    detailPanel = null,
    showDetail = false
}) => {
    const [isMobile, setIsMobile] = useState(window.innerWidth < 768);

    React.useEffect(() => {
        const handleResize = () => {
            setIsMobile(window.innerWidth < 768);
        };
        window.addEventListener('resize', handleResize);
        return () => window.removeEventListener('resize', handleResize);
    }, []);

    if (isMobile) {
        return (
            <div className="mobile-layout">
                <div className="mobile-map">
                    {rightPanel}
                </div>
                <div className="mobile-bottom-sheet">
                    {showDetail ? detailPanel : leftPanel}
                </div>
            </div>
        );
    }

    return (
        <div className="split-layout">
            <div
                className={`left-panel ${showDetail ? 'expanded' : ''}`}
                style={{ width: showDetail ? '50%' : `${leftWidth}px` }}
            >
                {showDetail ? detailPanel : leftPanel}
            </div>
            <div className="right-panel">
                {rightPanel}
            </div>
        </div>
    );
};

export default SplitLayout;
```

**Step 2: SplitLayout CSS**

```css
/* frontend/src/components/Layout/SplitLayout.css */
.split-layout {
    display: flex;
    height: calc(100vh - 120px);
    overflow: hidden;
}

.left-panel {
    height: 100%;
    overflow-y: auto;
    background: #fff;
    border-right: 1px solid #e0e0e0;
    transition: width 0.3s ease;
}

.left-panel.expanded {
    width: 50% !important;
}

.right-panel {
    flex: 1;
    height: 100%;
}

/* Mobile */
.mobile-layout {
    display: flex;
    flex-direction: column;
    height: calc(100vh - 60px);
}

.mobile-map {
    flex: 1;
    min-height: 40%;
}

.mobile-bottom-sheet {
    background: #fff;
    border-radius: 16px 16px 0 0;
    box-shadow: 0 -4px 20px rgba(0, 0, 0, 0.1);
    max-height: 60%;
    overflow-y: auto;
    padding: 16px;
}

.mobile-bottom-sheet::before {
    content: '';
    display: block;
    width: 40px;
    height: 4px;
    background: #ddd;
    border-radius: 2px;
    margin: 0 auto 16px;
}
```

**Step 3: Commit**

```bash
git add frontend/src/components/Layout/
git commit -m "feat: add SplitLayout component for desktop and mobile

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

### Task 9: 네이버 지도 컴포넌트 구현

**Files:**
- Create: `frontend/src/components/Map/NaverMap.js`
- Create: `frontend/src/components/Map/NaverMap.css`
- Modify: `frontend/public/index.html` (네이버 지도 스크립트 추가)

**Step 1: index.html에 네이버 지도 스크립트 추가**

`frontend/public/index.html`의 `<head>` 안에 추가:
```html
<script type="text/javascript" src="https://oapi.map.naver.com/openapi/v3/maps.js?ncpClientId=YOUR_CLIENT_ID"></script>
```

**Step 2: NaverMap 컴포넌트**

```jsx
// frontend/src/components/Map/NaverMap.js
import React, { useEffect, useRef, useState } from 'react';
import './NaverMap.css';

const NaverMap = ({
    center,
    onCenterChange,
    markers = [],
    onMarkerClick,
    selectedMarkerId,
    showCenterPin = false
}) => {
    const mapRef = useRef(null);
    const mapInstanceRef = useRef(null);
    const markersRef = useRef([]);
    const [address, setAddress] = useState('');

    // 지도 초기화
    useEffect(() => {
        if (!window.naver || !mapRef.current) return;

        const mapOptions = {
            center: new window.naver.maps.LatLng(center.lat, center.lng),
            zoom: 15,
            zoomControl: true,
            zoomControlOptions: {
                position: window.naver.maps.Position.TOP_RIGHT
            }
        };

        mapInstanceRef.current = new window.naver.maps.Map(mapRef.current, mapOptions);

        // 지도 이동 이벤트
        window.naver.maps.Event.addListener(mapInstanceRef.current, 'idle', () => {
            const center = mapInstanceRef.current.getCenter();
            if (onCenterChange) {
                onCenterChange({
                    lat: center.lat(),
                    lng: center.lng()
                });
            }

            // Reverse geocoding
            if (showCenterPin) {
                reverseGeocode(center.lat(), center.lng());
            }
        });

        return () => {
            if (mapInstanceRef.current) {
                mapInstanceRef.current.destroy();
            }
        };
    }, []);

    // 중심 좌표 변경
    useEffect(() => {
        if (mapInstanceRef.current && center) {
            const newCenter = new window.naver.maps.LatLng(center.lat, center.lng);
            mapInstanceRef.current.setCenter(newCenter);
        }
    }, [center.lat, center.lng]);

    // 마커 업데이트
    useEffect(() => {
        if (!mapInstanceRef.current || !window.naver) return;

        // 기존 마커 제거
        markersRef.current.forEach(marker => marker.setMap(null));
        markersRef.current = [];

        // 새 마커 추가
        markers.forEach(markerData => {
            const marker = new window.naver.maps.Marker({
                position: new window.naver.maps.LatLng(markerData.lat, markerData.lng),
                map: mapInstanceRef.current,
                title: markerData.name,
                icon: {
                    content: `<div class="custom-marker ${selectedMarkerId === markerData.id ? 'selected' : ''}">
                        <span>${markerData.name.substring(0, 4)}</span>
                    </div>`,
                    anchor: new window.naver.maps.Point(20, 40)
                }
            });

            window.naver.maps.Event.addListener(marker, 'click', () => {
                if (onMarkerClick) {
                    onMarkerClick(markerData);
                }
            });

            markersRef.current.push(marker);
        });
    }, [markers, selectedMarkerId, onMarkerClick]);

    const reverseGeocode = async (lat, lng) => {
        try {
            const response = await fetch(`/api/geocode/reverse?lat=${lat}&lng=${lng}`);
            const data = await response.json();
            if (data.address) {
                setAddress(data.address);
            }
        } catch (error) {
            console.error('Reverse geocode failed:', error);
        }
    };

    return (
        <div className="naver-map-container">
            <div ref={mapRef} className="naver-map" />

            {showCenterPin && (
                <>
                    <div className="center-pin">📍</div>
                    <div className="center-address">
                        {address || '지도를 이동하여 위치를 선택하세요'}
                    </div>
                </>
            )}
        </div>
    );
};

export default NaverMap;
```

**Step 3: NaverMap CSS**

```css
/* frontend/src/components/Map/NaverMap.css */
.naver-map-container {
    width: 100%;
    height: 100%;
    position: relative;
}

.naver-map {
    width: 100%;
    height: 100%;
}

.center-pin {
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -100%);
    font-size: 32px;
    z-index: 100;
    pointer-events: none;
}

.center-address {
    position: absolute;
    bottom: 20px;
    left: 50%;
    transform: translateX(-50%);
    background: white;
    padding: 8px 16px;
    border-radius: 8px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.15);
    font-size: 14px;
    z-index: 100;
    max-width: 80%;
    text-align: center;
}

.custom-marker {
    background: #ff6b6b;
    color: white;
    padding: 4px 8px;
    border-radius: 4px;
    font-size: 11px;
    font-weight: bold;
    white-space: nowrap;
    box-shadow: 0 2px 4px rgba(0,0,0,0.2);
}

.custom-marker.selected {
    background: #4263eb;
    transform: scale(1.1);
}
```

**Step 4: Commit**

```bash
git add frontend/src/components/Map/ frontend/public/index.html
git commit -m "feat: add NaverMap component with markers and center pin

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

### Task 10: 업데이트된 FilterPanel (예산 슬라이더/프리셋/직접입력)

**Files:**
- Modify: `frontend/src/components/FilterPanel.js`
- Modify: `frontend/src/components/FilterPanel.css`

**Step 1: FilterPanel 재작성**

```jsx
// frontend/src/components/FilterPanel.js
import React, { useState } from 'react';
import './FilterPanel.css';

const FilterPanel = ({ filters, onFilterChange }) => {
    const [customBudget, setCustomBudget] = useState('');

    const categories = [
        '전체', '한식', '중식', '일식', '양식', '분식',
        '카페/디저트', '패스트푸드', '치킨', '피자',
        '아시안', '멕시칸', '샐러드/건강식', '술집/호프', '베이커리'
    ];

    const budgetPresets = [5000, 10000, 15000, 20000, 30000];

    const handleBudgetPreset = (value) => {
        onFilterChange('budget', value);
        setCustomBudget('');
    };

    const handleCustomBudget = () => {
        const value = parseInt(customBudget);
        if (value > 0) {
            onFilterChange('budget', value);
        }
    };

    const handleCategoryClick = (cat) => {
        if (cat === '전체') {
            onFilterChange('categories', []);
        } else {
            const newCategories = filters.categories.includes(cat)
                ? filters.categories.filter(c => c !== cat)
                : [...filters.categories, cat];
            onFilterChange('categories', newCategories);
        }
    };

    const formatPrice = (price) => {
        if (price >= 10000) {
            return `${price / 10000}만원`;
        }
        return `${price.toLocaleString()}원`;
    };

    return (
        <div className="filter-panel">
            {/* 반경 필터 */}
            <div className="filter-group">
                <label className="filter-label">
                    📍 검색 반경
                    <span className="filter-value">{(filters.radius / 1000).toFixed(1)}km</span>
                </label>
                <input
                    type="range"
                    min="100"
                    max="5000"
                    step="100"
                    value={filters.radius}
                    onChange={(e) => onFilterChange('radius', parseInt(e.target.value))}
                    className="range-slider"
                />
                <div className="range-labels">
                    <span>100m</span>
                    <span>5km</span>
                </div>
            </div>

            {/* 예산 필터 */}
            <div className="filter-group">
                <label className="filter-label">
                    💰 예산
                    {filters.budget && (
                        <span className="filter-value">{formatPrice(filters.budget)}</span>
                    )}
                </label>

                {/* 프리셋 버튼 */}
                <div className="budget-presets">
                    {budgetPresets.map(preset => (
                        <button
                            key={preset}
                            className={`preset-btn ${filters.budget === preset ? 'active' : ''}`}
                            onClick={() => handleBudgetPreset(preset)}
                        >
                            {formatPrice(preset)}
                        </button>
                    ))}
                </div>

                {/* 슬라이더 */}
                <input
                    type="range"
                    min="1000"
                    max="50000"
                    step="1000"
                    value={filters.budget || 15000}
                    onChange={(e) => onFilterChange('budget', parseInt(e.target.value))}
                    className="range-slider"
                />

                {/* 직접 입력 */}
                <div className="custom-budget">
                    <input
                        type="number"
                        placeholder="직접 입력"
                        value={customBudget}
                        onChange={(e) => setCustomBudget(e.target.value)}
                        onKeyPress={(e) => e.key === 'Enter' && handleCustomBudget()}
                    />
                    <button onClick={handleCustomBudget}>적용</button>
                </div>

                {/* 예산 기준 */}
                <div className="budget-type">
                    <label>
                        <input
                            type="radio"
                            name="budgetType"
                            checked={filters.budgetType === 'menu'}
                            onChange={() => onFilterChange('budgetType', 'menu')}
                        />
                        메뉴 기준
                    </label>
                    <label>
                        <input
                            type="radio"
                            name="budgetType"
                            checked={filters.budgetType === 'average'}
                            onChange={() => onFilterChange('budgetType', 'average')}
                        />
                        평균 기준
                    </label>
                </div>
            </div>

            {/* 카테고리 필터 */}
            <div className="filter-group">
                <label className="filter-label">🍽️ 카테고리</label>
                <div className="category-chips">
                    {categories.map(cat => (
                        <button
                            key={cat}
                            className={`chip ${
                                cat === '전체'
                                    ? filters.categories.length === 0 ? 'active' : ''
                                    : filters.categories.includes(cat) ? 'active' : ''
                            }`}
                            onClick={() => handleCategoryClick(cat)}
                        >
                            {cat}
                        </button>
                    ))}
                </div>
            </div>

            {/* 필터 초기화 */}
            <button
                className="reset-filters"
                onClick={() => {
                    onFilterChange('radius', 1000);
                    onFilterChange('budget', null);
                    onFilterChange('budgetType', 'menu');
                    onFilterChange('categories', []);
                }}
            >
                필터 초기화
            </button>
        </div>
    );
};

export default FilterPanel;
```

**Step 2: FilterPanel CSS 업데이트**

```css
/* frontend/src/components/FilterPanel.css */
.filter-panel {
    padding: 16px;
    background: #f8f9fa;
    border-radius: 8px;
    margin-bottom: 16px;
}

.filter-group {
    margin-bottom: 20px;
}

.filter-label {
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-weight: 600;
    margin-bottom: 8px;
    font-size: 14px;
}

.filter-value {
    color: #4263eb;
    font-weight: 700;
}

.range-slider {
    width: 100%;
    height: 6px;
    border-radius: 3px;
    background: #ddd;
    outline: none;
    -webkit-appearance: none;
}

.range-slider::-webkit-slider-thumb {
    -webkit-appearance: none;
    width: 18px;
    height: 18px;
    border-radius: 50%;
    background: #4263eb;
    cursor: pointer;
}

.range-labels {
    display: flex;
    justify-content: space-between;
    font-size: 12px;
    color: #888;
    margin-top: 4px;
}

.budget-presets {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
    margin-bottom: 12px;
}

.preset-btn {
    padding: 6px 12px;
    border: 1px solid #ddd;
    border-radius: 16px;
    background: white;
    font-size: 13px;
    cursor: pointer;
    transition: all 0.2s;
}

.preset-btn:hover {
    border-color: #4263eb;
}

.preset-btn.active {
    background: #4263eb;
    color: white;
    border-color: #4263eb;
}

.custom-budget {
    display: flex;
    gap: 8px;
    margin-top: 12px;
}

.custom-budget input {
    flex: 1;
    padding: 8px 12px;
    border: 1px solid #ddd;
    border-radius: 4px;
    font-size: 14px;
}

.custom-budget button {
    padding: 8px 16px;
    background: #4263eb;
    color: white;
    border: none;
    border-radius: 4px;
    cursor: pointer;
}

.budget-type {
    display: flex;
    gap: 16px;
    margin-top: 12px;
}

.budget-type label {
    display: flex;
    align-items: center;
    gap: 4px;
    font-size: 13px;
    cursor: pointer;
}

.category-chips {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
}

.chip {
    padding: 6px 12px;
    border: 1px solid #ddd;
    border-radius: 16px;
    background: white;
    font-size: 13px;
    cursor: pointer;
    transition: all 0.2s;
}

.chip:hover {
    border-color: #4263eb;
}

.chip.active {
    background: #4263eb;
    color: white;
    border-color: #4263eb;
}

.reset-filters {
    width: 100%;
    padding: 10px;
    background: transparent;
    border: 1px solid #ddd;
    border-radius: 4px;
    color: #666;
    cursor: pointer;
    font-size: 13px;
}

.reset-filters:hover {
    background: #f0f0f0;
}
```

**Step 3: Commit**

```bash
git add frontend/src/components/FilterPanel.js frontend/src/components/FilterPanel.css
git commit -m "feat: update FilterPanel with budget slider, presets, and direct input

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

### Task 11: RestaurantCard 컴포넌트 구현

**Files:**
- Create: `frontend/src/components/Restaurant/RestaurantCard.js`
- Create: `frontend/src/components/Restaurant/RestaurantCard.css`

**Step 1: RestaurantCard 컴포넌트**

```jsx
// frontend/src/components/Restaurant/RestaurantCard.js
import React from 'react';
import './RestaurantCard.css';

const RestaurantCard = ({ restaurant, onDetailClick, isSelected }) => {
    const formatDistance = (meters) => {
        if (meters >= 1000) {
            return `${(meters / 1000).toFixed(1)}km`;
        }
        return `${meters}m`;
    };

    const formatPrice = (price) => {
        if (!price) return '가격 미정';
        return `${price.toLocaleString()}원`;
    };

    return (
        <div className={`restaurant-card ${isSelected ? 'selected' : ''}`}>
            <div className="card-header">
                <h3 className="restaurant-name">{restaurant.name}</h3>
                {restaurant.rating && (
                    <span className="rating">⭐ {restaurant.rating.toFixed(1)}</span>
                )}
            </div>

            <div className="card-meta">
                <span className="category">{restaurant.category}</span>
                <span className="separator">·</span>
                <span className="distance">{formatDistance(restaurant.distance)}</span>
            </div>

            {restaurant.representative_menus && restaurant.representative_menus.length > 0 && (
                <div className="menu-preview">
                    {restaurant.representative_menus.map((menu, idx) => (
                        <div key={idx} className="menu-item">
                            <span className="menu-name">{menu.name}</span>
                            <span className="menu-price">{formatPrice(menu.price)}</span>
                        </div>
                    ))}
                </div>
            )}

            <button
                className="detail-btn"
                onClick={() => onDetailClick(restaurant)}
            >
                상세보기
            </button>
        </div>
    );
};

export default RestaurantCard;
```

**Step 2: RestaurantCard CSS**

```css
/* frontend/src/components/Restaurant/RestaurantCard.css */
.restaurant-card {
    background: white;
    border-radius: 8px;
    padding: 16px;
    margin-bottom: 12px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    transition: all 0.2s;
    cursor: pointer;
}

.restaurant-card:hover {
    box-shadow: 0 4px 12px rgba(0,0,0,0.15);
}

.restaurant-card.selected {
    border: 2px solid #4263eb;
}

.card-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 8px;
}

.restaurant-name {
    font-size: 16px;
    font-weight: 600;
    margin: 0;
    flex: 1;
}

.rating {
    font-size: 14px;
    color: #f59f00;
    font-weight: 500;
}

.card-meta {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 13px;
    color: #666;
    margin-bottom: 12px;
}

.separator {
    color: #ddd;
}

.menu-preview {
    background: #f8f9fa;
    border-radius: 6px;
    padding: 10px;
    margin-bottom: 12px;
}

.menu-item {
    display: flex;
    justify-content: space-between;
    font-size: 13px;
    padding: 4px 0;
}

.menu-item:not(:last-child) {
    border-bottom: 1px solid #eee;
}

.menu-name {
    color: #333;
}

.menu-price {
    color: #4263eb;
    font-weight: 500;
}

.detail-btn {
    width: 100%;
    padding: 10px;
    background: #f8f9fa;
    border: none;
    border-radius: 6px;
    color: #333;
    font-size: 14px;
    cursor: pointer;
    transition: background 0.2s;
}

.detail-btn:hover {
    background: #e9ecef;
}
```

**Step 3: Commit**

```bash
git add frontend/src/components/Restaurant/
git commit -m "feat: add RestaurantCard component with menu preview

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

### Task 12: RestaurantDetail 사이드 패널 구현

**Files:**
- Create: `frontend/src/components/Restaurant/RestaurantDetail.js`
- Create: `frontend/src/components/Restaurant/RestaurantDetail.css`

**Step 1: RestaurantDetail 컴포넌트**

```jsx
// frontend/src/components/Restaurant/RestaurantDetail.js
import React, { useState, useEffect } from 'react';
import { getRestaurantMenus, contributeMenu } from '../../services/api';
import './RestaurantDetail.css';

const RestaurantDetail = ({ restaurant, onClose }) => {
    const [menus, setMenus] = useState([]);
    const [loading, setLoading] = useState(true);
    const [showContribute, setShowContribute] = useState(false);
    const [newMenu, setNewMenu] = useState({ name: '', price: '' });

    useEffect(() => {
        loadMenus();
    }, [restaurant.place_id]);

    const loadMenus = async () => {
        setLoading(true);
        try {
            const data = await getRestaurantMenus(restaurant.place_id);
            setMenus(data.menus || []);
        } catch (error) {
            console.error('Failed to load menus:', error);
        } finally {
            setLoading(false);
        }
    };

    const handleContribute = async () => {
        if (!newMenu.name) return;

        try {
            await contributeMenu(restaurant.place_id, {
                menu_name: newMenu.name,
                price: newMenu.price ? parseInt(newMenu.price) : null
            });
            setNewMenu({ name: '', price: '' });
            setShowContribute(false);
            loadMenus();
        } catch (error) {
            console.error('Failed to contribute menu:', error);
        }
    };

    const formatPrice = (price) => {
        if (!price) return '가격 미정';
        return `${price.toLocaleString()}원`;
    };

    return (
        <div className="restaurant-detail">
            <div className="detail-header">
                <button className="back-btn" onClick={onClose}>
                    ← 뒤로
                </button>
                <h2>{restaurant.name}</h2>
            </div>

            <div className="detail-info">
                <div className="info-row">
                    <span className="category">{restaurant.category}</span>
                    <span className="separator">·</span>
                    <span className="distance">{restaurant.distance}m</span>
                    {restaurant.rating && (
                        <>
                            <span className="separator">·</span>
                            <span className="rating">⭐ {restaurant.rating}</span>
                        </>
                    )}
                </div>

                {restaurant.address && (
                    <p className="address">📍 {restaurant.road_address || restaurant.address}</p>
                )}

                {restaurant.phone && (
                    <p className="phone">📞 {restaurant.phone}</p>
                )}
            </div>

            <div className="menu-section">
                <div className="menu-header">
                    <h3>메뉴</h3>
                    <button
                        className="add-menu-btn"
                        onClick={() => setShowContribute(!showContribute)}
                    >
                        + 메뉴 추가
                    </button>
                </div>

                {showContribute && (
                    <div className="contribute-form">
                        <input
                            type="text"
                            placeholder="메뉴명"
                            value={newMenu.name}
                            onChange={(e) => setNewMenu({...newMenu, name: e.target.value})}
                        />
                        <input
                            type="number"
                            placeholder="가격 (원)"
                            value={newMenu.price}
                            onChange={(e) => setNewMenu({...newMenu, price: e.target.value})}
                        />
                        <button onClick={handleContribute}>추가</button>
                    </div>
                )}

                {loading ? (
                    <p className="loading">메뉴 정보를 불러오는 중...</p>
                ) : menus.length > 0 ? (
                    <div className="menu-list">
                        {menus.map((menu, idx) => (
                            <div key={idx} className="menu-row">
                                <span className="menu-name">
                                    {menu.is_representative && '⭐ '}
                                    {menu.name}
                                </span>
                                <span className="menu-price">{formatPrice(menu.price)}</span>
                            </div>
                        ))}
                    </div>
                ) : (
                    <p className="no-menus">
                        메뉴 정보가 없습니다.
                        <br />
                        메뉴를 추가해주세요!
                    </p>
                )}
            </div>
        </div>
    );
};

export default RestaurantDetail;
```

**Step 2: RestaurantDetail CSS**

```css
/* frontend/src/components/Restaurant/RestaurantDetail.css */
.restaurant-detail {
    padding: 16px;
    height: 100%;
    overflow-y: auto;
}

.detail-header {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 20px;
    padding-bottom: 16px;
    border-bottom: 1px solid #eee;
}

.back-btn {
    background: none;
    border: none;
    font-size: 16px;
    cursor: pointer;
    color: #666;
    padding: 4px 8px;
}

.back-btn:hover {
    color: #333;
}

.detail-header h2 {
    margin: 0;
    font-size: 20px;
}

.detail-info {
    margin-bottom: 24px;
}

.info-row {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 14px;
    color: #666;
    margin-bottom: 12px;
}

.info-row .separator {
    color: #ddd;
}

.info-row .rating {
    color: #f59f00;
}

.address, .phone {
    font-size: 14px;
    color: #333;
    margin: 8px 0;
}

.menu-section {
    background: #f8f9fa;
    border-radius: 8px;
    padding: 16px;
}

.menu-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 16px;
}

.menu-header h3 {
    margin: 0;
    font-size: 16px;
}

.add-menu-btn {
    background: #4263eb;
    color: white;
    border: none;
    padding: 6px 12px;
    border-radius: 4px;
    font-size: 13px;
    cursor: pointer;
}

.contribute-form {
    display: flex;
    gap: 8px;
    margin-bottom: 16px;
    padding-bottom: 16px;
    border-bottom: 1px solid #ddd;
}

.contribute-form input {
    flex: 1;
    padding: 8px;
    border: 1px solid #ddd;
    border-radius: 4px;
    font-size: 13px;
}

.contribute-form button {
    padding: 8px 16px;
    background: #4263eb;
    color: white;
    border: none;
    border-radius: 4px;
    cursor: pointer;
}

.menu-list {
    display: flex;
    flex-direction: column;
    gap: 8px;
}

.menu-row {
    display: flex;
    justify-content: space-between;
    padding: 10px;
    background: white;
    border-radius: 4px;
}

.menu-row .menu-name {
    font-size: 14px;
}

.menu-row .menu-price {
    font-size: 14px;
    color: #4263eb;
    font-weight: 500;
}

.loading, .no-menus {
    text-align: center;
    color: #888;
    font-size: 14px;
    padding: 20px;
}
```

**Step 3: Commit**

```bash
git add frontend/src/components/Restaurant/
git commit -m "feat: add RestaurantDetail component with menu list and user contribution

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

### Task 13: API 서비스 업데이트

**Files:**
- Modify: `frontend/src/services/api.js`

**Step 1: API 서비스에 새 엔드포인트 추가**

```javascript
// frontend/src/services/api.js
import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:5000/api';

const apiClient = axios.create({
    baseURL: API_BASE_URL,
    headers: {
        'Content-Type': 'application/json',
    },
});

export const searchRestaurants = async (params) => {
    try {
        const response = await apiClient.post('/restaurants/search', {
            lat: params.latitude || params.lat,
            lng: params.longitude || params.lng,
            radius: params.radius,
            budget: params.budget,
            budget_type: params.budgetType,
            categories: params.categories,
            query: params.query
        });
        return response.data;
    } catch (error) {
        console.error('검색 실패:', error);
        throw error;
    }
};

export const getRestaurantDetail = async (placeId) => {
    try {
        const response = await apiClient.get(`/restaurants/${placeId}`);
        return response.data;
    } catch (error) {
        console.error('상세 조회 실패:', error);
        throw error;
    }
};

export const getRestaurantMenus = async (placeId) => {
    try {
        const response = await apiClient.get(`/restaurants/${placeId}/menus`);
        return response.data;
    } catch (error) {
        console.error('메뉴 조회 실패:', error);
        throw error;
    }
};

export const contributeMenu = async (placeId, menuData) => {
    try {
        const response = await apiClient.post(`/restaurants/${placeId}/menus/contribute`, menuData);
        return response.data;
    } catch (error) {
        console.error('메뉴 추가 실패:', error);
        throw error;
    }
};

export const updateDeliveryInfo = async (placeId, deliveryData) => {
    try {
        const response = await apiClient.post(`/restaurants/${placeId}/delivery`, deliveryData);
        return response.data;
    } catch (error) {
        console.error('배달 정보 업데이트 실패:', error);
        throw error;
    }
};

export const reverseGeocode = async (lat, lng) => {
    try {
        const response = await apiClient.get('/geocode/reverse', {
            params: { lat, lng }
        });
        return response.data;
    } catch (error) {
        console.error('주소 변환 실패:', error);
        throw error;
    }
};

export const geocodeAddress = async (query) => {
    try {
        const response = await apiClient.get('/geocode', {
            params: { query }
        });
        return response.data;
    } catch (error) {
        console.error('주소 검색 실패:', error);
        throw error;
    }
};

export default apiClient;
```

**Step 2: Commit**

```bash
git add frontend/src/services/api.js
git commit -m "feat: update API service with new endpoints

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

### Task 14: App.js 통합 (새 레이아웃 적용)

**Files:**
- Modify: `frontend/src/App.js`
- Modify: `frontend/src/App.css`

**Step 1: App.js 재작성**

```jsx
// frontend/src/App.js
import React, { useState, useEffect } from 'react';
import './App.css';
import { searchRestaurants, reverseGeocode, geocodeAddress } from './services/api';
import SplitLayout from './components/Layout/SplitLayout';
import NaverMap from './components/Map/NaverMap';
import FilterPanel from './components/FilterPanel';
import RestaurantCard from './components/Restaurant/RestaurantCard';
import RestaurantDetail from './components/Restaurant/RestaurantDetail';

function App() {
    const [location, setLocation] = useState({ lat: 37.5665, lng: 126.978 });
    const [locationAddress, setLocationAddress] = useState('위치 정보를 가져오는 중...');
    const [isLocationMode, setIsLocationMode] = useState(false);
    const [searchQuery, setSearchQuery] = useState('');
    const [restaurants, setRestaurants] = useState([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [filters, setFilters] = useState({
        radius: 1000,
        categories: [],
        budget: null,
        budgetType: 'menu'
    });
    const [selectedRestaurant, setSelectedRestaurant] = useState(null);
    const [showDetail, setShowDetail] = useState(false);

    // 초기 위치 설정
    useEffect(() => {
        if (navigator.geolocation) {
            navigator.geolocation.getCurrentPosition(
                (position) => {
                    const coords = {
                        lat: position.coords.latitude,
                        lng: position.coords.longitude
                    };
                    setLocation(coords);
                    getAddressFromCoords(coords.lat, coords.lng);
                },
                (error) => {
                    console.error('위치 정보를 가져올 수 없습니다:', error);
                    setLocationAddress('서울특별시 중구 (기본 위치)');
                }
            );
        }
    }, []);

    const getAddressFromCoords = async (lat, lng) => {
        try {
            const data = await reverseGeocode(lat, lng);
            if (data?.address) {
                setLocationAddress(data.address);
            }
        } catch (error) {
            console.error('주소 변환 실패:', error);
        }
    };

    const handleFilterChange = (key, value) => {
        setFilters(prev => ({ ...prev, [key]: value }));
    };

    const handleSearch = async () => {
        setLoading(true);
        setError(null);

        try {
            const params = {
                lat: location.lat,
                lng: location.lng,
                radius: filters.radius,
                query: searchQuery || '음식점',
                budget: filters.budget,
                budgetType: filters.budgetType,
                categories: filters.categories
            };

            const data = await searchRestaurants(params);
            setRestaurants(data.results || []);
        } catch (err) {
            setError('검색에 실패했습니다.');
        } finally {
            setLoading(false);
        }
    };

    const handleMapCenterChange = (newCenter) => {
        if (isLocationMode) {
            setLocation(newCenter);
            getAddressFromCoords(newCenter.lat, newCenter.lng);
        }
    };

    const handleSetLocation = () => {
        setIsLocationMode(false);
        handleSearch();
    };

    const handleMarkerClick = (restaurant) => {
        setSelectedRestaurant(restaurant);
    };

    const handleDetailClick = (restaurant) => {
        setSelectedRestaurant(restaurant);
        setShowDetail(true);
    };

    const handleCloseDetail = () => {
        setShowDetail(false);
    };

    // 마커 데이터 생성
    const markers = restaurants.map(r => ({
        id: r.place_id,
        lat: r.latitude,
        lng: r.longitude,
        name: r.name
    })).filter(m => m.lat && m.lng);

    // 좌측 패널 (리스트)
    const leftPanel = (
        <div className="list-panel">
            <div className="search-section">
                <div className="location-display">
                    <span className="location-icon">📍</span>
                    <span className="location-text">{locationAddress}</span>
                    <button
                        className="location-btn"
                        onClick={() => setIsLocationMode(true)}
                    >
                        위치 변경
                    </button>
                </div>

                <div className="search-input-group">
                    <input
                        type="text"
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        placeholder="검색어 입력 (예: 한식, 파스타)"
                        className="search-input"
                        onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
                    />
                    <button
                        onClick={handleSearch}
                        className="search-button"
                        disabled={loading}
                    >
                        {loading ? '...' : '검색'}
                    </button>
                </div>
            </div>

            <FilterPanel filters={filters} onFilterChange={handleFilterChange} />

            {error && <div className="error-message">{error}</div>}

            <div className="results-section">
                <h3 className="results-title">
                    검색 결과 {restaurants.length}개
                    {filters.budget && ` · 예산 ${filters.budget.toLocaleString()}원 이하`}
                </h3>
                <div className="restaurant-list">
                    {restaurants.map((restaurant) => (
                        <RestaurantCard
                            key={restaurant.place_id}
                            restaurant={restaurant}
                            onDetailClick={handleDetailClick}
                            isSelected={selectedRestaurant?.place_id === restaurant.place_id}
                        />
                    ))}
                </div>
            </div>
        </div>
    );

    // 우측 패널 (지도)
    const rightPanel = (
        <div className="map-panel">
            <NaverMap
                center={location}
                onCenterChange={handleMapCenterChange}
                markers={markers}
                onMarkerClick={handleMarkerClick}
                selectedMarkerId={selectedRestaurant?.place_id}
                showCenterPin={isLocationMode}
            />

            {isLocationMode && (
                <div className="location-mode-controls">
                    <p>지도를 이동하여 원하는 위치를 선택하세요</p>
                    <button onClick={handleSetLocation}>이 위치로 검색</button>
                    <button onClick={() => setIsLocationMode(false)}>취소</button>
                </div>
            )}
        </div>
    );

    // 상세 패널
    const detailPanel = selectedRestaurant && (
        <RestaurantDetail
            restaurant={selectedRestaurant}
            onClose={handleCloseDetail}
        />
    );

    return (
        <div className="App">
            <header className="App-header">
                <h1>🍽️ FoodFinder</h1>
            </header>

            <SplitLayout
                leftPanel={leftPanel}
                rightPanel={rightPanel}
                detailPanel={detailPanel}
                showDetail={showDetail}
            />
        </div>
    );
}

export default App;
```

**Step 2: App.css 업데이트**

```css
/* frontend/src/App.css */
* {
    box-sizing: border-box;
    margin: 0;
    padding: 0;
}

.App {
    height: 100vh;
    display: flex;
    flex-direction: column;
}

.App-header {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    padding: 16px 24px;
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.App-header h1 {
    font-size: 24px;
    margin: 0;
}

/* List Panel */
.list-panel {
    height: 100%;
    overflow-y: auto;
    padding: 16px;
}

.search-section {
    margin-bottom: 16px;
}

.location-display {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 12px;
    font-size: 14px;
}

.location-icon {
    font-size: 18px;
}

.location-text {
    flex: 1;
    color: #333;
}

.location-btn {
    padding: 4px 12px;
    background: #f0f0f0;
    border: none;
    border-radius: 4px;
    font-size: 12px;
    cursor: pointer;
}

.search-input-group {
    display: flex;
    gap: 8px;
}

.search-input {
    flex: 1;
    padding: 12px 16px;
    border: 1px solid #ddd;
    border-radius: 8px;
    font-size: 14px;
}

.search-button {
    padding: 12px 24px;
    background: #4263eb;
    color: white;
    border: none;
    border-radius: 8px;
    font-size: 14px;
    cursor: pointer;
}

.search-button:disabled {
    background: #aaa;
}

.results-title {
    font-size: 14px;
    color: #666;
    margin-bottom: 12px;
}

.error-message {
    background: #ffe0e0;
    color: #c00;
    padding: 12px;
    border-radius: 8px;
    margin-bottom: 16px;
    font-size: 14px;
}

/* Map Panel */
.map-panel {
    height: 100%;
    position: relative;
}

.location-mode-controls {
    position: absolute;
    bottom: 80px;
    left: 50%;
    transform: translateX(-50%);
    background: white;
    padding: 16px 24px;
    border-radius: 12px;
    box-shadow: 0 4px 20px rgba(0,0,0,0.15);
    text-align: center;
    z-index: 100;
}

.location-mode-controls p {
    margin-bottom: 12px;
    font-size: 14px;
    color: #333;
}

.location-mode-controls button {
    margin: 0 4px;
    padding: 8px 16px;
    border: none;
    border-radius: 6px;
    cursor: pointer;
}

.location-mode-controls button:first-of-type {
    background: #4263eb;
    color: white;
}

.location-mode-controls button:last-of-type {
    background: #f0f0f0;
    color: #333;
}

/* Mobile */
@media (max-width: 768px) {
    .App-header {
        padding: 12px 16px;
    }

    .App-header h1 {
        font-size: 18px;
    }
}
```

**Step 3: Commit**

```bash
git add frontend/src/App.js frontend/src/App.css
git commit -m "feat: integrate new split layout with map and restaurant components

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

## Phase 5: 테스트 및 마무리

### Task 15: Backend 단위 테스트 추가

**Files:**
- Create: `backend/tests/test_menu_service.py`

**Step 1: 메뉴 서비스 테스트**

```python
# backend/tests/test_menu_service.py
import pytest
from app import create_app
from database import db
from models.restaurant import Restaurant
from models.menu import Menu


@pytest.fixture
def app():
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'

    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def test_search_restaurants_basic(client, app):
    """기본 검색 테스트"""
    with app.app_context():
        response = client.post('/api/restaurants/search', json={
            'lat': 37.5665,
            'lng': 126.9780,
            'radius': 1000,
            'query': '음식점'
        })

        assert response.status_code == 200
        data = response.get_json()
        assert 'results' in data
        assert 'total' in data


def test_search_with_budget_filter(client, app):
    """예산 필터 테스트"""
    with app.app_context():
        response = client.post('/api/restaurants/search', json={
            'lat': 37.5665,
            'lng': 126.9780,
            'radius': 1000,
            'query': '음식점',
            'budget': 10000,
            'budget_type': 'menu'
        })

        assert response.status_code == 200
        data = response.get_json()
        assert data['filters_applied']['budget'] == 10000


def test_contribute_menu(client, app):
    """사용자 메뉴 기여 테스트"""
    with app.app_context():
        # 먼저 음식점 생성
        restaurant = Restaurant(
            place_id='test_place_123',
            name='테스트 음식점',
            latitude=37.5665,
            longitude=126.9780
        )
        db.session.add(restaurant)
        db.session.commit()

        # 메뉴 기여
        response = client.post('/api/restaurants/test_place_123/menus/contribute', json={
            'menu_name': '김치찌개',
            'price': 8000
        })

        assert response.status_code == 201
        data = response.get_json()
        assert data['name'] == '김치찌개'
        assert data['price'] == 8000
        assert data['source'] == 'user'
```

**Step 2: Commit**

```bash
git add backend/tests/
git commit -m "test: add menu service unit tests

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

### Task 16: 환경 설정 파일 업데이트

**Files:**
- Modify: `backend/.env.example`
- Modify: `frontend/.env.example` (생성)

**Step 1: Backend .env.example 업데이트**

```bash
# backend/.env.example
SECRET_KEY=your-secret-key-here
NAVER_CLIENT_ID=your-naver-client-id
NAVER_CLIENT_SECRET=your-naver-client-secret
NAVER_CLOUD_ID=your-cloud-client-id
NAVER_CLOUD_SECRET=your-cloud-client-secret
KAKAO_API_KEY=your-kakao-rest-api-key
DATABASE_URL=sqlite:///foodfinder.db
```

**Step 2: Frontend .env.example 생성**

```bash
# frontend/.env.example
REACT_APP_API_URL=http://localhost:5000/api
REACT_APP_NAVER_MAP_CLIENT_ID=your-naver-map-client-id
```

**Step 3: Commit**

```bash
git add backend/.env.example frontend/.env.example
git commit -m "chore: update environment configuration examples

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

### Task 17: 최종 통합 테스트 및 README 업데이트

**Step 1: 서버 실행 테스트**

```bash
cd backend
pip install -r requirements.txt
python -c "from app import create_app; from database import db; app = create_app(); app.app_context().push(); db.create_all()"
```

**Step 2: 프론트엔드 빌드 테스트**

```bash
cd frontend
npm install
npm run build
```

**Step 3: Commit**

```bash
git add .
git commit -m "chore: final integration and build verification

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

## 구현 체크리스트

- [ ] Task 1: Menu 모델 추가
- [ ] Task 2: UserMenuContribution 모델 추가
- [ ] Task 3: 네이버 플레이스 크롤러 구현
- [ ] Task 4: 배달앱 크롤러 구현
- [ ] Task 5: 카카오맵 API 클라이언트 구현
- [ ] Task 6: 메뉴 서비스 (하이브리드 캐싱) 구현
- [ ] Task 7: Restaurant API 업데이트
- [ ] Task 8: 분할 레이아웃 컴포넌트 구조
- [ ] Task 9: 네이버 지도 컴포넌트 구현
- [ ] Task 10: 업데이트된 FilterPanel
- [ ] Task 11: RestaurantCard 컴포넌트
- [ ] Task 12: RestaurantDetail 사이드 패널
- [ ] Task 13: API 서비스 업데이트
- [ ] Task 14: App.js 통합
- [ ] Task 15: Backend 단위 테스트
- [ ] Task 16: 환경 설정 파일 업데이트
- [ ] Task 17: 최종 통합 테스트
