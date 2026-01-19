from fastapi import APIRouter, Depends, HTTPException, status, Body
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr
from datetime import datetime, timedelta
from typing import Optional, Dict
from jose import JWTError, jwt
from passlib.context import CryptContext
import json
import os
import resend

# CONFIG
SECRET_KEY = os.getenv("SECRET_KEY", "tu_clave_secreta_super_segura_cambiar_en_prod")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 120 # 2 Hours

# RESEND API KEY
resend.api_key = os.getenv("RESEND_API_KEY", "")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

USERS_FILE = os.getenv("USERS_FILE_PATH", "users.json")

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

class User(BaseModel):
    username: str
    email: Optional[str] = None
    disabled: Optional[bool] = None
    is_admin: Optional[bool] = False

class UserInDB(User):
    hashed_password: str

class UserRegister(BaseModel):
    email: EmailStr
    password: str

# DATABASE HANDLING
users_db: Dict[str, dict] = {}

def load_users():
    global users_db
    
    # Ensure directory exists if it's a path with folders
    directory = os.path.dirname(USERS_FILE)
    if directory and not os.path.exists(directory):
        try:
            os.makedirs(directory, exist_ok=True)
        except Exception as e:
            print(f"Error creating directory for users file: {e}")

    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, "r") as f:
                users_db = json.load(f)
        except Exception as e:
            print(f"Error loading users: {e}")
            users_db = {}
    
    # Ensure admin always exists if DB is empty or corrupt
    admin_username = "gerardoj.suastegui"
    admin_pass = os.getenv("ADMIN_PASSWORD", "admin123")
    
    if admin_username not in users_db:
        # Create new admin
        users_db[admin_username] = {
            "username": admin_username,
            "email": "gerardoj.suastegui@velea.com",
            "hashed_password": pwd_context.hash(admin_pass),
            "disabled": False,
            "is_admin": True
        }
        save_users()
    else:
        # FORCE UPDATE ADMIN PASSWORD FROM ENV
        # This ensures the password is always what is set in Dockploy env vars
        print("Forcing admin password update from environment variable...")
        users_db[admin_username]["hashed_password"] = pwd_context.hash(admin_pass)
        users_db[admin_username]["is_admin"] = True
        users_db[admin_username]["disabled"] = False
        save_users()

def save_users():
    try:
        with open(USERS_FILE, "w") as f:
            json.dump(users_db, f, indent=4)
    except Exception as e:
        print(f"Error saving users: {e}")

# Load on startup (module level)
load_users()

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_user(db, username: str):
    if username in db:
        user_dict = db[username]
        return UserInDB(**user_dict)
    # Also allow login by email if username not found directly
    for user_key, user_val in db.items():
        if user_val.get("email") == username:
             return UserInDB(**user_val)
    return None

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception
    user = get_user(users_db, username=token_data.username)
    if user is None:
        raise credentials_exception
    return user

async def get_current_active_user(current_user: User = Depends(get_current_user)):
    if current_user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

router = APIRouter()

@router.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    print(f"Login attempt for user: {form_data.username}")
    user = get_user(users_db, form_data.username)
    if not user:
        print(f"User not found: {form_data.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not verify_password(form_data.password, user.hashed_password):
        print(f"Invalid password for user: {form_data.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    print(f"Login successful for user: {form_data.username}")
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    # Use username as sub
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/register")
async def register(user_data: UserRegister):
    # Check if email exists
    for u in users_db.values():
        if u.get("email") == user_data.email:
            raise HTTPException(status_code=400, detail="Email already registered")

    # Create new user
    username = user_data.email.split("@")[0] # Simple username generation
    if username in users_db:
        username = f"{username}_{int(datetime.now().timestamp())}"
    
    hashed_pw = pwd_context.hash(user_data.password)
    
    new_user = {
        "username": username,
        "email": user_data.email,
        "hashed_password": hashed_pw,
        "disabled": True, # Disabled by default until admin approves
        "is_admin": False
    }
    
    users_db[username] = new_user
    save_users()
    
    # Send Email via Resend
    try:
        r = resend.Emails.send({
            "from": "onboarding@resend.dev",
            "to": user_data.email,
            "subject": "Registro en Velea Limpieza - Pendiente de Aprobación",
            "html": f"""
            <h1>¡Gracias por registrarte!</h1>
            <p>Tu cuenta ha sido creada y está <strong>pendiente de aprobación</strong> por un administrador.</p>
            <p><strong>Usuario:</strong> {username}</p>
            <p>Recibirás una notificación cuando tu cuenta sea activada.</p>
            """
        })
        print(f"Email sent: {r}")
    except Exception as e:
        print(f"Failed to send email: {e}")
        # Don't fail registration if email fails, just log it
    
    return {"message": "User created successfully. Waiting for admin approval.", "username": username}

# --- ADMIN ENDPOINTS ---

async def get_current_admin_user(current_user: User = Depends(get_current_active_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Not authorized. Admin access required.")
    return current_user

@router.get("/users", response_model=list[User])
async def get_all_users(current_user: User = Depends(get_current_admin_user)):
    # Return list of users (without passwords)
    return [User(**u) for u in users_db.values()]

@router.post("/users/{username}/approve")
async def approve_user(username: str, current_user: User = Depends(get_current_admin_user)):
    if username not in users_db:
        raise HTTPException(status_code=404, detail="User not found")
        
    users_db[username]["disabled"] = False
    save_users()
    return {"message": f"User {username} approved successfully"}

@router.post("/users/{username}/toggle-status")
async def toggle_user_status(username: str, current_user: User = Depends(get_current_admin_user)):
    if username not in users_db:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Prevent disabling self
    if username == current_user.username:
         raise HTTPException(status_code=400, detail="Cannot disable your own admin account")

    current_status = users_db[username].get("disabled", False)
    users_db[username]["disabled"] = not current_status
    save_users()
    return {"message": f"User {username} is now {'disabled' if not current_status else 'enabled'}"}
