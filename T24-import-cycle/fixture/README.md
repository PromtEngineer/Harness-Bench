# flowkit

Text pipeline framework. Public API (frozen):

    from flowkit import Pipeline, Step, build, get_registry, register

KNOWN ISSUE: `import flowkit` currently fails with an ImportError after
the serializers module was added for the audit-export feature. The
package needs untangling; docs/CLI.md describes the CLI that has to ship
on top of it.
