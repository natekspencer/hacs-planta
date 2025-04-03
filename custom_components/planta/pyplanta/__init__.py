"""Planta API client."""

from asyncio import Lock
import logging
from typing import Any, Callable, Final

from aiohttp import ClientSession
import jwt

from .utils import decode

_LOGGER = logging.getLogger(__name__)

API_V1_ENDPOINT: Final = "https://app.getplanta.com/api/v1"
AUTH_ENDPOINT: Final = (
    "https://www.googleapis.com/identitytoolkit/v3/relyingparty/verifyPassword"
)
AUTH_ENDPOINT_KEY: Final = "QUl6YVN5RDE5MWFiWC1tT3FfZDlGczBiSkhhdENjajZ4OG5qX1dV"
CLIENT_VERSION_HEADER: Final = {"client-version": "ios-3.65.4"}


class Planta:
    """Planta API client class."""

    _lock = Lock()
    _token: dict[str, Any] | None = None
    _refresh_token_callback: Callable[[dict[str, str]], None] | None = None

    def __init__(
        self,
        *,
        session: ClientSession | None = None,
        token: dict[str, Any] | None = None,
        refresh_token_callback: Callable[[dict[str, str]], None] | None = None,
    ) -> None:
        """Initialize the client."""
        self._client = session if session else ClientSession()
        self._should_close = session is None
        self._headers: dict[str, str] = CLIENT_VERSION_HEADER.copy()
        if token:
            self._token = token
            self._headers["Authorization"] = f"Bearer {token['id_token']}"
        if refresh_token_callback:
            self._refresh_token_callback = refresh_token_callback

    @property
    def token(self) -> dict[str, str] | None:
        """Return the token, if any."""
        return self._token

    async def login(self, email: str, password: str) -> None:
        """Login to the Litter-Robot api and generate a new token."""
        tokens = await self._request(
            "POST",
            AUTH_ENDPOINT,
            params={"key": decode(AUTH_ENDPOINT_KEY)},
            json={"email": email, "password": password, "returnSecureToken": True},
        )
        self._token = {
            "id_token": tokens["idToken"],
            "refresh_token": tokens["refreshToken"],
        }
        self._headers["Authorization"] = f"Bearer {self._token['id_token']}"

    async def close(self) -> None:
        """Close the client."""
        if self._should_close:
            await self._client.close()
            self._client = None

    async def get_plants(self) -> list[dict[str, Any]]:
        """Get plants."""
        result = await self._request("GET", f"{API_V1_ENDPOINT}/userPlants")
        return result.get("data", {}).get("userPlants", [])

    async def get_plant_state(self, plant_id: str) -> dict[str, Any]:
        """Get plants."""
        result = await self._request(
            "GET", f"{API_V1_ENDPOINT}/userPlants/{plant_id}/actions/state"
        )
        return result.get("data", {})

    async def get_plant_images_and_notes(self, plant_id: str) -> list[dict[str, Any]]:
        """Get plants."""
        result = await self._request(
            "GET", f"{API_V1_ENDPOINT}/userPlants/{plant_id}/imagesAndNotes"
        )
        return result.get("data", {}).get("actions", [])

    async def plant_action_complete(self, action_id: str) -> bool:
        """Mark a plant action as completed."""
        if not (
            user_id := jwt.decode(
                self.token["id_token"],
                options={"verify_signature": False, "verify_exp": False},
                leeway=-30,
            ).get("user_id")
        ):
            return False
        result = await self._request(
            "POST",
            f"{API_V1_ENDPOINT}/actions/complete",
            json={"actions": [[action_id, user_id]]},
        )
        return result.get("status") == 200

    def _is_token_valid(self) -> bool:
        """Return `True` if the token is still valid."""
        if self.token is None:
            return False
        try:
            jwt.decode(
                self.token["id_token"],
                options={"verify_signature": False, "verify_exp": True},
                leeway=-30,
            )
        except jwt.ExpiredSignatureError:
            return False
        return True

    async def _refresh_token(self) -> None:
        """Refresh the token."""
        async with self._lock:
            if self._is_token_valid():
                return
            if "Authorization" in self._headers:
                self._headers.pop("Authorization")
            resp = await self._request(
                "POST",
                "https://securetoken.googleapis.com/v1/token",
                params={"key": decode(AUTH_ENDPOINT_KEY)},
                json={
                    "grant_type": "refresh_token",
                    "refresh_token": self._token["refresh_token"],
                },
            )
            self._token["id_token"] = resp["id_token"]
            self._token["refresh_token"] = resp["refresh_token"]
            self._headers["Authorization"] = f"Bearer {self._token['id_token']}"
            if self._refresh_token_callback:
                try:
                    self._refresh_token_callback(self.token)
                except Exception as ex:
                    _LOGGER.error(ex)

    async def _request(
        self, method: str, url: str, **kwargs: Any
    ) -> dict | list[dict] | None:
        """Make a request."""
        if "google" not in url and not self._is_token_valid():
            await self._refresh_token()

        _LOGGER.debug("Making %s request to %s", method, url)

        async with self._client.request(
            method, url, headers=self._headers, **kwargs
        ) as resp:
            resp.raise_for_status()
            data = await resp.json()
            _LOGGER.debug("Received %s response from %s", resp.status, url)
            return data  # type: ignore
