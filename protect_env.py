"""
أداة تشفير وفك تشفير ملف .env
الاستخدام:
  python protect_env.py encrypt    ← تشفير .env إلى .env.encrypted
  python protect_env.py decrypt    ← فك .env.encrypted إلى .env
  python protect_env.py unlock     ← فك في الذاكرة فقط (اختبار كلمة المرور)

سيُطلب منك إدخال كلمة مرور (مرتين عند التشفير للتأكيد).
"""
import os
import sys
import getpass
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

ENV_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_FILE = os.path.join(ENV_DIR, '.env')
ENCRYPTED_FILE = os.path.join(ENV_DIR, '.env.encrypted')
SALT_FILE = os.path.join(ENV_DIR, '.env.salt')


def _derive_key(password: str, salt: bytes) -> bytes:
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=600_000)
    return base64.urlsafe_b64encode(kdf.derive(password.encode()))


def encrypt(password: str):
    if not os.path.exists(ENV_FILE):
        print(f"[ERROR] File {ENV_FILE} not found.")
        return False

    with open(ENV_FILE, 'rb') as f:
        data = f.read()

    salt = os.urandom(16)
    key = _derive_key(password, salt)
    fernet = Fernet(key)
    encrypted = fernet.encrypt(data)

    with open(ENCRYPTED_FILE, 'wb') as f:
        f.write(encrypted)
    with open(SALT_FILE, 'wb') as f:
        f.write(salt)

    print(f"[OK] Encrypted {ENV_FILE} -> {ENCRYPTED_FILE}")
    print(f"[INFO] You can now delete {ENV_FILE} (keep .env.salt and .env.encrypted)")
    return True


def decrypt(password: str) -> bool:
    if not os.path.exists(ENCRYPTED_FILE):
        print(f"[ERROR] File {ENCRYPTED_FILE} not found.")
        return False
    if not os.path.exists(SALT_FILE):
        print(f"[ERROR] File {SALT_FILE} not found (cannot decrypt without it).")
        return False

    with open(SALT_FILE, 'rb') as f:
        salt = f.read()
    with open(ENCRYPTED_FILE, 'rb') as f:
        encrypted = f.read()

    try:
        key = _derive_key(password, salt)
        fernet = Fernet(key)
        decrypted = fernet.decrypt(encrypted)
    except Exception:
        print("[ERROR] Wrong password.")
        return False

    with open(ENV_FILE, 'wb') as f:
        f.write(decrypted)
    print(f"[OK] Decrypted -> {ENV_FILE}")
    return True


def verify_password(password: str) -> bool:
    """التحقق من كلمة المرور دون فك الملف إلى القرص."""
    if not os.path.exists(ENCRYPTED_FILE) or not os.path.exists(SALT_FILE):
        return False
    with open(SALT_FILE, 'rb') as f:
        salt = f.read()
    with open(ENCRYPTED_FILE, 'rb') as f:
        encrypted = f.read()
    try:
        key = _derive_key(password, salt)
        fernet = Fernet(key)
        fernet.decrypt(encrypted)
        return True
    except Exception:
        return False


def decrypt_to_memory(password: str) -> dict:
    """فك التشفير وإرجاع محتوى .env على شكل قاموس (دون حفظ على القرص)."""
    if not os.path.exists(ENCRYPTED_FILE) or not os.path.exists(SALT_FILE):
        return {}
    with open(SALT_FILE, 'rb') as f:
        salt = f.read()
    with open(ENCRYPTED_FILE, 'rb') as f:
        encrypted = f.read()
    try:
        key = _derive_key(password, salt)
        fernet = Fernet(key)
        decrypted = fernet.decrypt(encrypted).decode('utf-8')
        result = {}
        for line in decrypted.splitlines():
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '=' in line:
                k, v = line.split('=', 1)
                result[k.strip()] = v.strip()
        return result
    except Exception:
        return {}


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return

    command = sys.argv[1]

    if command == 'encrypt':
        if len(sys.argv) >= 3:
            encrypt(sys.argv[2])
        else:
            p1 = getpass.getpass("[KEY] Enter password to encrypt .env: ")
            p2 = getpass.getpass("[KEY] Re-enter password to confirm: ")
            if p1 != p2:
                print("[ERROR] Passwords do not match.")
                return
            encrypt(p1)

    elif command == 'decrypt':
        password = sys.argv[2] if len(sys.argv) >= 3 else getpass.getpass("[KEY] Enter password to decrypt .env: ")
        decrypt(password)

    elif command == 'unlock':
        password = sys.argv[2] if len(sys.argv) >= 3 else getpass.getpass("[KEY] Enter password to test: ")
        if verify_password(password):
            print("[OK] Password is correct.")
        else:
            print("[ERROR] Password is incorrect.")

    else:
        print(f"[ERROR] Unknown command: {command}")
        print(__doc__)


if __name__ == '__main__':
    main()
