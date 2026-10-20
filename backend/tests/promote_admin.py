from sqlalchemy import select

from app.database import SessionLocal
from app.models import User


def main():
    email = input(
        "Enter the email of the existing account to promote: "
    ).strip().lower()

    if not email:
        print("Email is required.")
        return

    confirmation = input(
        f"Promote {email} to administrator? Type YES to confirm: "
    ).strip()

    if confirmation != "YES":
        print("Cancelled.")
        return

    with SessionLocal() as db:
        user = db.scalar(
            select(User).where(User.email == email)
        )

        if user is None:
            print("Account not found. Register the account first.")
            return

        if user.is_admin:
            print("This account is already an administrator.")
            return

        user.is_admin = True
        db.commit()

        print(f"Administrator access enabled for {user.email}.")


if __name__ == "__main__":
    main()
