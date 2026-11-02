"""Load local configuration only at CLI entry points, never while importing tests."""
from pathlib import Path

from dotenv import load_dotenv


def load_environment():
    # Preserve environment variables supplied by Render or the calling process.
    # Disable interpolation so passwords and Argon2 hashes remain literal.
    return load_dotenv(Path(__file__).resolve().parent / '.env',
                       override=False, interpolate=False)
