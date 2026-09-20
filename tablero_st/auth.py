import base64
import hashlib
import hmac

from .db import fetch_one


def check_django_password(password, encoded):
    if not password or not encoded or encoded.startswith("!"):
        return False
    partes = encoded.split("$")
    if len(partes) != 4 or partes[0] != "pbkdf2_sha256":
        return False
    _, iterations, salt, esperado = partes
    derivado = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        int(iterations),
        dklen=32,
    )
    calculado = base64.b64encode(derivado).decode("ascii").strip()
    return hmac.compare_digest(calculado, esperado)


def autenticar(email, password):
    user = fetch_one(
        """
        SELECT id, email, nombre, password, es_admin_global, is_superuser, is_active
        FROM cuentas_usuario
        WHERE email = %s
        """,
        (email.strip(),),
    )
    if not user or not user["is_active"]:
        return None
    if not check_django_password(password, user["password"]):
        return None
    return {
        "id": user["id"],
        "email": user["email"],
        "nombre": user["nombre"] or user["email"],
        "es_admin": bool(user["es_admin_global"] or user["is_superuser"]),
    }
