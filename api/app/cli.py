"""Server-side admin commands.

Bootstrap the first parent account (decision #6):

    uv run python -m app.cli create-parent --email you@example.com --name "Parent"

Prompts for the password (or pass --password for scripted setups).

Load the starter routine templates (School Day / Home Day) for a child:

    uv run python -m app.cli seed-starter

Uses the only child if exactly one exists; otherwise pass --child-id.
"""

import argparse
import asyncio
import getpass
import sys

from sqlalchemy import select
from sqlalchemy.exc import OperationalError

from app import models
from app.db import async_session
from app.security import hash_password
from app.seed import seed_starter_templates


async def _create_parent(email: str, display_name: str, password: str) -> str:
    async with async_session() as db:
        try:
            existing = await db.execute(select(models.User).where(models.User.email == email))
        except OperationalError as exc:
            raise SystemExit(
                f"error: database not ready ({exc.orig}); run `make migrate` first"
            ) from exc
        if existing.scalar_one_or_none() is not None:
            raise SystemExit(f"error: a user with email {email} already exists")
        user = models.User(
            email=email,
            password_hash=hash_password(password),
            display_name=display_name,
            role="parent",
        )
        db.add(user)
        await db.commit()
        return user.id


async def _seed_starter(child_id: str | None) -> list[str]:
    async with async_session() as db:
        if child_id is None:
            result = await db.execute(select(models.Child.id))
            child_ids = list(result.scalars())
            if len(child_ids) != 1:
                raise SystemExit(
                    f"error: found {len(child_ids)} children; pass --child-id explicitly"
                )
            child_id = child_ids[0]
        try:
            return await seed_starter_templates(db, child_id)
        except ValueError as exc:
            raise SystemExit(f"error: {exc}") from exc


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="app.cli")
    sub = parser.add_subparsers(dest="command", required=True)

    create = sub.add_parser("create-parent", help="Create a parent account")
    create.add_argument("--email", required=True)
    create.add_argument("--name", required=True, dest="display_name")
    create.add_argument("--password", help="omit to be prompted")

    seed = sub.add_parser("seed-starter", help="Load starter routine templates for a child")
    seed.add_argument("--child-id", help="defaults to the only child, if exactly one exists")

    args = parser.parse_args(argv)
    if args.command == "create-parent":
        password = args.password or getpass.getpass("Password (min 8 chars): ")
        if len(password) < 8:
            raise SystemExit("error: password must be at least 8 characters")
        user_id = asyncio.run(_create_parent(args.email.lower(), args.display_name, password))
        print(f"created parent account {user_id}", file=sys.stderr)
    elif args.command == "seed-starter":
        created = asyncio.run(_seed_starter(args.child_id))
        if created:
            print(f"created templates: {', '.join(created)}", file=sys.stderr)
        else:
            print("starter templates already present; nothing created", file=sys.stderr)


if __name__ == "__main__":
    main()
