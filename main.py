from fastapi import FastAPI, HTTPException  # FastAPI 앱 객체와 HTTP 예외 클래스 임포트
from fastapi.middleware.cors import CORSMiddleware  # 👈 추가  # 브라우저 CORS(교차 출처 요청) 허용을 위한 미들웨어
from fastapi.responses import FileResponse  # 정적 파일(index.html)을 그대로 응답으로 내려주기 위한 클래스
from pydantic import BaseModel, Field  # 요청/응답 데이터 검증 및 스키마 정의용 Pydantic 도구
from typing import Optional, List  # 선택적 필드, 리스트 타입 힌트
from datetime import datetime, timedelta  # 목업 주가 데이터의 날짜 계산용
import math  # 포물선 궤적 계산에 필요한 삼각함수(sin, cos, radians)
import random  # 목업 사용자/주가 데이터를 무작위로 생성하기 위함

app = FastAPI(  # FastAPI 애플리케이션 인스턴스 생성 (이 객체가 uvicorn이 구동하는 ASGI 앱)
    title="User Management API",  # Swagger UI(/docs) 상단에 표시될 API 이름
    description="""
    사용자 관리 백엔드 API입니다.

    ## 주요 기능
    - 사용자 목록 조회
    - 사용자 단건 조회
    - 사용자 생성

    ## 특징
    - Mock 데이터 30명 기본 제공
    - Swagger UI 자동 제공 (/docs)
    """,  # Swagger UI에 마크다운으로 렌더링되는 API 설명
    version="1.0.0",  # API 버전 표시 (OpenAPI 문서에 노출)
    contact={
        "name": "Doyoung Kim",
        "email": "example@email.com"
    }  # OpenAPI 문서에 표시되는 담당자 연락처 정보
)

# --------------------------------------------------
# 🔥 CORS 설정 (여기 추가!)
# --------------------------------------------------
origins = [  # 이 백엔드에 요청을 허용할 프론트엔드 출처(origin) 목록
    "http://127.0.0.1:9000",   # 👈 프론트 주소
    "http://localhost:9000",   # 👈 혹시 localhost 쓸 경우 대비
]

app.add_middleware(  # 모든 요청/응답을 가로채는 CORS 미들웨어를 앱에 등록
    CORSMiddleware,
    allow_origins=origins,      # 허용할 출처 (위에서 정의한 origins 리스트만 허용)
    allow_credentials=True,     # 쿠키/인증 헤더 등 자격 증명을 포함한 요청 허용
    allow_methods=["*"],        # 모든 HTTP 메서드 허용 (GET, POST, PUT, DELETE 등)
    allow_headers=["*"],        # 모든 요청 헤더 허용
)

# --------------------------------------------------
# 데이터 모델 정의
# --------------------------------------------------
class UserCreate(BaseModel):  # POST /users 요청 바디의 스키마 (클라이언트가 보내는 데이터)
    username: str = Field(..., example="honggildong", description="사용자 이름")  # 필수(...) 문자열 필드
    email: str = Field(..., example="hong@example.com", description="이메일 주소")  # 필수 문자열 필드
    age: Optional[int] = Field(None, example=25, description="나이")  # 선택 필드, 기본값 None

class UserResponse(BaseModel):  # 사용자 관련 API가 반환하는 응답 스키마
    id: int = Field(..., example=1, description="사용자 ID")  # 필수 정수 필드
    username: str = Field(..., example="honggildong")  # 필수 문자열 필드
    email: str = Field(..., example="hong@example.com")  # 필수 문자열 필드
    age: Optional[int] = Field(None, example=25)  # 선택 정수 필드

