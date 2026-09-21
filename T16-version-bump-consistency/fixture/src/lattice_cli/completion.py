"""Shell completion generator."""

BASH_TEMPLATE = "complete -W 'status sync prune' lattice"


def generate(shell):
    if shell == "bash":
        return BASH_TEMPLATE
    raise ValueError("unsupported shell: %s" % shell)
