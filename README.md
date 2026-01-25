# FoodFinder - 맛집 추천 프로그램

위치 기반 맞춤형 맛집 추천 웹 애플리케이션

## 주요 기능

- 현재 위치 기반 맛집 검색
- 고급 필터링 (거리, 카테고리, 가격, 배달비)
- 배달 정보 관리 (사용자 입력)
- 네이버 지도 API 연동
- SQLite 데이터베이스 저장

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

### 1. 저장소 클론

```bash
git clone <repository-url>
cd FoodFinder
```

### 2. 백엔드 설정

```bash
cd backend
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate

pip install -r requirements.txt
```

### 3. 환경 변수 설정

```bash
cp .env.example .env
```

`.env` 파일을 편집하여 네이버 API 키를 입력하세요:

```
SECRET_KEY=your-secret-key-here
NAVER_CLIENT_ID=your-naver-client-id
NAVER_CLIENT_SECRET=your-naver-client-secret
DATABASE_URL=sqlite:///foodfinder.db
```

### 4. 네이버 API 키 발급

1. [네이버 개발자 센터](https://developers.naver.com/main/) 접속
2. 애플리케이션 등록
3. "검색" API 사용 신청
4. Client ID와 Client Secret 발급
5. `.env` 파일에 키 입력

### 5. 프론트엔드 설정

```bash
cd ../frontend
npm install
```

### 6. 실행

**백엔드 서버 실행 (터미널 1):**
```bash
cd backend
python app.py
```

**프론트엔드 서버 실행 (터미널 2):**
```bash
cd frontend
npm start
```

브라우저에서 http://localhost:3000 접속

## API 엔드포인트

| 메소드 | 엔드포인트 | 설명 |
|--------|-----------|------|
| GET | `/api/health` | 헬스 체크 |
| POST | `/api/restaurants/search` | 맛집 검색 |
| POST | `/api/restaurants/<place_id>/delivery` | 배달 정보 업데이트 |
| GET | `/api/restaurants/nearby` | 주변 맛집 조회 |

### 검색 API 요청 예시

```bash
curl -X POST http://localhost:5000/api/restaurants/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "한식",
    "latitude": 37.5665,
    "longitude": 126.9780,
    "radius": 1000
  }'
```

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
    └── plans/                # 구현 계획
```

## 테스트 실행

```bash
cd backend
pytest tests/ -v
```

## 라이선스

MIT License