# --------------------------------------------------
# Mock 데이터 생성
# --------------------------------------------------
def generate_mock_users():  # 서버 시작 시 호출되어 30명의 가짜 사용자 데이터를 만드는 함수
    users = []  # 생성된 사용자를 담을 리스트
    for i in range(1, 31):  # id 1부터 30까지 반복
        users.append({
            "id": i,  # 순차 증가하는 사용자 ID
            "username": f"user{i}",  # user1, user2 ... 형태의 아이디
            "email": f"user{i}@example.com",  # 아이디 기반 이메일
            "age": random.randint(18, 60)  # 18~60 사이 무작위 나이
        })
    return users  # 생성된 사용자 리스트 반환

db_users = generate_mock_users()  # 앱 로딩 시 1회 실행되어 메모리 DB 역할을 하는 리스트를 만듦 (재시작하면 초기화됨)

# --------------------------------------------------
# API 엔드포인트
# --------------------------------------------------

@app.get("/", include_in_schema=False)  # 루트 경로 GET 요청 처리, Swagger 문서 목록에는 노출하지 않음
def read_root():
    return FileResponse("index.html")  # 프론트엔드 페이지(index.html)를 그대로 응답으로 반환


@app.get("/tetris", include_in_schema=False)  # 캔버스 기반 테트리스 게임 페이지 제공
def read_tetris():
    return FileResponse("index2.html")  # index2.html을 그대로 응답으로 반환


@app.get("/health")  # 서버 생존 확인용 헬스체크 엔드포인트
def health_check():
    return {"status": "ok", "message": "FastAPI 서버 정상 동작 중"}  # 단순 상태 메시지 JSON 반환


@app.get("/users", response_model=List[UserResponse])  # 전체 사용자 목록 조회, 응답은 UserResponse 리스트로 검증/직렬화
def get_users():
    return db_users  # 메모리에 저장된 사용자 전체를 그대로 반환


@app.get("/users/{user_id}", response_model=UserResponse)  # 경로 파라미터 user_id로 특정 사용자 조회
def get_user(user_id: int):
    for user in db_users:  # 전체 사용자를 순회하며
        if user["id"] == user_id:  # id가 일치하는 사용자를 찾으면
            return user  # 해당 사용자 반환
    raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")  # 못 찾으면 404 에러 발생


@app.post("/users", response_model=UserResponse, status_code=201)  # 신규 사용자 생성, 성공 시 201 Created 반환
def create_user(user: UserCreate):  # 요청 바디를 UserCreate 스키마로 자동 검증
    new_id = len(db_users) + 1  # 현재 목록 길이 + 1을 새 ID로 사용 (단일 프로세스 한정 안전)

    new_user = {
        "id": new_id,  # 새로 부여된 ID
        "username": user.username,  # 요청에서 받은 사용자 이름
        "email": user.email,  # 요청에서 받은 이메일
        "age": user.age  # 요청에서 받은 나이 (없으면 None)
    }

    db_users.append(new_user)  # 메모리 DB(리스트)에 새 사용자 추가
    return new_user  # 생성된 사용자 정보 반환


# --------------------------------------------------
# 차트용 Mock 데이터 (프론트 index.html에서 사용)
# --------------------------------------------------
def generate_mock_stock_data(days: int = 60, base_price: int = 71000):  # 최근 days일치 캔들스틱(OHLC) 목업 데이터 생성
    data = []  # 일자별 시세를 담을 리스트
    prev_close = base_price  # 첫날의 시가로 사용할 기준가 (이후에는 전날 종가가 다음날 시가가 됨)
    date = datetime.now() - timedelta(days=days)  # days일 전 날짜부터 시작

    for _ in range(days):  # days 횟수만큼 반복 (주말 제외되므로 실제 데이터 수는 더 적음)
        date += timedelta(days=1)  # 하루씩 날짜 증가

        if date.weekday() >= 5:  # 주말 제외  # weekday()가 5(토) 또는 6(일)이면
            continue  # 해당 날짜는 건너뜀 (장이 열리지 않는 날 가정)

        change_rate = (random.random() - 0.5) * 0.04  # ±2% 변동  # -2%~+2% 사이 무작위 등락률
        open_price = prev_close  # 시가는 전날 종가와 동일하게 설정
        close = round(open_price * (1 + change_rate) / 10) * 10  # 종가 = 시가 * (1+등락률), 10원 단위로 반올림
        high = round(max(open_price, close) * (1 + random.random() * 0.015) / 10) * 10  # 고가 = 시가/종가 중 큰 값에 최대 1.5% 추가
        low = round(min(open_price, close) * (1 - random.random() * 0.015) / 10) * 10  # 저가 = 시가/종가 중 작은 값에서 최대 1.5% 차감

        data.append({
            "date": date.strftime("%Y-%m-%d"),  # 프론트에서 Date로 파싱하기 쉬운 ISO 형식 문자열
            "open": open_price,  # 시가
            "high": high,  # 고가
            "low": low,  # 저가
            "close": close  # 종가
        })

        prev_close = close  # 다음 반복에서 시가로 사용할 수 있도록 종가를 저장

    return data  # 영업일 기준 OHLC 리스트 반환


