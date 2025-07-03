from fastapi import APIRouter, Request, Depends, HTTPException
from starlette.responses import RedirectResponse
from authlib.integrations.starlette_client import OAuth
import os
import logging
from pdf_saas_app.app.db.session import get_db
from pdf_saas_app.app.db.models import User
from pdf_saas_app.app.services.auth_services import create_access_token
from sqlalchemy.orm import Session
from fastapi.responses import JSONResponse

router = APIRouter()
oauth = OAuth()
logger = logging.getLogger(__name__)

# Check required environment variables
def check_google_env_vars():
    required_vars = ['GOOGLE_CLIENT_ID', 'GOOGLE_CLIENT_SECRET', 'GOOGLE_REDIRECT_URI']
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    if missing_vars:
        logger.error(f"Missing Google OAuth environment variables: {missing_vars}")
        raise HTTPException(status_code=500, detail=f"Missing environment variables: {missing_vars}")
    return True

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

@router.get('/login')
async def login_via_google(request: Request):
    try:
        check_google_env_vars()
        redirect_uri = os.getenv('GOOGLE_REDIRECT_URI')
        logger.info(f"Redirecting to Google OAuth with redirect_uri: {redirect_uri}")
        return await oauth.google.authorize_redirect(request, redirect_uri)
    except Exception as e:
        logger.error(f"Error in Google login: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Google login failed: {str(e)}")

# Mobile-specific login endpoint
@router.get('/mobile/login')
async def mobile_login_via_google(request: Request):
    """Mobile endpoint that returns authorization URL instead of redirecting"""
    try:
        check_google_env_vars()
        redirect_uri = os.getenv('GOOGLE_REDIRECT_URI')
        logger.info(f"Generating Google OAuth URL for mobile with redirect_uri: {redirect_uri}")
        
        # Generate the authorization URL for mobile apps
        auth_url = await oauth.google.create_authorization_url(request, redirect_uri)
        logger.info(f"Generated authorization URL for mobile: {auth_url}")
        
        return JSONResponse({
            "auth_url": auth_url,
            "message": "Use this URL to open Google OAuth in mobile browser or WebView"
        })
    except Exception as e:
        logger.error(f"Error in mobile Google login: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Mobile Google login failed: {str(e)}")

