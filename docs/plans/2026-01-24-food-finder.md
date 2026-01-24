# 맛집 추천 프로그램 (FoodFinder) 구현 계획

> **Claude를 위한 안내:** REQUIRED SUB-SKILL: superpowers:executing-plans를 사용하여 이 계획을 단계별로 구현하세요.

**목표:** 네이버 지도 API를 활용하여 위치 기반으로 사용자 맞춤형 맛집을 추천하는 웹 애플리케이션 개발

**아키텍처:** Flask 기반 RESTful API 백엔드와 React 프론트엔드로 구성. SQLite 데이터베이스로 사용자 설정 및 배달 정보 저장. 네이버 지도 API로 실시간 맛집 데이터 조회.

**기술 스택:**
- 백엔드: Python 3.9+, Flask, SQLAlchemy, requests
- 프론트엔드: React 18, Axios, Naver Maps JavaScript API
- 데이터베이스: SQLite
- API: 네이버 지도 API, 네이버 플레이스 검색 API

---

## Task 1: 프로젝트 초기 설정

**파일:**
- Create: `backend/requirements.txt`
- Create: `backend/config.py`
- Create: `backend/.env.example`
- Create: `backend/.gitignore`
- Create: `.gitignore`

**Step 1: 백엔드 requirements.txt 작성**

```txt
Flask==3.0.0
Flask-CORS==4.0.0
SQLAlchemy==2.0.23
python-dotenv==1.0.0
requests==2.31.0
pytest==7.4.3
pytest-flask==1.3.0
```

**Step 2: 환경 설정 파일 작성**

`backend/config.py`:
```python
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """기본 설정"""
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key')
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'sqlite:///foodfinder.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # 네이버 API 설정
    NAVER_CLIENT_ID = os.getenv('NAVER_CLIENT_ID')
    NAVER_CLIENT_SECRET = os.getenv('NAVER_CLIENT_SECRET')

    # 검색 기본값
    DEFAULT_SEARCH_RADIUS = 1000  # 미터
    MAX_SEARCH_RADIUS = 5000
```

**Step 3: .env.example 파일 작성**

`backend/.env.example`:
```
SECRET_KEY=your-secret-key-here
NAVER_CLIENT_ID=your-naver-client-id
NAVER_CLIENT_SECRET=your-naver-client-secret
DATABASE_URL=sqlite:///foodfinder.db
```

**Step 4: .gitignore 파일 작성**

루트 `.gitignore`:
```
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
*.egg-info/

# 환경 변수
.env

# 데이터베이스
*.db
*.sqlite

# IDE
.vscode/
.idea/
*.swp

# Node
node_modules/
npm-debug.log
yarn-error.log

# Build
build/
dist/
```

**Step 5: 디렉토리 구조 생성**

```bash
cd FoodFinder
mkdir -p backend/api backend/models backend/tests
mkdir -p frontend/src/components frontend/src/services
touch backend/__init__.py backend/api/__init__.py backend/models/__init__.py
```

**Step 6: 가상 환경 생성 및 패키지 설치**

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

**Step 7: Git 초기화 및 첫 커밋**

```bash
cd ..
git init
git add .
git commit -m "chore: 프로젝트 초기 설정 및 환경 구성"
```

---

## Task 2: 데이터베이스 모델 설계 (TDD)

**파일:**
- Create: `backend/models/restaurant.py`
- Create: `backend/models/user_preference.py`
- Create: `backend/database.py`
- Create: `backend/tests/test_models.py`

**Step 1: 테스트 작성 - Restaurant 모델**

`backend/tests/test_models.py`:
```python
import pytest
from backend.database import db, init_db
from backend.models.restaurant import Restaurant
from flask import Flask


@pytest.fixture
def app():
    """테스트용 Flask 앱 생성"""
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['TESTING'] = True
    init_db(app)

    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def test_restaurant_creation(app):
    """Restaurant 모델 생성 테스트"""
    with app.app_context():
        restaurant = Restaurant(
            place_id='12345',
            name='맛있는 식당',
            category='한식',
            address='서울시 강남구',
            latitude=37.5665,
            longitude=126.9780,
            phone='02-1234-5678',
            rating=4.5
        )
        db.session.add(restaurant)
        db.session.commit()

        found = Restaurant.query.filter_by(place_id='12345').first()
        assert found is not None
        assert found.name == '맛있는 식당'
        assert found.category == '한식'
        assert found.rating == 4.5


def test_restaurant_to_dict(app):
    """Restaurant to_dict 메서드 테스트"""
    with app.app_context():
        restaurant = Restaurant(
            place_id='12345',
            name='맛있는 식당',
            category='한식',
            address='서울시 강남구',
            latitude=37.5665,
            longitude=126.9780
        )

        result = restaurant.to_dict()
        assert result['place_id'] == '12345'
        assert result['name'] == '맛있는 식당'
        assert 'latitude' in result
        assert 'longitude' in result
```

**Step 2: 테스트 실행 - 실패 확인**

```bash
cd backend
pytest tests/test_models.py::test_restaurant_creation -v
```
예상 결과: FAIL - "ModuleNotFoundError: No module named 'backend.models.restaurant'"

**Step 3: database.py 구현**

`backend/database.py`:
```python
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

def init_db(app):
    """데이터베이스 초기화"""
    db.init_app(app)
    return db
```

**Step 4: Restaurant 모델 구현**

