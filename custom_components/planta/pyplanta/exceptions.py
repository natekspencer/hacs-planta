"""Planta exceptions."""


class PlantaError(Exception):
    """Generic Planta error."""


class UnauthorizedError(PlantaError):
    """Unauthorized error."""
