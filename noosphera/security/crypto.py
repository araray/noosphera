from __future__ import annotations

import asyncio
import bcrypt


async def hash_secret(secret: str) -> str:
    """
    Bcrypt-hash a secret string. CPU-bound, so offload to a thread.
    """
    def _do() -> bytes:
        return bcrypt.hashpw(secret.encode("utf-8"), bcrypt.gensalt())

    hashed = await asyncio.to_thread(_do)
    return hashed.decode("utf-8")


async def verify_secret(secret: str, hashed: str) -> bool:
    def _do() -> bool:
        return bcrypt.checkpw(secret.encode("utf-8"), hashed.encode("utf-8"))

    return await asyncio.to_thread(_do)
