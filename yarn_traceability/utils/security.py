"""Password hashing with bcrypt."""
import bcrypt

import config


def hash_password(password: str, rounds: int = config.BCRYPT_ROUNDS) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=rounds)).decode("ascii")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("ascii"))
    except ValueError:
        return False