`backend/models/restaurant.py`:
```python
from datetime import datetime
from backend.database import db


class Restaurant(db.Model):
    """음식점 정보 모델"""
    __tablename__ = 'restaurants'

    id = db.Column(db.Integer, primary_key=True)
    place_id = db.Column(db.String(100), unique=True, nullable=False, index=True)
    name = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(50))
    address = db.Column(db.String(300))
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    phone = db.Column(db.String(20))
    rating = db.Column(db.Float)

    # 배달 정보 (사용자 입력)
    delivery_available = db.Column(db.Boolean, default=False)
    delivery_fee = db.Column(db.Integer)  # 원 단위
    minimum_order = db.Column(db.Integer)  # 원 단위

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        """딕셔너리로 변환"""
        return {
            'id': self.id,
            'place_id': self.place_id,
            'name': self.name,
            'category': self.category,
            'address': self.address,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'phone': self.phone,
            'rating': self.rating,
            'delivery_available': self.delivery_available,
            'delivery_fee': self.delivery_fee,
            'minimum_order': self.minimum_order,
        }

    def __repr__(self):
        return f'<Restaurant {self.name}>'
```

**Step 5: 테스트 실행 - 성공 확인**

```bash
pytest tests/test_models.py -v
```
예상 결과: PASS - 모든 테스트 통과

**Step 6: UserPreference 모델 테스트 작성**

`backend/tests/test_models.py`에 추가:
```python
from backend.models.user_preference import UserPreference


def test_user_preference_creation(app):
    """UserPreference 모델 생성 테스트"""
    with app.app_context():
        pref = UserPreference(
            session_id='test-session-123',
            favorite_categories=['한식', '일식'],
            max_distance=2000,
            max_price_per_person=20000,
            max_delivery_fee=3000
        )
        db.session.add(pref)
        db.session.commit()

        found = UserPreference.query.filter_by(session_id='test-session-123').first()
        assert found is not None
        assert '한식' in found.favorite_categories
        assert found.max_distance == 2000
```

**Step 7: 테스트 실행 - 실패 확인**

```bash
pytest tests/test_models.py::test_user_preference_creation -v
```
예상 결과: FAIL

**Step 8: UserPreference 모델 구현**

`backend/models/user_preference.py`:
```python
from datetime import datetime
from backend.database import db
import json


class UserPreference(db.Model):
    """사용자 선호도 설정 모델"""
    __tablename__ = 'user_preferences'

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(100), unique=True, nullable=False, index=True)

    # 선호 카테고리 (JSON 배열로 저장)
    _favorite_categories = db.Column('favorite_categories', db.Text)

    # 검색 필터
    max_distance = db.Column(db.Integer, default=1000)  # 미터
    max_price_per_person = db.Column(db.Integer)  # 원
    max_delivery_fee = db.Column(db.Integer)  # 원

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @property
    def favorite_categories(self):
        """카테고리 리스트 반환"""
        if self._favorite_categories:
            return json.loads(self._favorite_categories)
        return []

    @favorite_categories.setter
    def favorite_categories(self, value):
        """카테고리 리스트 저장"""
        self._favorite_categories = json.dumps(value, ensure_ascii=False)

    def to_dict(self):
        """딕셔너리로 변환"""
        return {
            'session_id': self.session_id,
            'favorite_categories': self.favorite_categories,
            'max_distance': self.max_distance,
            'max_price_per_person': self.max_price_per_person,
            'max_delivery_fee': self.max_delivery_fee,
        }
```

**Step 9: 테스트 실행 - 성공 확인**

```bash
pytest tests/test_models.py -v
```
예상 결과: PASS

**Step 10: 커밋**

```bash
git add backend/models/ backend/database.py backend/tests/test_models.py
git commit -m "feat: Restaurant 및 UserPreference 데이터베이스 모델 구현"
```

---

## Task 3: 네이버 지도 API 연동 (TDD)

**파일:**
- Create: `backend/api/naver_map.py`
- Create: `backend/tests/test_naver_map.py`

**Step 1: 네이버 API 클라이언트 테스트 작성**

`backend/tests/test_naver_map.py`:
```python
import pytest
from unittest.mock import patch, Mock
from backend.api.naver_map import NaverMapClient


@pytest.fixture
def naver_client():
    """네이버 클라이언트 픽스처"""
    return NaverMapClient(
        client_id='test-client-id',
        client_secret='test-client-secret'
    )


def test_search_local_success(naver_client):
    """장소 검색 성공 테스트"""
    mock_response = {
        'items': [
            {
                'title': '맛있는 <b>한식</b>집',
                'category': '한식>일반한식',
                'address': '서울특별시 강남구',
                'roadAddress': '서울특별시 강남구 테헤란로 123',
                'mapx': '1269780',
                'mapy': '375665',
                'telephone': '02-1234-5678'
            }
        ]
    }

    with patch('requests.get') as mock_get:
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = mock_response

        results = naver_client.search_local('한식', latitude=37.5665, longitude=126.9780)

        assert len(results) == 1
        assert '한식' in results[0]['title']
        assert results[0]['latitude'] == 37.5665
        assert results[0]['longitude'] == 126.9780


def test_search_local_api_error(naver_client):
    """API 에러 처리 테스트"""
    with patch('requests.get') as mock_get:
        mock_get.return_value.status_code = 401

        results = naver_client.search_local('한식')
        assert results == []
```

**Step 2: 테스트 실행 - 실패 확인**

```bash
pytest tests/test_naver_map.py::test_search_local_success -v
```
예상 결과: FAIL - "ModuleNotFoundError"

**Step 3: NaverMapClient 구현**

