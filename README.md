# User Management API

FastAPI로 만든 간단한 사용자 관리 REST API 예제입니다. 서버를 시작할 때 30명의 Mock 사용자를 메모리에 생성하며, Swagger UI를 통해 API를 바로 탐색하고 호출할 수 있습니다.

## 기술 구성

- Python 3.9+
- [FastAPI](https://fastapi.tiangolo.com/): API 라우팅, 요청/응답 검증, OpenAPI 문서 생성
- [Pydantic](https://docs.pydantic.dev/): 사용자 생성 요청과 응답 스키마 정의
- Uvicorn: ASGI 서버

## 빠른 시작

가상 환경을 만들고 필요한 패키지를 설치합니다.

```bash
python -m venv .venv
source .venv/bin/activate
pip install fastapi "uvicorn[standard]"
```

개발 서버를 실행합니다.

```bash
uvicorn main:app --reload
```

서버는 기본적으로 `http://127.0.0.1:8000`에서 실행됩니다.

- 대화형 API 문서: `http://127.0.0.1:8000/docs`
- ReDoc 문서: `http://127.0.0.1:8000/redoc`
- OpenAPI 명세(JSON): `http://127.0.0.1:8000/openapi.json`

## API 요약

| Method | Path | 설명 | 성공 응답 |
| --- | --- | --- | --- |
| `GET` | `/` | 웹 프론트(`index.html`) 서빙 | `200 OK` |
| `GET` | `/health` | 서버 상태 확인 | `200 OK` |
| `GET` | `/users` | 전체 사용자 목록 조회 | `200 OK` |
| `GET` | `/users/{user_id}` | ID로 사용자 한 명 조회 | `200 OK`, `404 Not Found` |
| `POST` | `/users` | 새 사용자 생성 | `201 Created` |

### 사용자 생성

`username`과 `email`은 필수이고, `age`는 선택 값입니다.

```bash
curl -X POST http://127.0.0.1:8000/users \
  -H "Content-Type: application/json" \
  -d '{
    "username": "honggildong",
    "email": "hong@example.com",
    "age": 25
  }'
```

응답 예시:

```json
{
  "id": 31,
  "username": "honggildong",
  "email": "hong@example.com",
  "age": 25
}
```

### 사용자 조회

```bash
curl http://127.0.0.1:8000/users/1
```

존재하지 않는 ID를 요청하면 다음과 같이 `404 Not Found`를 반환합니다.

```json
{
  "detail": "사용자를 찾을 수 없습니다."
}
```

## 구현 구조와 동작 방식

애플리케이션 전체는 `main.py`에 있으며, 시작 시 `generate_mock_users()`가 ID 1~30의 사용자 목록을 만듭니다. 각 사용자의 나이는 18~60 범위에서 무작위로 배정되므로 서버를 재시작하면 초기 데이터의 나이가 달라질 수 있습니다.

`UserCreate` 모델은 생성 요청 본문을, `UserResponse` 모델은 API 응답을 정의합니다. FastAPI는 이 모델을 사용해 요청 데이터를 검증하고 OpenAPI/Swagger 문서의 스키마를 자동 생성합니다. 새 사용자는 현재 목록 길이를 기준으로 다음 ID를 부여받고, 프로세스 메모리의 `db_users` 목록에 추가됩니다.

## 현재 제약 사항

이 프로젝트는 API 학습 및 테스트용 예제입니다.

- 데이터는 인메모리에만 저장되므로 서버 재시작 시 생성한 사용자가 사라집니다.
- 인증·인가, 수정·삭제 API, 페이지네이션, 중복 이메일 검사 기능은 아직 없습니다.
- `email`은 문자열 필드이며 이메일 형식의 엄격한 검증은 하지 않습니다.
- 다중 워커/동시 요청 환경에서는 현재의 ID 생성 방식 대신 데이터베이스의 자동 증가 ID 또는 UUID를 사용하는 것이 안전합니다.

실서비스로 확장할 때는 데이터베이스와 마이그레이션을 도입하고, 인증 및 입력 제약 조건을 추가하는 것을 권장합니다.

## 라이선스

[MIT License](LICENSE)
