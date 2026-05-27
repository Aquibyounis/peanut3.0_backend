"""
Resource ownership verification helpers for user-isolation.
"""

from fastapi import HTTPException, status


def verify_resource_ownership(user_id: str, resource_user_id: str) -> bool:
    """Return ``True`` if *user_id* matches *resource_user_id*."""
    return str(user_id) == str(resource_user_id)


def raise_if_not_owner(user_id: str, resource_user_id: str) -> None:
    """
    Raise a 403 Forbidden if the authenticated user is not the resource owner.
    """
    if not verify_resource_ownership(user_id, resource_user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this resource.",
        )
