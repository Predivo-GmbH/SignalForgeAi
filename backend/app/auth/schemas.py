from pydantic import BaseModel, EmailStr, Field, field_validator


def _validate_password_strength(v: str) -> str:
    """Shared password complexity check for all password-setting schemas."""
    if not any(c.isupper() for c in v):
        raise ValueError('Password must contain at least one uppercase letter')
    if not any(c.islower() for c in v):
        raise ValueError('Password must contain at least one lowercase letter')
    if not any(c.isdigit() for c in v):
        raise ValueError('Password must contain at least one digit')
    return v


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)

    @field_validator('password')
    @classmethod
    def validate_password_strength(cls, v):
        return _validate_password_strength(v)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class LoginResponse(BaseModel):
    """Login response — either full tokens or 2FA challenge."""
    access_token: str | None = None
    refresh_token: str | None = None
    token_type: str = "bearer"
    requires_2fa: bool = False
    partial_token: str | None = None


class RefreshRequest(BaseModel):
    refresh_token: str


class ProfileResponse(BaseModel):
    id: str
    email: str
    is_active: bool
    totp_enabled: bool = False
    created_at: str
    updated_at: str | None = None


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)

    @field_validator('new_password')
    @classmethod
    def validate_password_strength(cls, v):
        return _validate_password_strength(v)


class ChangeEmailRequest(BaseModel):
    new_email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class MessageResponse(BaseModel):
    message: str


# ---------- Two-Factor Authentication ----------


class TwoFactorSetupResponse(BaseModel):
    qr_code: str
    secret: str
    provisioning_uri: str


class TwoFactorVerifyRequest(BaseModel):
    code: str = Field(min_length=6, max_length=6)


class TwoFactorEnableResponse(BaseModel):
    message: str
    backup_codes: list[str]


class TwoFactorDisableRequest(BaseModel):
    password: str = Field(min_length=1, max_length=128)
    code: str = Field(min_length=6, max_length=9)


class TwoFactorLoginRequest(BaseModel):
    partial_token: str
    code: str = Field(min_length=6, max_length=9)


class TwoFactorValidateRequest(BaseModel):
    code: str = Field(min_length=6, max_length=9)
