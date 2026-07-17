"""Command-line interface for cofferdam (BR-CLI-*).

Provides three commands over a local policy file:

    cofferdam validate PATH
    cofferdam inspect  PATH
    cofferdam decide   PATH --integration ... --kind ... --operation ... \\
                            --method ... --url ... --credential ...

``validate`` exits non-zero on an invalid policy. ``inspect`` prints a redacted
summary. ``decide`` prints allow/deny and a reason code. No command ever prints a
secret value (BR-CLI-004). Uses the stdlib ``argparse`` to keep the core
dependency-free.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from cofferdam.config import load_policy
from cofferdam.decisions import decide
from cofferdam.errors import CofferdamError
from cofferdam.http import host_from_url

EXIT_OK = 0
EXIT_DENIED = 1
EXIT_INVALID = 2
EXIT_USAGE = 3


def _cmd_validate(args: argparse.Namespace) -> int:
    try:
        load_policy(args.path, strict=args.strict)
    except CofferdamError as exc:
        print(f"INVALID: {exc}", file=sys.stderr)
        for problem in getattr(exc, "problems", []) or []:
            print(f"  - {problem}", file=sys.stderr)
        return EXIT_INVALID
    print(f"OK: {args.path} is a valid policy")
    return EXIT_OK


def _cmd_inspect(args: argparse.Namespace) -> int:
    try:
        policy = load_policy(args.path)
    except CofferdamError as exc:
        print(f"INVALID: {exc}", file=sys.stderr)
        return EXIT_INVALID

    print(f"environment       : {policy.environment.value}")
    print(f"default_decision  : {policy.default_decision.value}")
    if policy.mail is not None:
        print(f"mail.mode         : {policy.mail.mode}")
    print(f"integrations      : {len(policy.integrations)}")
    for name, integ in sorted(policy.integrations.items()):
        state = "enabled" if integ.enabled else "disabled"
        hosts = ", ".join(integ.allowed_hosts) or "(none)"
        print(f"  - {name} [{integ.kind.value}, {state}] hosts: {hosts}")
    print(f"credentials       : {len(policy.credentials)}")
    for name, cred in sorted(policy.credentials.items()):
        # Redacted: show the source *name*, never a value (BR-CLI-004).
        source = f"env:{cred.secret_env}" if cred.secret_env else "raw:<redacted>"
        print(f"  - {name} [profile={cred.profile}, source={source}]")
    return EXIT_OK


def _cmd_decide(args: argparse.Namespace) -> int:
    try:
        policy = load_policy(args.path)
    except CofferdamError as exc:
        print(f"INVALID: {exc}", file=sys.stderr)
        return EXIT_INVALID

    host = host_from_url(args.url) if args.url else args.host
    decision = decide(
        policy,
        integration=args.integration,
        kind=args.kind,
        operation=args.operation,
        method=args.method,
        host=host,
        credential=args.credential,
    )
    verdict = "ALLOW" if decision.allowed else "DENY"
    print(f"{verdict}  reason={decision.reason_code}")
    if decision.detail:
        print(f"  detail: {decision.detail}")
    return EXIT_OK if decision.allowed else EXIT_DENIED


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cofferdam",
        description="Guard non-Production Frappe/ERPNext outbound side effects.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_validate = sub.add_parser("validate", help="validate a policy file")
    p_validate.add_argument("path")
    p_validate.add_argument(
        "--strict",
        action="store_true",
        help="also require secret_env vars to be set and reject raw secrets",
    )
    p_validate.set_defaults(func=_cmd_validate)

    p_inspect = sub.add_parser("inspect", help="print a redacted policy summary")
    p_inspect.add_argument("path")
    p_inspect.set_defaults(func=_cmd_inspect)

    p_decide = sub.add_parser("decide", help="simulate a policy decision")
    p_decide.add_argument("path")
    p_decide.add_argument("--integration", required=True)
    p_decide.add_argument("--kind")
    p_decide.add_argument("--operation")
    p_decide.add_argument("--method")
    p_decide.add_argument("--url", help="target URL; hostname is parsed structurally")
    p_decide.add_argument("--host", help="target hostname (alternative to --url)")
    p_decide.add_argument("--credential")
    p_decide.set_defaults(func=_cmd_decide)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except CofferdamError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return EXIT_INVALID


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
