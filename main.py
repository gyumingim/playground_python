from fastapi import FastAPI, Request, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.security import OAuth2AuthorizationCodeBearer
from starlette.middleware.sessions import SessionMiddleware

import os
import requests
from typing import Optional
from pydantic import BaseModel

# Google OAuth 클라이언트 설정
GOOGLE_CLIENT_ID = "YOUR_GOOGLE_CLIENT_ID"
GOOGLE_CLIENT_SECRET = "YOUR_GOOGLE_CLIENT_SECRET"
GOOGLE_REDIRECT_URI = "http://localhost:8000/callback"
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USER_INFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"

app = FastAPI()

# 세션 미들웨어 설정 (쿠키 기반 세션)
app.add_middleware(
    SessionMiddleware, 
    secret_key="your-secret-key-for-sessions"
)

# 템플릿 설정
templates = Jinja2Templates(directory="templates")

# 정적 파일 설정
app.mount("/static", StaticFiles(directory="static"), name="static")

# 사용자 모델
class User(BaseModel):
    id: str
    email: str
    name: Optional[str] = None
    picture: Optional[str] = None

# 루트 페이지 (로그인 페이지)
@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

# 구글 로그인 요청 핸들러
@app.get("/login/google")
async def login_google():
    # OAuth 인증 요청 URL 생성
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "response_type": "code",
        "scope": "openid email profile",
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "prompt": "select_account",
    }
    
    # URL 쿼리 파라미터 생성
    query_string = "&".join(f"{key}={value}" for key, value in params.items())
    auth_url = f"{GOOGLE_AUTH_URL}?{query_string}"
    
    # 구글 인증 페이지로 리디렉션
    return RedirectResponse(auth_url)

# OAuth 콜백 핸들러
@app.get("/callback")
async def auth_callback(request: Request, code: str):
    # 인증 코드로 액세스 토큰 요청
    token_data = {
        "code": code,
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "grant_type": "authorization_code",
    }
    
    token_response = requests.post(GOOGLE_TOKEN_URL, data=token_data)
    token_response_json = token_response.json()
    
    # 토큰 응답에서 액세스 토큰 추출
    access_token = token_response_json.get("access_token")
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to retrieve access token"
        )
    
    # 액세스 토큰으로 사용자 정보 요청
    user_info_response = requests.get(
        GOOGLE_USER_INFO_URL,
        headers={"Authorization": f"Bearer {access_token}"}
    )
    user_info = user_info_response.json()
    
    # 사용자 정보 저장 (실제 앱에서는 데이터베이스에 저장)
    user = User(
        id=user_info.get("sub"),
        email=user_info.get("email"),
        name=user_info.get("name"),
        picture=user_info.get("picture")
    )
    
    # 세션에 사용자 정보 저장
    request.session["user"] = user.dict()
    
    # 홈 페이지로 리디렉션
    return RedirectResponse(url="/home")

# 홈 페이지 (로그인 후)
@app.get("/home", response_class=HTMLResponse)
async def home(request: Request):
    # 세션에서 사용자 정보 확인
    user_data = request.session.get("user")
    if not user_data:
        # 사용자 정보가 없으면 로그인 페이지로 리디렉션
        return RedirectResponse(url="/")
    
    return templates.TemplateResponse(
        "home.html", 
        {"request": request, "user": user_data}
    )

# 로그아웃
@app.get("/logout")
async def logout(request: Request):
    # 세션에서 사용자 정보 삭제
    request.session.pop("user", None)
    return RedirectResponse(url="/")

# 앱 실행 (개발용)
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)