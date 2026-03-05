import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt import (
    create_2fa_pending_token,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.auth.dependencies import get_current_user
from app.auth.schemas import (
    ChangeEmailRequest,
    ChangePasswordRequest,
    LoginRequest,
    LoginResponse,
    MessageResponse,
    ProfileResponse,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    TwoFactorDisableRequest,
    TwoFactorEnableResponse,
    TwoFactorLoginRequest,
    TwoFactorSetupResponse,
    TwoFactorValidateRequest,
    TwoFactorVerifyRequest,
)
from app.core.database import get_db
from app.core.rate_limit import limiter
from app.core.security import hash_password, verify_password
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
async def register(body: RegisterRequest, request: Request, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == body.email))
    if result.scalar_one_or_none():
        # NOTE: Specific error message kept for frontend UX. This is a LOW-risk
        # user enumeration vector — an attacker could probe for registered emails.
        # To mitigate fully, return a generic "Registration failed" and handle
        # the duplicate-email case in the frontend via a separate flow.
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(email=body.email, password_hash=hash_password(body.password))
    db.add(user)
    await db.commit()
    await db.refresh(user)

    return TokenResponse(
        access_token=create_access_token(str(user.id)),
        refresh_token=create_refresh_token(str(user.id)),
    )


@router.post("/login", response_model=LoginResponse)
@limiter.limit("10/minute")
async def login(body: LoginRequest, request: Request, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if user.totp_enabled:
        return LoginResponse(
            requires_2fa=True,
            partial_token=create_2fa_pending_token(str(user.id)),
        )

    return LoginResponse(
        access_token=create_access_token(str(user.id)),
        refresh_token=create_refresh_token(str(user.id)),
    )


@router.post("/refresh", response_model=TokenResponse)
@limiter.limit("20/minute")
async def refresh(body: RefreshRequest, request: Request, db: AsyncSession = Depends(get_db)):
    payload = decode_token(body.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    user_id = payload["sub"]

    # Verify user still exists and is active
    result = await db.execute(
        select(User).where(User.id == uuid.UUID(user_id), User.is_active.is_(True))
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="User not found or inactive")

    return TokenResponse(
        access_token=create_access_token(user_id),
        refresh_token=create_refresh_token(user_id),
    )


@router.get("/me", response_model=ProfileResponse)
async def get_profile(
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return the authenticated user's profile."""
    result = await db.execute(
        select(User).where(User.id == uuid.UUID(user_id))
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return ProfileResponse(
        id=str(user.id),
        email=user.email,
        is_active=user.is_active,
        totp_enabled=user.totp_enabled,
        created_at=user.created_at.isoformat() if user.created_at else "",
        updated_at=user.updated_at.isoformat() if user.updated_at else None,
    )


@router.put("/password", response_model=MessageResponse)
async def change_password(
    body: ChangePasswordRequest,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Change the authenticated user's password."""
    result = await db.execute(
        select(User).where(User.id == uuid.UUID(user_id))
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if not verify_password(body.current_password, user.password_hash):
        raise HTTPException(status_code=400, detail="Current password is incorrect")

    user.password_hash = hash_password(body.new_password)
    await db.commit()

    # Invalidate all existing tokens so the user must re-authenticate
    from app.core.token_blacklist import blacklist_all_user_tokens

    await blacklist_all_user_tokens(str(user.id))

    return MessageResponse(message="Password updated successfully")


@router.put("/email", response_model=ProfileResponse)
async def change_email(
    body: ChangeEmailRequest,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Change the authenticated user's email address."""
    result = await db.execute(
        select(User).where(User.id == uuid.UUID(user_id))
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=400, detail="Password is incorrect")

    # Check if new email is already taken
    existing = await db.execute(
        select(User).where(User.email == body.new_email, User.id != user.id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already in use")

    user.email = body.new_email
    await db.commit()
    await db.refresh(user)
    return ProfileResponse(
        id=str(user.id),
        email=user.email,
        is_active=user.is_active,
        totp_enabled=user.totp_enabled,
        created_at=user.created_at.isoformat() if user.created_at else "",
        updated_at=user.updated_at.isoformat() if user.updated_at else None,
    )


# ---------- Two-Factor Authentication ----------


@router.post("/2fa/setup", response_model=TwoFactorSetupResponse)
@limiter.limit("5/minute")
async def setup_2fa(
    request: Request,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate TOTP secret and QR code. Does NOT enable 2FA yet."""
    from app.auth.totp import (
        encrypt_totp_secret,
        generate_qr_code_data_uri,
        generate_totp_secret,
        get_provisioning_uri,
    )

    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.totp_enabled:
        raise HTTPException(status_code=400, detail="2FA is already enabled")

    secret = generate_totp_secret()
    user.totp_secret_enc = encrypt_totp_secret(secret)
    await db.commit()

    uri = get_provisioning_uri(secret, user.email)
    qr = generate_qr_code_data_uri(uri)
    return TwoFactorSetupResponse(qr_code=qr, secret=secret, provisioning_uri=uri)


@router.post("/2fa/verify", response_model=TwoFactorEnableResponse)
@limiter.limit("5/minute")
async def verify_and_enable_2fa(
    body: TwoFactorVerifyRequest,
    request: Request,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Verify TOTP code and enable 2FA. Returns backup codes (shown once)."""
    from app.auth.totp import (
        decrypt_totp_secret,
        generate_backup_codes,
        hash_backup_codes,
        verify_totp_code,
    )

    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.totp_enabled:
        raise HTTPException(status_code=400, detail="2FA is already enabled")
    if not user.totp_secret_enc:
        raise HTTPException(status_code=400, detail="Call /auth/2fa/setup first")

    secret = decrypt_totp_secret(user.totp_secret_enc)
    if not verify_totp_code(secret, body.code):
        raise HTTPException(status_code=400, detail="Invalid TOTP code")

    backup_codes = generate_backup_codes()
    user.backup_codes_hash = hash_backup_codes(backup_codes)
    user.totp_enabled = True
    await db.commit()

    return TwoFactorEnableResponse(
        message="Two-factor authentication enabled",
        backup_codes=backup_codes,
    )


@router.post("/2fa/disable", response_model=MessageResponse)
@limiter.limit("5/minute")
async def disable_2fa(
    body: TwoFactorDisableRequest,
    request: Request,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Disable 2FA. Requires password + TOTP/backup code."""
    from app.auth.totp import decrypt_totp_secret, verify_backup_code, verify_totp_code

    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not user.totp_enabled:
        raise HTTPException(status_code=400, detail="2FA is not enabled")
    if not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=400, detail="Password is incorrect")

    secret = decrypt_totp_secret(user.totp_secret_enc)  # type: ignore[arg-type]
    code_valid = verify_totp_code(secret, body.code)
    if not code_valid and user.backup_codes_hash:
        idx = verify_backup_code(body.code, user.backup_codes_hash)
        code_valid = idx is not None

    if not code_valid:
        raise HTTPException(status_code=400, detail="Invalid code")

    user.totp_enabled = False
    user.totp_secret_enc = None
    user.backup_codes_hash = None
    await db.commit()

    # Invalidate all existing tokens after 2FA removal
    from app.core.token_blacklist import blacklist_all_user_tokens

    await blacklist_all_user_tokens(str(user.id))

    return MessageResponse(message="Two-factor authentication disabled")


@router.post("/2fa/login", response_model=TokenResponse)
@limiter.limit("10/minute")
async def login_2fa(
    body: TwoFactorLoginRequest, request: Request, db: AsyncSession = Depends(get_db),
):
    """Second step of login: exchange partial_token + TOTP code for full tokens."""
    from app.auth.totp import decrypt_totp_secret, verify_backup_code, verify_totp_code

    payload = decode_token(body.partial_token)
    if not payload or payload.get("type") != "2fa_pending":
        raise HTTPException(status_code=401, detail="Invalid or expired partial token")

    user_id = payload["sub"]
    result = await db.execute(
        select(User).where(User.id == uuid.UUID(user_id), User.is_active.is_(True))
    )
    user = result.scalar_one_or_none()
    if not user or not user.totp_enabled or not user.totp_secret_enc:
        raise HTTPException(status_code=401, detail="Invalid state")

    secret = decrypt_totp_secret(user.totp_secret_enc)
    code_valid = verify_totp_code(secret, body.code)

    # Try backup code if TOTP fails
    if not code_valid and user.backup_codes_hash:
        idx = verify_backup_code(body.code, user.backup_codes_hash)
        if idx is not None:
            code_valid = True
            # Consume the backup code
            codes = list(user.backup_codes_hash)
            codes.pop(idx)
            user.backup_codes_hash = codes
            await db.commit()

    if not code_valid:
        raise HTTPException(status_code=401, detail="Invalid 2FA code")

    return TokenResponse(
        access_token=create_access_token(user_id),
        refresh_token=create_refresh_token(user_id),
    )


@router.post("/2fa/validate", response_model=MessageResponse)
async def validate_2fa(
    body: TwoFactorValidateRequest,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Validate a TOTP code for sensitive operations (e.g. trading activation)."""
    from app.auth.totp import decrypt_totp_secret, verify_backup_code, verify_totp_code

    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user = result.scalar_one_or_none()
    if not user or not user.totp_enabled or not user.totp_secret_enc:
        raise HTTPException(status_code=403, detail="2FA is not enabled")

    secret = decrypt_totp_secret(user.totp_secret_enc)
    code_valid = verify_totp_code(secret, body.code)

    if not code_valid and user.backup_codes_hash:
        idx = verify_backup_code(body.code, user.backup_codes_hash)
        if idx is not None:
            code_valid = True
            codes = list(user.backup_codes_hash)
            codes.pop(idx)
            user.backup_codes_hash = codes
            await db.commit()

    if not code_valid:
        raise HTTPException(status_code=403, detail="Invalid 2FA code")

    return MessageResponse(message="Code verified")


# ---------- GDPR Compliance ----------

UTC = timezone.utc


@router.delete("/user", status_code=204)
@limiter.limit("1/minute")
async def delete_account(
    request: Request,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete user account and all associated data (GDPR right to erasure)."""
    uid = uuid.UUID(user_id)
    result = await db.execute(select(User).where(User.id == uid))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    await db.delete(user)
    await db.commit()
    # Blacklist all tokens so any cached JWTs are rejected
    from app.core.token_blacklist import blacklist_all_user_tokens

    await blacklist_all_user_tokens(user_id, ttl_seconds=86400)
    return Response(status_code=204)


@router.get("/user/export")
@limiter.limit("2/minute")
async def export_user_data(
    request: Request,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Export all user data (GDPR right to data portability)."""
    uid = uuid.UUID(user_id)
    # Collect all user data
    user_result = await db.execute(select(User).where(User.id == uid))
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    from app.models.signal import Signal
    from app.models.trade import Trade
    from app.models.strategy import Strategy
    from app.models.position import Position
    from app.models.order import Order

    signals = (await db.execute(select(Signal).where(Signal.user_id == uid))).scalars().all()
    trades = (await db.execute(select(Trade).where(Trade.user_id == uid))).scalars().all()
    strategies = (await db.execute(select(Strategy).where(Strategy.user_id == uid))).scalars().all()
    positions = (await db.execute(select(Position).where(Position.user_id == uid))).scalars().all()
    orders = (await db.execute(select(Order).where(Order.user_id == uid))).scalars().all()

    export = {
        "user": {
            "id": str(user.id),
            "email": user.email,
            "created_at": str(user.created_at) if hasattr(user, "created_at") else None,
            "has_2fa": user.totp_enabled,
        },
        "strategies": [
            {
                "id": str(s.id),
                "name": s.name,
                "is_active": s.is_active,
                "config": s.config,
            }
            for s in strategies
        ],
        "signals": [
            {
                "id": str(s.id),
                "symbol": s.symbol,
                "direction": s.direction,
                "created_at": str(s.created_at),
            }
            for s in signals
        ],
        "trades": [
            {
                "id": str(t.id),
                "symbol": t.symbol,
                "direction": t.direction,
                "entry_price": t.entry_price,
                "exit_price": t.exit_price,
                "pnl": t.pnl,
                "created_at": str(t.created_at),
            }
            for t in trades
        ],
        "positions": [
            {
                "id": str(p.id),
                "symbol": p.symbol,
                "direction": p.direction,
                "entry_price": p.entry_price,
            }
            for p in positions
        ],
        "orders": [
            {
                "id": str(o.id),
                "symbol": o.symbol,
                "direction": o.direction,
                "status": o.status,
            }
            for o in orders
        ],
        "exported_at": str(datetime.now(UTC)),
    }
    return export