`backend/api/naver_map.py`:
```python
import requests
from typing import List, Dict, Optional
import re


class NaverMapClient:
    """네이버 지도 API 클라이언트"""

    BASE_URL = 'https://openapi.naver.com/v1/search/local.json'

    def __init__(self, client_id: str, client_secret: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.headers = {
            'X-Naver-Client-Id': client_id,
            'X-Naver-Client-Secret': client_secret
        }

    def search_local(
        self,
        query: str,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        radius: int = 1000,
        display: int = 20
    ) -> List[Dict]:
        """
        네이버 지역 검색 API 호출

        Args:
            query: 검색어 (예: '한식', '카페')
            latitude: 중심 위도
            longitude: 중심 경도
            radius: 검색 반경 (미터)
            display: 결과 개수 (최대 20)

        Returns:
            검색 결과 리스트
        """
        params = {
            'query': query,
            'display': min(display, 20),
            'sort': 'random'
        }

        try:
            response = requests.get(
                self.BASE_URL,
                headers=self.headers,
                params=params,
                timeout=10
            )

            if response.status_code != 200:
                print(f"API 에러: {response.status_code}")
                return []

            data = response.json()
            items = data.get('items', [])

            # 결과 정제
            results = []
            for item in items:
                results.append(self._parse_item(item))

            # 위치 기반 필터링 (선택사항)
            if latitude and longitude:
                results = self._filter_by_distance(
                    results, latitude, longitude, radius
                )

            return results

        except requests.exceptions.RequestException as e:
            print(f"네트워크 에러: {e}")
            return []

    def _parse_item(self, item: Dict) -> Dict:
        """API 응답 아이템 파싱"""
        # HTML 태그 제거
        title = re.sub(r'<[^>]+>', '', item.get('title', ''))

        # 좌표 변환 (네이버는 KATEC 좌표계 사용)
        mapx = item.get('mapx', '0')
        mapy = item.get('mapy', '0')

        # KATEC to WGS84 간단 변환 (정확도 낮음, 실제론 라이브러리 사용 권장)
        longitude = float(mapx) / 10000000
        latitude = float(mapy) / 10000000

        # 카테고리 추출 (첫 번째 항목만)
        category_full = item.get('category', '')
        category = category_full.split('>')[0] if category_full else ''

        return {
            'title': title,
            'category': category,
            'address': item.get('address', ''),
            'road_address': item.get('roadAddress', ''),
            'latitude': latitude,
            'longitude': longitude,
            'telephone': item.get('telephone', ''),
            'link': item.get('link', '')
        }

    def _filter_by_distance(
        self,
        results: List[Dict],
        lat: float,
        lon: float,
        radius: int
    ) -> List[Dict]:
        """거리 기반 필터링 (간단한 유클리드 거리 사용)"""
        # 실제로는 Haversine 공식 사용 권장
        filtered = []
        for result in results:
            # 간단한 거리 계산 (1도 ≈ 111km)
            lat_diff = abs(result['latitude'] - lat) * 111000
            lon_diff = abs(result['longitude'] - lon) * 88000  # 한국 위도 기준
            distance = (lat_diff ** 2 + lon_diff ** 2) ** 0.5

            if distance <= radius:
                result['distance'] = int(distance)
                filtered.append(result)

        return sorted(filtered, key=lambda x: x.get('distance', 0))
```

**Step 4: 테스트 실행 - 성공 확인**

```bash
pytest tests/test_naver_map.py -v
```
예상 결과: PASS

**Step 5: 커밋**

```bash
git add backend/api/naver_map.py backend/tests/test_naver_map.py
git commit -m "feat: 네이버 지도 API 클라이언트 구현"
```

---

## Task 4: Flask 애플리케이션 및 REST API 구현 (TDD)

**파일:**
- Create: `backend/app.py`
- Create: `backend/api/restaurant.py`
- Create: `backend/tests/test_api.py`

**Step 1: API 엔드포인트 테스트 작성**

`backend/tests/test_api.py`:
```python
import pytest
import json
from backend.app import create_app
from backend.database import db


@pytest.fixture
def app():
    """테스트용 Flask 앱"""
    app = create_app({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'NAVER_CLIENT_ID': 'test-id',
        'NAVER_CLIENT_SECRET': 'test-secret'
    })

    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def test_health_check(client):
    """헬스 체크 엔드포인트 테스트"""
    response = client.get('/api/health')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['status'] == 'ok'


def test_search_restaurants(client):
    """맛집 검색 엔드포인트 테스트"""
    response = client.post('/api/restaurants/search', json={
        'query': '한식',
        'latitude': 37.5665,
        'longitude': 126.9780,
        'radius': 1000
    })

    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'results' in data
    assert isinstance(data['results'], list)


def test_search_restaurants_missing_params(client):
    """필수 파라미터 누락 테스트"""
    response = client.post('/api/restaurants/search', json={
        'query': '한식'
    })

    assert response.status_code == 400
```

**Step 2: 테스트 실행 - 실패 확인**

```bash
pytest tests/test_api.py::test_health_check -v
```
예상 결과: FAIL

**Step 3: Flask 앱 팩토리 구현**

`backend/app.py`:
```python
from flask import Flask
from flask_cors import CORS
from backend.database import db, init_db
from backend.config import Config


def create_app(config_override=None):
    """Flask 애플리케이션 팩토리"""
    app = Flask(__name__)

    # 설정 로드
    app.config.from_object(Config)
    if config_override:
        app.config.update(config_override)

    # CORS 설정
    CORS(app)

    # 데이터베이스 초기화
    init_db(app)

    # 블루프린트 등록
    from backend.api.restaurant import restaurant_bp
    app.register_blueprint(restaurant_bp, url_prefix='/api')

    # 헬스 체크
    @app.route('/api/health')
    def health():
        return {'status': 'ok'}, 200

    return app


if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        db.create_all()
    app.run(debug=True, host='0.0.0.0', port=5000)
```

**Step 4: Restaurant API 블루프린트 구현**

