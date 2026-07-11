"""Generate a VAPID keypair for web push.

Run once, then set the printed values in the runtime .env:
    python scripts/generate_vapid_keys.py
"""

import base64

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def main() -> None:
    key = ec.generate_private_key(ec.SECP256R1())
    private_raw = key.private_numbers().private_value.to_bytes(32, "big")
    public_raw = key.public_key().public_bytes(
        serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint
    )
    print("VAPID_PRIVATE_KEY=" + _b64url(private_raw))
    print("VAPID_PUBLIC_KEY=" + _b64url(public_raw))


if __name__ == "__main__":
    main()
