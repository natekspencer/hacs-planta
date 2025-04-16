"""Planta API client."""

from asyncio import Lock
import logging
from typing import Any, Callable, Final

from aiohttp import ClientSession
import jwt

from .exceptions import PlantaError, UnauthorizedError

_LOGGER = logging.getLogger(__name__)

API_V1_ENDPOINT: Final = "https://public.planta-api.com/v1"


class Planta:
    """Planta API client class."""

    _lock = Lock()
    _tokens: dict[str, str] | None = None
    _refresh_tokens_callback: Callable[[dict[str, str]], None] | None = None

    def __init__(
        self,
        *,
        session: ClientSession | None = None,
        tokens: dict[str, str] | None = None,
        refresh_tokens_callback: Callable[[dict[str, str]], None] | None = None,
    ) -> None:
        """Initialize the client."""
        self._client = session if session else ClientSession()
        self._should_close = session is None
        self._headers: dict[str, str] = {}
        if tokens and "accessToken" in tokens:
            self._tokens = tokens
            self._headers["Authorization"] = f"Bearer {tokens['accessToken']}"
        if refresh_tokens_callback:
            self._refresh_tokens_callback = refresh_tokens_callback

    @property
    def tokens(self) -> dict[str, str] | None:
        """Return the tokens, if any."""
        return self._tokens

    async def authorize(self, code: str) -> None:
        """Exchange OTP for an access and refresh token."""
        result = await self._request(
            "POST", f"{API_V1_ENDPOINT}/auth/authorize", json={"code": code}
        )
        self._tokens = tokens = result["data"]
        self._headers["Authorization"] = (
            f"{tokens['tokenType']} {tokens['accessToken']}"
        )

    async def refresh_tokens(self, *, force: bool = False) -> None:
        """Refresh the tokens."""
        if not self._tokens:
            raise UnauthorizedError("App has not yet been authorized")
        if "refreshToken" not in self._tokens:
            raise PlantaError("Unable to refresh tokens - refresh token is missing")
        async with self._lock:
            if not force and self._is_access_token_valid():
                return
            if "Authorization" in self._headers:
                self._headers.pop("Authorization")
            result = await self._request(
                "POST",
                f"{API_V1_ENDPOINT}/auth/refreshToken",
                json={"refreshToken": self._tokens["refreshToken"]},
            )
            self._tokens = tokens = result["data"]
            self._headers["Authorization"] = (
                f"{tokens['tokenType']} {tokens['accessToken']}"
            )
            if self._refresh_tokens_callback:
                try:
                    self._refresh_tokens_callback(self.tokens)
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

    def _is_access_token_valid(self) -> bool:
        """Return `True` if the access token is still valid."""
        if self.tokens is None:
            return False
        try:
            jwt.decode(
                self.tokens["accessToken"],
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
        if "authorize" not in url and not self._is_access_token_valid():
            await self.refresh_tokens()

        _LOGGER.debug("Making %s request to %s", method, url)

        async with self._client.request(
            method, url, headers=self._headers, **kwargs
        ) as resp:
            if "application/json" in resp.headers.get("Content-Type", ""):
                data = await resp.json()
            else:
                data = {"raw": await resp.text()}

            if resp.status >= 400:
                message = data.get("message", f"HTTP {resp.status} Error")
                error_type = data.get("errorType", "unknown")

                if resp.status == 401 or error_type == "unauthorized":
                    raise UnauthorizedError(message)
                else:
                    raise PlantaError(f"{error_type}: {message}")

            if not resp.content_length:
                return resp.status

            _LOGGER.debug("Received %s response from %s", resp.status, url)
            return data  # type: ignore