`backend/api/restaurant.py`:
```python
from flask import Blueprint, request, jsonify
from backend.api.naver_map import NaverMapClient
from backend.database import db
from backend.models.restaurant import Restaurant
from backend.config import Config

restaurant_bp = Blueprint('restaurant', __name__)


@restaurant_bp.route('/restaurants/search', methods=['POST'])
def search_restaurants():
    """
    맛집 검색 API

    Request Body:
        - query: 검색어 (필수)
        - latitude: 위도 (필수)
        - longitude: 경도 (필수)
        - radius: 검색 반경 (선택, 기본 1000m)
        - categories: 카테고리 필터 (선택)
        - max_price: 최대 가격 (선택)
    """
    data = request.get_json()

    # 필수 파라미터 검증
    if not data or 'query' not in data:
        return jsonify({'error': '검색어는 필수입니다'}), 400

    if 'latitude' not in data or 'longitude' not in data:
        return jsonify({'error': '위치 정보는 필수입니다'}), 400

    query = data['query']
    latitude = float(data['latitude'])
    longitude = float(data['longitude'])
    radius = data.get('radius', Config.DEFAULT_SEARCH_RADIUS)

    # 네이버 API 호출
    naver_client = NaverMapClient(
        Config.NAVER_CLIENT_ID,
        Config.NAVER_CLIENT_SECRET
    )

    results = naver_client.search_local(
        query=query,
        latitude=latitude,
        longitude=longitude,
        radius=radius
    )

    # 카테고리 필터 적용
    if 'categories' in data and data['categories']:
        categories = data['categories']
        results = [r for r in results if r['category'] in categories]

    return jsonify({
        'results': results,
        'count': len(results)
    }), 200


@restaurant_bp.route('/restaurants/<place_id>/delivery', methods=['POST'])
def update_delivery_info(place_id):
    """
    배달 정보 업데이트 (사용자 입력)

    Request Body:
        - delivery_fee: 배달비
        - minimum_order: 최소 주문 금액
    """
    data = request.get_json()

    restaurant = Restaurant.query.filter_by(place_id=place_id).first()

    if not restaurant:
        # 새로운 레스토랑 정보 생성
        restaurant = Restaurant(place_id=place_id)
        db.session.add(restaurant)

    # 배달 정보 업데이트
    if 'delivery_fee' in data:
        restaurant.delivery_fee = data['delivery_fee']
        restaurant.delivery_available = True

    if 'minimum_order' in data:
        restaurant.minimum_order = data['minimum_order']

    db.session.commit()

    return jsonify(restaurant.to_dict()), 200


@restaurant_bp.route('/restaurants/nearby', methods=['GET'])
def get_nearby_restaurants():
    """
    주변 맛집 조회 (배달비 필터 포함)

    Query Params:
        - lat: 위도
        - lon: 경도
        - max_delivery_fee: 최대 배달비
    """
    latitude = request.args.get('lat', type=float)
    longitude = request.args.get('lon', type=float)
    max_delivery_fee = request.args.get('max_delivery_fee', type=int)

    if not latitude or not longitude:
        return jsonify({'error': '위치 정보는 필수입니다'}), 400

    # 배달 가능한 레스토랑 조회
    query = Restaurant.query.filter_by(delivery_available=True)

    if max_delivery_fee:
        query = query.filter(Restaurant.delivery_fee <= max_delivery_fee)

    restaurants = query.all()

    # 거리 계산 및 정렬 (간단한 버전)
    results = []
    for r in restaurants:
        lat_diff = abs(r.latitude - latitude) * 111000
        lon_diff = abs(r.longitude - longitude) * 88000
        distance = (lat_diff ** 2 + lon_diff ** 2) ** 0.5

        if distance <= 3000:  # 3km 이내
            result = r.to_dict()
            result['distance'] = int(distance)
            results.append(result)

    results.sort(key=lambda x: x['distance'])

    return jsonify({
        'results': results,
        'count': len(results)
    }), 200
```

**Step 5: 테스트 실행 - 성공 확인**

```bash
pytest tests/test_api.py -v
```
예상 결과: PASS

**Step 6: 통합 테스트**

```bash
# 개발 서버 실행
cd backend
python app.py
```

다른 터미널에서:
```bash
# 헬스 체크
curl http://localhost:5000/api/health

# 검색 테스트 (실제 API 키 필요)
curl -X POST http://localhost:5000/api/restaurants/search \
  -H "Content-Type: application/json" \
  -d '{"query":"한식","latitude":37.5665,"longitude":126.9780,"radius":1000}'
```

**Step 7: 커밋**

```bash
git add backend/app.py backend/api/restaurant.py backend/tests/test_api.py
git commit -m "feat: Flask REST API 및 맛집 검색 엔드포인트 구현"
```

---

## Task 5: React 프론트엔드 초기 설정

**파일:**
- Create: `frontend/package.json`
- Create: `frontend/src/App.js`
- Create: `frontend/src/services/api.js`
- Create: `frontend/public/index.html`

**Step 1: React 프로젝트 생성**

```bash
cd FoodFinder
npx create-react-app frontend
cd frontend
npm install axios react-naver-maps
```

**Step 2: API 서비스 레이어 작성**

`frontend/src/services/api.js`:
```javascript
import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:5000/api';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const searchRestaurants = async (params) => {
  /**
   * 맛집 검색
   * @param {Object} params - { query, latitude, longitude, radius, categories }
   */
  try {
    const response = await apiClient.post('/restaurants/search', params);
    return response.data;
  } catch (error) {
    console.error('검색 실패:', error);
    throw error;
  }
};

export const updateDeliveryInfo = async (placeId, deliveryData) => {
  /**
   * 배달 정보 업데이트
   * @param {string} placeId - 장소 ID
   * @param {Object} deliveryData - { delivery_fee, minimum_order }
   */
  try {
    const response = await apiClient.post(
      `/restaurants/${placeId}/delivery`,
      deliveryData
    );
    return response.data;
  } catch (error) {
    console.error('배달 정보 업데이트 실패:', error);
    throw error;
  }
};

export const getNearbyRestaurants = async (lat, lon, maxDeliveryFee) => {
  /**
   * 주변 맛집 조회
   */
  try {
    const params = { lat, lon };
    if (maxDeliveryFee) {
      params.max_delivery_fee = maxDeliveryFee;
    }

    const response = await apiClient.get('/restaurants/nearby', { params });
    return response.data;
  } catch (error) {
    console.error('주변 맛집 조회 실패:', error);
    throw error;
  }
};

export default apiClient;
```

