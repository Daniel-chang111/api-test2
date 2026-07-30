"""KRX OpenAPI를 브라우저에 안전하게 전달하는 작은 FastAPI 앱."""

from datetime import date, timedelta
from pathlib import Path
import json
import os
import re
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse


BASE_DIR = Path(__file__).resolve().parent
KEY_FILE = BASE_DIR / ".key"
KRX_STOCK_URL = "https://data-dbg.krx.co.kr/svc/apis/sto/stk_bydd_trd"
DATE_PATTERN = re.compile(r"^\d{8}$")

app = FastAPI(title="KRX 시세 화면", version="1.0.0")


def default_trade_date() -> str:
    """주말에는 직전 금요일을 기본 조회일로 사용한다."""
    target = date.today() - timedelta(days=1)
    while target.weekday() >= 5:
        target -= timedelta(days=1)
    return target.strftime("%Y%m%d")


def load_krx_key() -> str:
    """환경 변수 또는 gitignore된 .key 파일에서만 인증키를 읽는다."""
    key = os.getenv("KRX_AUTH_KEY", "").strip()
    if not key and KEY_FILE.exists():
        key = KEY_FILE.read_text(encoding="utf-8").strip()
    if not key:
        raise HTTPException(
            status_code=500,
            detail="KRX 인증키가 없습니다. .key 파일 또는 KRX_AUTH_KEY 환경 변수를 설정하세요.",
        )
    return key


@app.get("/", include_in_schema=False)
def read_root() -> FileResponse:
    return FileResponse(BASE_DIR / "index.html")


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/krx/stocks")
def get_krx_stocks(
    bas_dd: str = Query(default_factory=default_trade_date, description="기준일자 (YYYYMMDD)"),
) -> dict:
    """승인된 유가증권시장 일별매매정보를 조회해 전달한다."""
    if not DATE_PATTERN.fullmatch(bas_dd):
        raise HTTPException(status_code=422, detail="bas_dd는 YYYYMMDD 형식이어야 합니다.")

    request = Request(
        f"{KRX_STOCK_URL}?{urlencode({'basDd': bas_dd})}",
        headers={"AUTH_KEY": load_krx_key(), "Accept": "application/json"},
        method="GET",
    )
    try:
        with urlopen(request, timeout=15) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        if error.code in (401, 403):
            raise HTTPException(
                status_code=502,
                detail=(
                    "KRX가 인증을 거부했습니다. KRX OpenAPI에서 "
                    "'유가증권 일별매매정보(stk_bydd_trd)' 이용기간 및 승인 상태를 확인하세요."
                ),
            ) from error
        raise HTTPException(status_code=502, detail=f"KRX API 요청 실패 (HTTP {error.code})") from error
    except (URLError, TimeoutError, json.JSONDecodeError) as error:
        raise HTTPException(status_code=502, detail="KRX API 응답을 가져오지 못했습니다.") from error

    if payload.get("respCode") and payload.get("respCode") != "200":
        raise HTTPException(status_code=502, detail=payload.get("respMsg", "KRX API 오류"))

    records = payload.get("OutBlock_1", [])
    return {"basDd": bas_dd, "apiName": "유가증권 일별매매정보", "apiId": "stk_bydd_trd", "count": len(records), "items": records}
