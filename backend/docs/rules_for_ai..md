
Не забывайпро масштабируемость, архитектуру, правила программирования DRY, SOLID, Single Responsibility. Понятная архитектура.

СТАНДАРТАЛИЗАЦИЯ. Все комментарии единого стиля на английском. В функциях указываются ожидаемые args, что она выполняет кратко и что возвращает в тройнх кавычках. Весь код написан по стандартизированным решениям

Пример кода:
```python
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

class InvalidPayloadError(ValueError):
    """Raised when the input payload contains invalid data."""
    pass


def validate_user_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Validates and sanitizes incoming user registration data.

    Args:
        payload (Dict[str, Any]): Raw user payload containing account details.

    Returns:
        Dict[str, Any]: Sanitized user payload with normalized email and fields.

    Raises:
        InvalidPayloadError: If required fields are missing or email format is invalid.
    """
    required_fields = {"email", "username"}
    
    missing_fields = required_fields - payload.keys()
    if missing_fields:
        logger.error(f"Validation failed. Missing required fields: {missing_fields}")
        raise InvalidPayloadError(f"Missing required fields: {', '.join(missing_fields)}")

    email = str(payload["email"]).strip().lower()
    if "@" not in email or email.startswith("@") or email.endswith("@"):
        logger.error(f"Validation failed. Invalid email format: {email}")
        raise InvalidPayloadError(f"Invalid email address provided: {email}")

    return {
        "email": email,
        "username": str(payload["username"]).strip(),
        "is_active": True,
    }
```