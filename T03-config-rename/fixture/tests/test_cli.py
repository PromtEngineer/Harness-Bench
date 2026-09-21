from app import cli
from app.config import PRODUCT_NAME


def test_product_name():
    assert PRODUCT_NAME == "Nova"


def test_banner():
    assert cli.banner() == "Nova v2.4.1 — Nova command-line interface"


def test_description_mentions_product():
    assert cli.DESCRIPTION == "Nova command-line interface"
