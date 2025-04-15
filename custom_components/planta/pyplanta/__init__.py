"""Planta API client."""

from asyncio import Lock
import logging
from typing import Any, Callable, Final

from aiohttp import ClientSession
import jwt

from .utils import UnauthorizedError

_LOGGER = logging.getLogger(__name__)

API_V1_ENDPOINT: Final = "https://public.planta-api.com/v1"


class Planta:
    """Planta API client class."""

    _lock = Lock()
    _token: dict[str, str] | None = None
    _refresh_token_callback: Callable[[dict[str, str]], None] | None = None

    def __init__(
        self,
        *,
        session: ClientSession | None = None,
        token: dict[str, str] | None = None,
        refresh_token_callback: Callable[[dict[str, str]], None] | None = None,
    ) -> None:
        """Initialize the client."""
        self._client = session if session else ClientSession()
        self._should_close = session is None
        self._headers: dict[str, str] = {}
        if token and "accessToken" in token:
            self._token = token
            self._headers["Authorization"] = f"Bearer {token['accessToken']}"
        if refresh_token_callback:
            self._refresh_token_callback = refresh_token_callback

    @property
    def token(self) -> dict[str, str] | None:
        """Return the token, if any."""
        return self._token

    async def authorize(self, code: str) -> None:
        """Exchange OTP for a token and refresh token."""
        result = await self._request(
            "POST", f"{API_V1_ENDPOINT}/auth/authorize", json={"code": code}
        )
        self._token = tokens = result["data"]
        self._headers["Authorization"] = (
            f"{tokens['tokenType']} {tokens['accessToken']}"
        )

    async def refresh_tokens(self) -> None:
        """Refresh the tokens."""
        if not self._token:
            raise UnauthorizedError("App has not yet been authorized.")
        async with self._lock:
            if self._is_token_valid():
                return
            if "Authorization" in self._headers:
                self._headers.pop("Authorization")
            result = await self._request(
                "POST",
                f"{API_V1_ENDPOINT}/auth/refreshToken",
                json={"refreshToken": self._token["refreshToken"]},
            )
            self._token = tokens = result["data"]
            self._headers["Authorization"] = (
                f"{tokens['tokenType']} {tokens['accessToken']}"
            )
            if self._refresh_token_callback:
                try:
                    self._refresh_token_callback(self.token)
                except Exception as ex:
                    _LOGGER.error(ex)

    async def close(self) -> None:
        """Close the client."""
        if self._should_close:
            await self._client.close()
            self._client = None

    async def get_plants(
        self, *, cursor: str | None = None, fetch_all: bool = True
    ) -> dict[str, list[dict[str, Any]] | str | None]:
        """Get plants.

        Args:
            cursor (str | None): The starting cursor for pagination. Default is None.
            fetch_all (bool): Whether to fetch all pages or just the first page. Defaults to True.

        Returns:
            dict: A dictionary containing plant data and optionally the next page cursor.
        """
        plants = []

        while True:
            result = await self._request(
                "GET",
                f"{API_V1_ENDPOINT}/addedPlants",
                **{"params": {"cursor": cursor} if cursor else {}},
            )

            plants.extend(result.get("data", []))
            cursor = result.get("pagination", {}).get("nextPage")

            if not fetch_all or not cursor:
                break

        return {
            "plants": plants,
            "cursor": cursor,
        }

    async def get_plant(self, plant_id: str) -> dict[str, Any]:
        """Get plant."""
        result = await self._request("GET", f"{API_V1_ENDPOINT}/addedPlants/{plant_id}")
        return result.get("data", {})

    async def plant_action_complete(self, plant_id: str, action_type: str) -> bool:
        """Mark a plant action as completed."""
        result = await self._request(
            "POST",
            f"{API_V1_ENDPOINT}/addedPlants/{plant_id}/actions/complete",
            json={"actionType": action_type},
        )
        return result == 204

    def _is_token_valid(self) -> bool:
        """Return `True` if the token is still valid."""
        if self.token is None:
            return False
        try:
            jwt.decode(
                self.token["accessToken"],
                options={"verify_signature": False, "verify_exp": True},
                leeway=-30,
            )
        except jwt.ExpiredSignatureError:
            return False
        return True

    async def _request(
        self, method: str, url: str, **kwargs: Any
    ) -> dict | list[dict] | int | None:
        """Make a request."""
        if "authorize" not in url and not self._is_token_valid():
            await self.refresh_tokens()

        _LOGGER.debug("Making %s request to %s", method, url)

        async with self._client.request(
            method, url, headers=self._headers, **kwargs
        ) as resp:
            resp.raise_for_status()
            if not resp.content_length:
                return resp.status
            data = await resp.json()
            _LOGGER.debug("Received %s response from %s", resp.status, url)
            return data  # type: ignore
