from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timedelta
import jwt
from passlib.context import CryptContext
from loguru import logger

from app.models.database import get_db, SessionLocal
from app.models.schemas import User, UserSession
from app.utils.config import settings

router = APIRouter()
security = HTTPBearer()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Pydantic models
class UserLogin(BaseModel):
    email: str
    password: str

class UserRegister(BaseModel):
    email: str
    password: str
    kalshi_api_key: Optional[str] = None
    kalshi_private_key: Optional[str] = None
    risk_profile: str = "moderate"

class UserResponse(BaseModel):
    id: str
    email: str
    risk_profile: str
    is_active: bool
    created_at: datetime

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    expires_in: int
    user: UserResponse

class PasswordReset(BaseModel):
    email: str

class PasswordUpdate(BaseModel):
    current_password: str
    new_password: str

# Helper functions
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Hash a password"""
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=24)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")
    return encoded_jwt

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security),
                     db: SessionLocal = Depends(get_db)) -> User:
    """Get current authenticated user"""
    try:
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

        # Decode JWT token
        payload = jwt.decode(credentials.credentials, settings.SECRET_KEY, algorithms=["HS256"])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception

        # Get user from database
        user = db.query(User).filter(User.id == user_id).first()
        if user is None:
            raise credentials_exception

        # Check if user is active
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Inactive user"
            )

        return user

    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

@router.post("/register", response_model=TokenResponse)
async def register(user_data: UserRegister, db: SessionLocal = Depends(get_db)):
    """Register a new user"""
    try:
        # Check if user already exists
        existing_user = db.query(User).filter(User.email == user_data.email).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )

        # Validate risk profile
        if user_data.risk_profile not in settings.RISK_PROFILES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid risk profile. Must be one of: {list(settings.RISK_PROFILES.keys())}"
            )

        # Create new user
        hashed_password = get_password_hash(user_data.password)
        new_user = User(
            email=user_data.email,
            hashed_password=hashed_password,
            kalshi_api_key=user_data.kalshi_api_key,
            kalshi_private_key=user_data.kalshi_private_key,
            risk_profile=user_data.risk_profile,
            is_active=True
        )

        db.add(new_user)
        db.commit()
        db.refresh(new_user)

        # Create access token
        access_token_expires = timedelta(hours=24)
        access_token = create_access_token(
            data={"sub": str(new_user.id)},
            expires_delta=access_token_expires
        )

        # Save user session
        user_session = UserSession(
            user_id=new_user.id,
            token=access_token,
            expires_at=datetime.utcnow() + access_token_expires
        )
        db.add(user_session)
        db.commit()

        logger.info(f"User registered successfully: {user_data.email}")

        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=int(access_token_expires.total_seconds()),
            user=UserResponse(
                id=str(new_user.id),
                email=new_user.email,
                risk_profile=new_user.risk_profile,
                is_active=new_user.is_active,
                created_at=new_user.created_at
            )
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error registering user: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )

@router.post("/login", response_model=TokenResponse)
async def login(user_credentials: UserLogin, db: SessionLocal = Depends(get_db)):
    """Authenticate user and return access token"""
    try:
        # Find user by email
        user = db.query(User).filter(User.email == user_credentials.email).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )

        # Verify password
        if not verify_password(user_credentials.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )

        # Check if user is active
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Account is inactive"
            )

        # Create access token
        access_token_expires = timedelta(hours=24)
        access_token = create_access_token(
            data={"sub": str(user.id)},
            expires_delta=access_token_expires
        )

        # Save user session
        user_session = UserSession(
            user_id=user.id,
            token=access_token,
            expires_at=datetime.utcnow() + access_token_expires
        )
        db.add(user_session)
        db.commit()

        logger.info(f"User logged in successfully: {user.email}")

        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=int(access_token_expires.total_seconds()),
            user=UserResponse(
                id=str(user.id),
                email=user.email,
                risk_profile=user.risk_profile,
                is_active=user.is_active,
                created_at=user.created_at
            )
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during login: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )

@router.post("/logout")
async def logout(current_user: User = Depends(get_current_user),
                 db: SessionLocal = Depends(get_db)):
    """Logout user and invalidate token"""
    try:
        # Invalidate user sessions
        db.query(UserSession).filter(UserSession.user_id == current_user.id).delete()
        db.commit()

        logger.info(f"User logged out: {current_user.email}")

        return {"message": "Successfully logged out"}

    except Exception as e:
        logger.error(f"Error during logout: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Logout failed"
        )

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current user information"""
    return UserResponse(
        id=str(current_user.id),
        email=current_user.email,
        risk_profile=current_user.risk_profile,
        is_active=current_user.is_active,
        created_at=current_user.created_at
    )

