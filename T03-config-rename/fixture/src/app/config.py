"""Application configuration."""

PRODUCT_NAME = "Orion"
VERSION = "2.4.1"
SUPPORT_EMAIL = "support@stellarlabs.example"


def product_string():
    return f"{PRODUCT_NAME} v{VERSION}"
