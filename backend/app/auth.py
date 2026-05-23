"""
Supabase JWT doğrulama middleware.
Her korumalı endpoint bu fonksiyonu kullanır.
"""

import logging
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from app.config import settings

logger = logging.getLogger(__name__)

_bearer = HTTPBearer(auto_error=False)

ALGORITHM = "HS256"


def _get_jwt_secret() -> str:
    # Supabase JWT secret = service key'in ikinci segmenti decode edilince çıkar.
    # Kolay yol: Supabase Dashboard → Settings → API → JWT Secret
    # .env'e SUPABASE_JWT_SECRET olarak ekleyin.
    secret = getattr(settings, "SUPABASE_JWT_SECRET", None)
    if not secret:
        # Fallback: service key'den çıkar (base64 middle segment)
        import base64, json
        try:
            parts = settings.SUPABASE_SERVICE_KEY.split(".")
            padded = parts[1] + "=" * (-len(parts[1]) % 4)
            payload = json.loads(base64.urlsafe_b64decode(padded))
            logger.warning("SUPABASE_JWT_SECRET tanımlanmamış, service key'den çıkarıldı.")
            return settings.SUPABASE_SERVICE_KEY  # geçici
        except Exception:
            raise RuntimeError("SUPABASE_JWT_SECRET veya SUPABASE_SERVICE_KEY gerekli.")
    return secret


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
) -> dict:
    """
    Authorization: Bearer <supabase_jwt> header'ından kullanıcıyı doğrular.
    Başarısız olursa 401 döner.
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Kimlik doğrulama gerekli.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    try:
        payload = jwt.decode(
            token,
            settings.SUPABASE_ANON_KEY,
            algorithms=[ALGORITHM],
            options={"verify_aud": False},
        )
        user_id: str = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Geçersiz token.")
        return {"id": user_id, "email": payload.get("email"), "role": payload.get("role")}
    except JWTError as exc:
        logger.warning("JWT doğrulama hatası: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Geçersiz veya süresi dolmuş token.",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
) -> Optional[dict]:
    """Token varsa doğrula, yoksa None döndür (anonim erişim)."""
    if not credentials:
        return None
    try:
        return await get_current_user(credentials)
    except HTTPException:
        return None