def compute_trajectory(v0: float = 40, angle_deg: float = 45, g: float = 9.8, steps: int = 60):  # 투사체(포물선) 운동 궤적 계산
    angle = math.radians(angle_deg)  # 각도(도)를 라디안으로 변환 (삼각함수는 라디안 입력 필요)
    flight_time = (2 * v0 * math.sin(angle)) / g  # 물리 공식: 총 비행 시간 = 2*v0*sin(θ)/g
    points = []  # 시간에 따른 (x, y) 좌표를 담을 리스트

    for i in range(steps + 1):  # 0부터 steps까지, 총 (steps+1)개의 샘플 포인트 생성
        t = flight_time * i / steps  # 전체 비행시간을 steps 구간으로 나눈 현재 시점의 경과 시간
        x = v0 * math.cos(angle) * t  # 수평 거리 = 초기속도의 수평 성분 * 시간 (등속 운동)
        y = v0 * math.sin(angle) * t - 0.5 * g * t * t  # 높이 = 초기속도의 수직 성분 * 시간 - 중력에 의한 낙하량
        points.append({"x": round(x, 2), "y": max(0, round(y, 2))})  # 소수점 2자리로 반올림, 높이는 음수 방지(0 이상)

    return points  # 시간 순서대로 정렬된 궤적 좌표 리스트 반환


@app.get("/mock/stock")  # 프론트 캔들스틱 차트에 사용할 주가 목업 데이터 제공
def get_mock_stock():
    return generate_mock_stock_data()  # 기본 파라미터(60일, 71000원)로 생성한 OHLC 데이터 반환


@app.get("/mock/funnel")  # 프론트 퍼널 차트에 사용할 단계별 인원 목업 데이터 제공
def get_mock_funnel():
    return {
        "stages": ["노출", "클릭", "가입", "결제"],  # 퍼널 단계 이름 (진입 순서대로)
        "values": [10000, 4200, 1800, 650]  # 각 단계별 인원 수 (단계가 진행될수록 감소)
    }


@app.get("/mock/parabola")  # 프론트 포물선 시뮬레이션 차트에 사용할 궤적 데이터 제공
def get_mock_parabola():
    v0, angle, g = 40, 45, 9.8  # 초기 속도(m/s), 발사 각도(도), 중력가속도(m/s^2) 고정값
    return {
        "v0": v0,  # 초기 속도 (프론트에서 제목 표시에 사용)
        "angle": angle,  # 발사 각도 (프론트에서 제목 표시에 사용)
        "g": g,  # 중력가속도
        "points": compute_trajectory(v0, angle, g)  # 실제 궤적 좌표 리스트
    }


@app.get("/mock/radial")  # 프론트 방사형(radial) 차트에 사용할 목표 달성률 목업 데이터 제공
def get_mock_radial():
    return {
        "labels": ["매출 달성률", "방문자 달성률", "전환율 달성률"],  # 각 지표 이름
        "series": [76, 62, 45]  # 각 지표의 달성률(%) 값
    }
