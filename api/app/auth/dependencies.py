from fastapi import Header, HTTPException, status

from api.app.config.settings import API_KEY


def verify_api_key(
    x_api_key: str = Header(..., description="API key for authorization")
) -> None:
    if x_api_key != API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API Key"
        )
