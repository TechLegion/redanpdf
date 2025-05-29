from fastapi import APIRouter, Request, Depends, HTTPException
from starlette.responses import RedirectResponse
from authlib.integrations.starlette_client import OAuth
import os
from pdf_saas_app.app.db.session import get_db
from pdf_saas_app.app.db.models import User
from pdf_saas_app.app.services.auth_services import create_access_token
from sqlalchemy.orm import Session

router = APIRouter()
oauth = OAuth()

# Register Google OAuth
oauth.register(
    name='google',
    client_id=os.getenv('GOOGLE_CLIENT_ID'),
    client_secret=os.getenv('GOOGLE_CLIENT_SECRET'),
    access_token_url='https://oauth2.googleapis.com/token',
    access_token_params=None,
    authorize_url='https://accounts.google.com/o/oauth2/auth',
    authorize_params=None,
    api_base_url='https://www.googleapis.com/oauth2/v1/',
    userinfo_endpoint='https://openidconnect.googleapis.com/v1/userinfo',
    client_kwargs={'scope': 'openid email profile'},
)

@router.get('/login/google')
async def login_via_google(request: Request):
    redirect_uri = os.getenv('GOOGLE_REDIRECT_URI')
    return await oauth.google.authorize_redirect(request, redirect_uri)

@router.get('/google/callback')
async def auth_google_callback(request: Request, db: Session = Depends(get_db)):
    token = await oauth.google.authorize_access_token(request)
    userinfo = await oauth.google.parse_id_token(request, token)
    if not userinfo or 'email' not in userinfo:
        raise HTTPException(status_code=400, detail='Google authentication failed')
    # Find or create user
    user = db.query(User).filter(User.email == userinfo['email']).first()
    if not user:
        user = User(email=userinfo['email'], hashed_password='')  # No password for Google users
        db.add(user)
        db.commit()
        db.refresh(user)
    # Issue JWT
    jwt = create_access_token(data={"sub": user.id})
    # Redirect to frontend with JWT as query param
    frontend_url = os.getenv('FRONTEND_URL', 'http://localhost:5500/pdf_saas_app/frontend/index.html')
    redirect_url = f"{frontend_url}?token={jwt}"
    return RedirectResponse(redirect_url)