# FoodFinder 빠른 시작 가이드

## 🚀 5분 안에 시작하기

### 1단계: 필수 프로그램 설치 확인

- ✅ Python 3.9 이상
- ✅ Node.js 14 이상
- ✅ Git

### 2단계: 프로젝트 설정

```bash
# 1. 저장소 클론
git clone <repository-url>
cd FoodFinder

# 2. 백엔드 가상환경 생성 및 패키지 설치
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
cd ..

# 3. 프론트엔드 패키지 설치
cd frontend
npm install
cd ..
```

### 3단계: Naver API 키 발급

1. **https://developers.naver.com/** 접속
2. **로그인** 후 **Application > 애플리케이션 등록** 클릭
3. 다음 정보 입력:
    - 애플리케이션 이름: `FoodFinder` (원하는 이름)
    - 사용 API: **검색** 체크
    - 비로그인 오픈 API 서비스 환경:
        - **WEB 설정** 추가
        - 웹 서비스 URL: `http://localhost:3000`
4. **등록하기** 클릭
5. **Client ID**와 **Client Secret** 복사

### 4단계: 환경 변수 설정

```bash
# backend/.env 파일 생성 (backend/.env.example 참고)
# 아래 내용을 복사하여 backend/.env 파일에 붙여넣기
```

```env
NAVER_CLIENT_ID=발급받은_클라이언트_ID
NAVER_CLIENT_SECRET=발급받은_클라이언트_시크릿
SECRET_KEY=mysecretkey123
DATABASE_URL=sqlite:///foodfinder.db
```

### 5단계: 실행! 🎉

**Windows:**

```bash
# 프로젝트 루트에서
run.bat
```

**수동 실행:**

```bash
# 터미널 1 - 백엔드
cd backend
.venv\Scripts\python.exe app.py

# 터미널 2 - 프론트엔드
cd frontend
npm start
```

### 6단계: 브라우저에서 확인

브라우저가 자동으로 열리지 않으면:

- **http://localhost:3000** 접속

## 🎯 사용 방법

1. **위치 권한 허용**: 브라우저에서 위치 권한을 허용하세요
2. **검색어 입력**: "한식", "카페", "치킨" 등 원하는 음식 종류 입력
3. **검색 버튼 클릭**: 주변 맛집이 표시됩니다!
4. **필터 사용**: 거리, 카테고리 등으로 결과를 필터링할 수 있습니다

## 🛑 서버 종료

**Windows:**

```bash
stop.bat
```

**수동 종료:**
각 터미널에서 `Ctrl + C` 누르기

## ❓ 문제 해결

### 검색 결과가 나오지 않아요

- Naver API 키가 올바른지 확인하세요
- `backend/.env` 파일에 키가 제대로 입력되었는지 확인하세요
- 백엔드 서버를 재시작하세요

### 위치를 찾을 수 없어요

- 브라우저에서 위치 권한을 허용했는지 확인하세요
- HTTPS가 아닌 localhost에서는 위치 권한이 필요합니다

### 포트가 이미 사용 중이에요

```bash
# 포트 5000 사용 중인 프로세스 종료
taskkill /F /IM python.exe

# 포트 3000 사용 중인 프로세스 종료
taskkill /F /IM node.exe
```

## 📚 더 알아보기

자세한 내용은 [README.md](README.md)를 참고하세요.

## 🎊 완료!

이제 FoodFinder로 주변 맛집을 찾아보세요! 🍽️
