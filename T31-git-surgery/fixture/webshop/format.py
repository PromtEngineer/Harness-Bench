"""Display formatting."""


def cents_to_str(cents):
    return f"{cents // 100}.{cents % 100:02d}"