**Step 3: 기본 App 컴포넌트 작성**

`frontend/src/App.js`:
```javascript
import React, { useState, useEffect } from 'react';
import './App.css';
import { searchRestaurants } from './services/api';

function App() {
  const [location, setLocation] = useState(null);
  const [searchQuery, setSearchQuery] = useState('한식');
  const [restaurants, setRestaurants] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // 현재 위치 가져오기
  useEffect(() => {
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        (position) => {
          setLocation({
            latitude: position.coords.latitude,
            longitude: position.coords.longitude,
          });
        },
        (error) => {
          console.error('위치 정보를 가져올 수 없습니다:', error);
          // 기본값 (서울 시청)
          setLocation({
            latitude: 37.5665,
            longitude: 126.9780,
          });
        }
      );
    }
  }, []);

  // 맛집 검색
  const handleSearch = async () => {
    if (!location) {
      alert('위치 정보를 불러오는 중입니다.');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const data = await searchRestaurants({
        query: searchQuery,
        latitude: location.latitude,
        longitude: location.longitude,
        radius: 1000,
      });

      setRestaurants(data.results || []);
    } catch (err) {
      setError('검색에 실패했습니다. 나중에 다시 시도해주세요.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="App">
      <header className="App-header">
        <h1>🍽️ FoodFinder - 맛집 추천</h1>
      </header>

      <main className="container">
        <div className="search-section">
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="음식 종류를 입력하세요 (예: 한식, 일식)"
            className="search-input"
          />
          <button onClick={handleSearch} className="search-button" disabled={loading}>
            {loading ? '검색 중...' : '검색'}
          </button>
        </div>

        {error && <div className="error-message">{error}</div>}

        <div className="results-section">
          {restaurants.length > 0 ? (
            <div className="restaurant-list">
              {restaurants.map((restaurant, index) => (
                <div key={index} className="restaurant-card">
                  <h3>{restaurant.title}</h3>
                  <p className="category">{restaurant.category}</p>
                  <p className="address">{restaurant.road_address || restaurant.address}</p>
                  {restaurant.distance && (
                    <p className="distance">거리: {restaurant.distance}m</p>
                  )}
                  {restaurant.telephone && (
                    <p className="phone">📞 {restaurant.telephone}</p>
                  )}
                </div>
              ))}
            </div>
          ) : (
            !loading && <p className="no-results">검색 결과가 없습니다.</p>
          )}
        </div>
      </main>
    </div>
  );
}

export default App;
```

**Step 4: 기본 스타일 작성**

`frontend/src/App.css`:
```css
.App {
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.App-header {
  padding: 2rem;
  text-align: center;
  color: white;
}

.App-header h1 {
  margin: 0;
  font-size: 2.5rem;
  text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.3);
}

.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 2rem;
}

.search-section {
  display: flex;
  gap: 1rem;
  margin-bottom: 2rem;
  background: white;
  padding: 1.5rem;
  border-radius: 12px;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}

.search-input {
  flex: 1;
  padding: 0.75rem 1rem;
  border: 2px solid #e0e0e0;
  border-radius: 8px;
  font-size: 1rem;
  transition: border-color 0.3s;
}

.search-input:focus {
  outline: none;
  border-color: #667eea;
}

.search-button {
  padding: 0.75rem 2rem;
  background: #667eea;
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 1rem;
  font-weight: bold;
  cursor: pointer;
  transition: background 0.3s;
}

.search-button:hover:not(:disabled) {
  background: #5568d3;
}

.search-button:disabled {
  background: #ccc;
  cursor: not-allowed;
}

.error-message {
  background: #fee;
  color: #c33;
  padding: 1rem;
  border-radius: 8px;
  margin-bottom: 1rem;
}

.restaurant-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 1.5rem;
}

.restaurant-card {
  background: white;
  padding: 1.5rem;
  border-radius: 12px;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
  transition: transform 0.3s, box-shadow 0.3s;
}

.restaurant-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 12px rgba(0, 0, 0, 0.15);
}

.restaurant-card h3 {
  margin: 0 0 0.5rem 0;
  color: #333;
  font-size: 1.25rem;
}

.category {
  display: inline-block;
  background: #667eea;
  color: white;
  padding: 0.25rem 0.75rem;
  border-radius: 20px;
  font-size: 0.875rem;
  margin-bottom: 0.5rem;
}

.address {
  color: #666;
  font-size: 0.875rem;
  margin: 0.5rem 0;
}

.distance {
  color: #667eea;
  font-weight: bold;
  margin: 0.5rem 0;
}

.phone {
  color: #444;
  margin: 0.5rem 0;
}

.no-results {
  text-align: center;
  color: white;
  font-size: 1.25rem;
  margin-top: 3rem;
}
```

**Step 5: 환경 변수 설정**

`frontend/.env`:
```
REACT_APP_API_URL=http://localhost:5000/api
REACT_APP_NAVER_MAP_CLIENT_ID=your-naver-map-client-id
```

**Step 6: 프론트엔드 실행 테스트**

```bash
cd frontend
npm start
```

