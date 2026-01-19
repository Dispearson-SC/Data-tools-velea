
import json
import os
from passlib.context import CryptContext

# Configuration matches auth.py
USERS_FILE = "users.json"
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def reset_password(username, new_password):
    if not os.path.exists(USERS_FILE):
        print(f"Error: {USERS_FILE} not found.")
        return

    try:
        with open(USERS_FILE, "r") as f:
            users_db = json.load(f)
    except Exception as e:
        print(f"Error loading users: {e}")
        return

    if username not in users_db:
        print(f"User {username} not found.")
        # Optional: Create if not exists? The user asked to "reconfigure", implying it exists.
        # But looking at auth.py, if admin is missing it creates it.
        # Let's just create/update it to be safe as this is likely the admin.
        print(f"Creating/Updating user {username}...")
        users_db[username] = {
            "username": username,
            "email": f"{username}@velea.com", # Default email if creating
            "hashed_password": pwd_context.hash(new_password),
            "disabled": False,
            "is_admin": True
        }
    else:
        print(f"Updating password for {username}...")
        users_db[username]["hashed_password"] = pwd_context.hash(new_password)
        # Ensure account is enabled and admin
        users_db[username]["disabled"] = False
        users_db[username]["is_admin"] = True

    try:
        with open(USERS_FILE, "w") as f:
            json.dump(users_db, f, indent=4)
        print("Password updated successfully.")
    except Exception as e:
        print(f"Error saving users: {e}")

if __name__ == "__main__":
    reset_password("gerardoj.suastegui", "Uranio6Polonio+")