@router.put("/profile")
async def update_profile(
    risk_profile: str,
    kalshi_api_key: Optional[str] = None,
    kalshi_private_key: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: SessionLocal = Depends(get_db)
):
    """Update user profile"""
    try:
        # Validate risk profile
        if risk_profile not in settings.RISK_PROFILES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid risk profile. Must be one of: {list(settings.RISK_PROFILES.keys())}"
            )

        # Update user profile
        current_user.risk_profile = risk_profile
        if kalshi_api_key is not None:
            current_user.kalshi_api_key = kalshi_api_key
        if kalshi_private_key is not None:
            current_user.kalshi_private_key = kalshi_private_key

        current_user.updated_at = datetime.utcnow()
        db.commit()

        logger.info(f"User profile updated: {current_user.email}")

        return {"message": "Profile updated successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating profile: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Profile update failed"
        )

@router.post("/change-password")
async def change_password(
    password_data: PasswordUpdate,
    current_user: User = Depends(get_current_user),
    db: SessionLocal = Depends(get_db)
):
    """Change user password"""
    try:
        # Verify current password
        if not verify_password(password_data.current_password, current_user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect"
            )

        # Hash new password
        new_hashed_password = get_password_hash(password_data.new_password)

        # Update password
        current_user.hashed_password = new_hashed_password
        current_user.updated_at = datetime.utcnow()
        db.commit()

        # Invalidate all user sessions (force re-login)
        db.query(UserSession).filter(UserSession.user_id == current_user.id).delete()
        db.commit()

        logger.info(f"Password changed for user: {current_user.email}")

        return {"message": "Password changed successfully. Please login again."}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error changing password: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password change failed"
        )

@router.get("/sessions")
async def get_user_sessions(current_user: User = Depends(get_current_user),
                           db: SessionLocal = Depends(get_db)):
    """Get active user sessions"""
    try:
        sessions = db.query(UserSession).filter(
            UserSession.user_id == current_user.id,
            UserSession.expires_at > datetime.utcnow()
        ).all()

        return {
            "sessions": [
                {
                    "id": str(session.id),
                    "created_at": session.created_at,
                    "expires_at": session.expires_at,
                    "is_current": True  # Simplified - would check against current token
                }
                for session in sessions
            ],
            "total_sessions": len(sessions)
        }

    except Exception as e:
        logger.error(f"Error getting user sessions: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get sessions"
        )

@router.delete("/sessions")
async def revoke_all_sessions(current_user: User = Depends(get_current_user),
                             db: SessionLocal = Depends(get_db)):
    """Revoke all user sessions"""
    try:
        # Delete all user sessions
        deleted_count = db.query(UserSession).filter(UserSession.user_id == current_user.id).delete()
        db.commit()

        logger.info(f"All sessions revoked for user: {current_user.email}")

        return {"message": f"Revoked {deleted_count} sessions successfully"}

    except Exception as e:
        logger.error(f"Error revoking sessions: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to revoke sessions"
        )

@router.get("/verify-token")
async def verify_token(current_user: User = Depends(get_current_user)):
    """Verify if current token is valid"""
    return {
        "valid": True,
        "user_id": str(current_user.id),
        "email": current_user.email,
        "expires_at": None  # Would extract from token in production
    }