브라우저에서 http://localhost:3000 접속하여 UI 확인

**Step 7: 커밋**

```bash
git add frontend/
git commit -m "feat: React 프론트엔드 초기 구현 및 검색 UI 추가"
```

---

## Task 6: 고급 필터링 기능 추가

**파일:**
- Modify: `frontend/src/App.js`
- Create: `frontend/src/components/FilterPanel.js`

**Step 1: FilterPanel 컴포넌트 작성**

`frontend/src/components/FilterPanel.js`:
```javascript
import React from 'react';
import './FilterPanel.css';

const FilterPanel = ({ filters, onFilterChange }) => {
  const categories = ['한식', '중식', '일식', '양식', '카페', '디저트', '치킨', '피자'];

  return (
    <div className="filter-panel">
      <h3>🔍 검색 필터</h3>

      <div className="filter-group">
        <label>검색 반경 (미터)</label>
        <input
          type="range"
          min="500"
          max="5000"
          step="500"
          value={filters.radius}
          onChange={(e) => onFilterChange('radius', parseInt(e.target.value))}
        />
        <span className="filter-value">{filters.radius}m</span>
      </div>

      <div className="filter-group">
        <label>음식 종류</label>
        <div className="category-chips">
          {categories.map((cat) => (
            <button
              key={cat}
              className={`chip ${filters.categories.includes(cat) ? 'active' : ''}`}
              onClick={() => {
                const newCategories = filters.categories.includes(cat)
                  ? filters.categories.filter((c) => c !== cat)
                  : [...filters.categories, cat];
                onFilterChange('categories', newCategories);
              }}
            >
              {cat}
            </button>
          ))}
        </div>
      </div>

      <div className="filter-group">
        <label>최대 배달비 (원)</label>
        <input
          type="number"
          min="0"
          step="500"
          value={filters.maxDeliveryFee || ''}
          onChange={(e) => onFilterChange('maxDeliveryFee', parseInt(e.target.value) || null)}
          placeholder="제한 없음"
        />
      </div>

      <div className="filter-group">
        <label>최대 거리 당 가격 (원/인)</label>
        <input
          type="number"
          min="0"
          step="1000"
          value={filters.maxPrice || ''}
          onChange={(e) => onFilterChange('maxPrice', parseInt(e.target.value) || null)}
          placeholder="제한 없음"
        />
      </div>
    </div>
  );
};

export default FilterPanel;
```

**Step 2: FilterPanel 스타일**

`frontend/src/components/FilterPanel.css`:
```css
.filter-panel {
  background: white;
  padding: 1.5rem;
  border-radius: 12px;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
  margin-bottom: 2rem;
}

.filter-panel h3 {
  margin: 0 0 1.5rem 0;
  color: #333;
}

.filter-group {
  margin-bottom: 1.5rem;
}

.filter-group label {
  display: block;
  margin-bottom: 0.5rem;
  color: #555;
  font-weight: 600;
}

.filter-group input[type="range"] {
  width: 100%;
  margin-right: 1rem;
}

.filter-value {
  color: #667eea;
  font-weight: bold;
}

.category-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.chip {
  padding: 0.5rem 1rem;
  border: 2px solid #e0e0e0;
  background: white;
  border-radius: 20px;
  cursor: pointer;
  transition: all 0.3s;
}

.chip:hover {
  border-color: #667eea;
}

.chip.active {
  background: #667eea;
  color: white;
  border-color: #667eea;
}

.filter-group input[type="number"] {
  width: 100%;
  padding: 0.5rem;
  border: 2px solid #e0e0e0;
  border-radius: 8px;
  font-size: 1rem;
}

.filter-group input[type="number"]:focus {
  outline: none;
  border-color: #667eea;
}
```

**Step 3: App.js에 필터 통합**

`frontend/src/App.js` 수정:
```javascript
import React, { useState, useEffect } from 'react';
import './App.css';
import { searchRestaurants } from './services/api';
import FilterPanel from './components/FilterPanel';

function App() {
  const [location, setLocation] = useState(null);
  const [searchQuery, setSearchQuery] = useState('음식점');
  const [restaurants, setRestaurants] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [filters, setFilters] = useState({
    radius: 1000,
    categories: [],
    maxDeliveryFee: null,
    maxPrice: null,
  });

  useEffect(() => {
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        (position) => {
          setLocation({
            latitude: position.coords.latitude,
            longitude: position.coords.longitude,
          });
        },
        (error) => {
          console.error('위치 정보를 가져올 수 없습니다:', error);
          setLocation({
            latitude: 37.5665,
            longitude: 126.9780,
          });
        }
      );
    }
  }, []);

  const handleFilterChange = (key, value) => {
    setFilters((prev) => ({ ...prev, [key]: value }));
  };

  const handleSearch = async () => {
    if (!location) {
      alert('위치 정보를 불러오는 중입니다.');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const params = {
        query: searchQuery,
        latitude: location.latitude,
        longitude: location.longitude,
        radius: filters.radius,
      };

      if (filters.categories.length > 0) {
        params.categories = filters.categories;
      }

      const data = await searchRestaurants(params);
      setRestaurants(data.results || []);
    } catch (err) {
      setError('검색에 실패했습니다. 나중에 다시 시도해주세요.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="App">
      <header className="App-header">
        <h1>🍽️ FoodFinder - 맛집 추천</h1>
        <p>위치 기반 맞춤형 맛집 찾기</p>
      </header>

      <main className="container">
        <div className="search-section">
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="음식 종류를 입력하세요"
            className="search-input"
          />
          <button onClick={handleSearch} className="search-button" disabled={loading}>
            {loading ? '검색 중...' : '검색'}
          </button>
        </div>

        <FilterPanel filters={filters} onFilterChange={handleFilterChange} />

        {error && <div className="error-message">{error}</div>}

        <div className="results-section">
          {restaurants.length > 0 ? (
            <>
              <h2>검색 결과 ({restaurants.length}개)</h2>
              <div className="restaurant-list">
                {restaurants.map((restaurant, index) => (
                  <div key={index} className="restaurant-card">
                    <h3>{restaurant.title}</h3>
                    <p className="category">{restaurant.category}</p>
                    <p className="address">
                      {restaurant.road_address || restaurant.address}
                    </p>
                    {restaurant.distance && (
                      <p className="distance">📍 {restaurant.distance}m</p>
                    )}
                    {restaurant.telephone && (
                      <p className="phone">📞 {restaurant.telephone}</p>
                    )}
                  </div>
                ))}
              </div>
            </>
          ) : (
            !loading && <p className="no-results">검색 결과가 없습니다.</p>
          )}
        </div>
      </main>
    </div>
  );
}

export default App;
```