@router.get('/callback')
async def auth_google_callback(request: Request, db: Session = Depends(get_db)):
    try:
        logger.info("Google OAuth callback received")
        
        # Check environment variables
        check_google_env_vars()
        
        # Get access token
        logger.info("Getting access token from Google")
        token = await oauth.google.authorize_access_token(request)
        logger.info("Access token received successfully")
        
        # Parse user info
        logger.info("Parsing user info from token")
        userinfo = await oauth.google.parse_id_token(request, token)
        logger.info(f"User info received: {userinfo.get('email', 'No email')}")
        
        if not userinfo or 'email' not in userinfo:
            logger.error("No userinfo or email in Google response")
            raise HTTPException(status_code=400, detail='Google authentication failed - no email received')
        
        email = userinfo['email']
        logger.info(f"Processing user with email: {email}")
        
        # Find or create user
        user = db.query(User).filter(User.email == email).first()
        if not user:
            logger.info(f"Creating new user for email: {email}")
            user = User(
                email=email, 
                hashed_password='',  # No password for Google users
                is_active=True
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            logger.info(f"New user created with ID: {user.id}")
        else:
            logger.info(f"Existing user found with ID: {user.id}")
        
        # Issue JWT
        logger.info("Creating JWT token")
        jwt = create_access_token(data={"sub": str(user.id)})
        logger.info("JWT token created successfully")
        
        # Redirect to frontend with JWT as query param
        frontend_url = os.getenv('FRONTEND_URL', 'http://localhost:5500/test_interface_render.html')
        redirect_url = f"{frontend_url}?token={jwt}"
        logger.info(f"Redirecting to frontend: {frontend_url}")
        
        return RedirectResponse(redirect_url)
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Unexpected error in Google callback: {str(e)}")
        logger.error(f"Error type: {type(e).__name__}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Google authentication failed: {str(e)}")

# Mobile-specific callback endpoint
@router.get('/mobile/callback')
async def mobile_auth_google_callback(request: Request, db: Session = Depends(get_db)):
    """Mobile callback endpoint that returns JSON instead of redirecting"""
    try:
        logger.info("Mobile Google OAuth callback received")
        
        # Check environment variables
        check_google_env_vars()
        
        # Get access token
        logger.info("Getting access token from Google")
        token = await oauth.google.authorize_access_token(request)
        logger.info("Access token received successfully")
        
        # Parse user info
        logger.info("Parsing user info from token")
        userinfo = await oauth.google.parse_id_token(request, token)
        logger.info(f"User info received: {userinfo.get('email', 'No email')}")
        
        if not userinfo or 'email' not in userinfo:
            logger.error("No userinfo or email in Google response")
            raise HTTPException(status_code=400, detail='Google authentication failed - no email received')
        
        email = userinfo['email']
        logger.info(f"Processing user with email: {email}")
        
        # Find or create user
        user = db.query(User).filter(User.email == email).first()
        if not user:
            logger.info(f"Creating new user for email: {email}")
            user = User(
                email=email, 
                hashed_password='',  # No password for Google users
                is_active=True
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            logger.info(f"New user created with ID: {user.id}")
        else:
            logger.info(f"Existing user found with ID: {user.id}")
        
        # Issue JWT
        logger.info("Creating JWT token")
        jwt = create_access_token(data={"sub": str(user.id)})
        logger.info("JWT token created successfully")
        
        # Return JSON response for mobile apps
        return JSONResponse({
            "success": True,
            "token": jwt,
            "user": {
                "id": user.id,
                "email": user.email,
                "is_active": user.is_active
            },
            "message": "Authentication successful"
        })
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Unexpected error in mobile Google callback: {str(e)}")
        logger.error(f"Error type: {type(e).__name__}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Mobile Google authentication failed: {str(e)}")

# Token exchange endpoint for mobile apps using authorization code
@router.post('/mobile/token')
async def mobile_token_exchange(request: Request, db: Session = Depends(get_db)):
    """Exchange authorization code for JWT token (for mobile apps)"""
    try:
        from fastapi import Form
        
        # Get authorization code from request body
        form_data = await request.form()
        auth_code = form_data.get('code')
        
        if not auth_code:
            raise HTTPException(status_code=400, detail="Authorization code is required")
        
        logger.info("Mobile token exchange with authorization code")
        
        # Check environment variables
        check_google_env_vars()
        
        # Exchange authorization code for access token
        redirect_uri = os.getenv('GOOGLE_REDIRECT_URI')
        token = await oauth.google.fetch_token(
            'https://oauth2.googleapis.com/token',
            authorization_response=f"?code={auth_code}",
            redirect_uri=redirect_uri
        )
        
        # Get user info
        userinfo = await oauth.google.parse_id_token(request, token)
        
        if not userinfo or 'email' not in userinfo:
            raise HTTPException(status_code=400, detail='Google authentication failed - no email received')
        
        email = userinfo['email']
        
        # Find or create user
        user = db.query(User).filter(User.email == email).first()
        if not user:
            user = User(
                email=email, 
                hashed_password='',
                is_active=True
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        
        # Issue JWT
        jwt = create_access_token(data={"sub": str(user.id)})
        
        return JSONResponse({
            "success": True,
            "token": jwt,
            "user": {
                "id": user.id,
                "email": user.email,
                "is_active": user.is_active
            }
        })
        
    except Exception as e:
        logger.error(f"Error in mobile token exchange: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Token exchange failed: {str(e)}")

@router.get('/debug')
async def debug_google_oauth():
    """Debug endpoint to check Google OAuth configuration"""
    try:
        # Check environment variables
        env_vars = {
            'GOOGLE_CLIENT_ID': os.getenv('GOOGLE_CLIENT_ID'),
            'GOOGLE_CLIENT_SECRET': os.getenv('GOOGLE_CLIENT_SECRET'),
            'GOOGLE_REDIRECT_URI': os.getenv('GOOGLE_REDIRECT_URI'),
            'FRONTEND_URL': os.getenv('FRONTEND_URL', 'http://localhost:5500/test_interface_render.html')
        }
        
        # Check if variables are set
        missing_vars = [k for k, v in env_vars.items() if not v]
        
        return {
            "status": "success" if not missing_vars else "error",
            "environment_variables": {
                k: "SET" if v else "MISSING" for k, v in env_vars.items()
            },
            "missing_variables": missing_vars,
            "oauth_registered": bool(oauth.google),
            "client_id_length": len(env_vars['GOOGLE_CLIENT_ID']) if env_vars['GOOGLE_CLIENT_ID'] else 0,
            "client_secret_length": len(env_vars['GOOGLE_CLIENT_SECRET']) if env_vars['GOOGLE_CLIENT_SECRET'] else 0
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "error_type": type(e).__name__
        }