**Step 4: 테스트**

```bash
npm start
```

필터 패널에서 값 변경 후 검색하여 동작 확인

**Step 5: 커밋**

```bash
git add frontend/src/
git commit -m "feat: 고급 필터링 UI 및 카테고리 선택 기능 추가"
```

---

## Task 7: 배달 정보 관리 기능

**파일:**
- Create: `frontend/src/components/DeliveryInfoModal.js`
- Modify: `frontend/src/App.js`

**Step 1: 배달 정보 입력 모달 컴포넌트**

`frontend/src/components/DeliveryInfoModal.js`:
```javascript
import React, { useState } from 'react';
import './DeliveryInfoModal.css';
import { updateDeliveryInfo } from '../services/api';

const DeliveryInfoModal = ({ restaurant, onClose, onUpdate }) => {
  const [deliveryFee, setDeliveryFee] = useState('');
  const [minimumOrder, setMinimumOrder] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      const data = await updateDeliveryInfo(restaurant.place_id || `temp-${Date.now()}`, {
        delivery_fee: parseInt(deliveryFee),
        minimum_order: parseInt(minimumOrder),
      });

      alert('배달 정보가 저장되었습니다!');
      onUpdate(data);
      onClose();
    } catch (error) {
      alert('저장에 실패했습니다.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <h2>📦 배달 정보 입력</h2>
        <h3>{restaurant.title}</h3>

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label>배달비 (원)</label>
            <input
              type="number"
              value={deliveryFee}
              onChange={(e) => setDeliveryFee(e.target.value)}
              placeholder="예: 3000"
              required
            />
          </div>

          <div className="form-group">
            <label>최소 주문 금액 (원)</label>
            <input
              type="number"
              value={minimumOrder}
              onChange={(e) => setMinimumOrder(e.target.value)}
              placeholder="예: 12000"
              required
            />
          </div>

          <div className="modal-actions">
            <button type="button" onClick={onClose} className="btn-cancel">
              취소
            </button>
            <button type="submit" className="btn-submit" disabled={loading}>
              {loading ? '저장 중...' : '저장'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default DeliveryInfoModal;
```

**Step 2: 모달 스타일**

`frontend/src/components/DeliveryInfoModal.css`:
```css
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.7);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
}

.modal-content {
  background: white;
  padding: 2rem;
  border-radius: 16px;
  max-width: 500px;
  width: 90%;
  box-shadow: 0 10px 25px rgba(0, 0, 0, 0.3);
}

.modal-content h2 {
  margin: 0 0 0.5rem 0;
  color: #333;
}

.modal-content h3 {
  margin: 0 0 1.5rem 0;
  color: #667eea;
  font-size: 1.1rem;
}

.form-group {
  margin-bottom: 1.5rem;
}

.form-group label {
  display: block;
  margin-bottom: 0.5rem;
  color: #555;
  font-weight: 600;
}

.form-group input {
  width: 100%;
  padding: 0.75rem;
  border: 2px solid #e0e0e0;
  border-radius: 8px;
  font-size: 1rem;
}

.form-group input:focus {
  outline: none;
  border-color: #667eea;
}

.modal-actions {
  display: flex;
  gap: 1rem;
  justify-content: flex-end;
  margin-top: 2rem;
}

.btn-cancel,
.btn-submit {
  padding: 0.75rem 1.5rem;
  border: none;
  border-radius: 8px;
  font-size: 1rem;
  cursor: pointer;
  transition: all 0.3s;
}

.btn-cancel {
  background: #e0e0e0;
  color: #555;
}

.btn-cancel:hover {
  background: #d0d0d0;
}

.btn-submit {
  background: #667eea;
  color: white;
}

.btn-submit:hover:not(:disabled) {
  background: #5568d3;
}

.btn-submit:disabled {
  background: #ccc;
  cursor: not-allowed;
}
```

**Step 3: App.js에 모달 통합**

`frontend/src/App.js`에 추가:
```javascript
// import 추가
import DeliveryInfoModal from './components/DeliveryInfoModal';

// 상태 추가
const [selectedRestaurant, setSelectedRestaurant] = useState(null);

// 레스토랑 카드에 버튼 추가 (restaurant-card 내부)
<button
  className="add-delivery-btn"
  onClick={() => setSelectedRestaurant(restaurant)}
>
  배달 정보 추가
</button>

// 모달 렌더링 (return 문 끝부분)
{selectedRestaurant && (
  <DeliveryInfoModal
    restaurant={selectedRestaurant}
    onClose={() => setSelectedRestaurant(null)}
    onUpdate={(data) => {
      // 업데이트된 정보 반영
      console.log('Updated:', data);
    }}
  />
)}
```

**Step 4: 버튼 스타일 추가**

`frontend/src/App.css`에 추가:
```css
.add-delivery-btn {
  width: 100%;
  padding: 0.75rem;
  margin-top: 1rem;
  background: #28a745;
  color: white;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-weight: bold;
  transition: background 0.3s;
}

.add-delivery-btn:hover {
  background: #218838;
}
```

**Step 5: 테스트**

검색 후 레스토랑 카드에서 "배달 정보 추가" 버튼 클릭하여 모달 동작 확인

**Step 6: 커밋**

```bash
git add frontend/src/
git commit -m "feat: 배달 정보 입력 모달 및 사용자 데이터 수집 기능 추가"
```

---

## Task 8: README 및 문서화

**파일:**
- Create: `README.md`
- Create: `docs/API.md`
- Create: `docs/SETUP.md`

**Step 1: README 작성**

`README.md`:
```markdown
# 🍽️ FoodFinder - 맛집 추천 프로그램

위치 기반 맞춤형 맛집 추천 웹 애플리케이션

## 주요 기능

- 📍 현재 위치 기반 맛집 검색
- 🔍 고급 필터링 (거리, 카테고리, 가격, 배달비)
- 🚚 배달 정보 관리 (사용자 입력)
- 🗺️ 네이버 지도 API 연동
- 💾 SQLite 데이터베이스 저장

## 기술 스택

### 백엔드
- Python 3.9+
- Flask 3.0
- SQLAlchemy
- 네이버 지도 API

### 프론트엔드
- React 18
- Axios
- CSS3

### 데이터베이스
- SQLite

## 빠른 시작

자세한 설정 방법은 [SETUP.md](docs/SETUP.md)를 참고하세요.

### 1. 환경 설정

```bash
# 저장소 클론
git clone <repository-url>
cd FoodFinder

# 백엔드 설정
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 환경 변수 설정
cp .env.example .env
# .env 파일을 편집하여 네이버 API 키 입력

# 프론트엔드 설정
cd ../frontend
npm install
```

### 2. 네이버 API 키 발급

1. [네이버 개발자 센터](https://developers.naver.com/main/) 접속
2. 애플리케이션 등록
3. Client ID와 Client Secret 발급
4. `backend/.env`에 키 입력

### 3. 실행

```bash
# 백엔드 서버 실행 (터미널 1)
cd backend
python app.py

# 프론트엔드 서버 실행 (터미널 2)
cd frontend
npm start
```

브라우저에서 http://localhost:3000 접속

## API 문서

자세한 API 명세는 [API.md](docs/API.md)를 참고하세요.

## 프로젝트 구조

```
FoodFinder/
├── backend/
│   ├── api/
│   │   ├── naver_map.py      # 네이버 API 클라이언트
│   │   └── restaurant.py     # 레스토랑 API 엔드포인트
│   ├── models/
│   │   ├── restaurant.py     # 레스토랑 모델
│   │   └── user_preference.py
│   ├── tests/
│   ├── app.py                # Flask 앱
│   ├── config.py             # 설정
│   └── database.py           # DB 초기화
├── frontend/
│   ├── src/
│   │   ├── components/       # React 컴포넌트
│   │   ├── services/         # API 서비스
│   │   └── App.js
│   └── public/
└── docs/
    ├── plans/                # 구현 계획
    ├── API.md
    └── SETUP.md
```

## 개발 로드맵

- [x] 프로젝트 초기 설정
- [x] 데이터베이스 모델
- [x] 네이버 API 연동
- [x] REST API 구현
- [x] React UI 구현
- [x] 필터링 시스템
- [x] 배달 정보 관리
- [ ] 네이버 지도 시각화
- [ ] 가격 정보 크롤링
- [ ] 사용자 인증
- [ ] 즐겨찾기 기능

## 라이선스

MIT License

## 기여

이슈와 PR을 환영합니다!
```

**Step 2: 커밋**

```bash
git add README.md docs/
git commit -m "docs: README 및 프로젝트 문서 작성"
```

---

## Task 9: 최종 테스트 및 배포 준비

**Step 1: 전체 테스트 실행**

```bash
# 백엔드 테스트
cd backend
pytest tests/ -v --cov=backend

# 프론트엔드 빌드 테스트
cd ../frontend
npm run build
```

**Step 2: 프로덕션 설정 파일 작성**

`backend/wsgi.py`:
```python
from app import create_app

app = create_app()

if __name__ == '__main__':
    app.run()
```

**Step 3: requirements 업데이트**

```bash
cd backend
pip freeze > requirements.txt
```

**Step 4: 최종 커밋**

```bash
git add .
git commit -m "chore: 최종 테스트 및 프로덕션 준비"
git tag -a v1.0.0 -m "Release version 1.0.0"
```

---

## 다음 단계 (향후 개선사항)

1. **네이버 지도 시각화**
   - React-Naver-Maps 라이브러리로 지도에 마커 표시
   - 클러스터링 기능

2. **배달 앱 크롤링**
   - Selenium으로 배달의민족/쿠팡이츠 정보 수집
   - 주기적 업데이트 스케줄러

3. **가격 정보**
   - 메뉴 가격 데이터 수집
   - 가격대별 필터링

4. **사용자 기능**
   - 회원가입/로그인
   - 즐겨찾기
   - 리뷰 시스템

5. **성능 최적화**
   - Redis 캐싱
   - PostgreSQL + PostGIS로 마이그레이션
   - 인덱싱 최적화

---

## 참고 자료

- [네이버 지도 API 문서](https://developers.naver.com/docs/serviceapi/search/local/local.md)
- [Flask 공식 문서](https://flask.palletsprojects.com/)
- [React 공식 문서](https://react.dev/)
- [SQLAlchemy 문서](https://docs.sqlalchemy.org/)
