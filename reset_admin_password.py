from getpass import getpass
import re

from pwdlib import PasswordHash
from backend.database.connection import get_connection


ADMIN_USER_ID = 4
password_hash = PasswordHash.recommended()


def validate_password(password):
    if not 8 <= len(password) <= 128:
        raise ValueError("Password must contain 8–128 characters.")
    if not re.search(r"[a-z]", password):
        raise ValueError("Password needs a lowercase letter.")
    if not re.search(r"[A-Z]", password):
        raise ValueError("Password needs an uppercase letter.")
    if not re.search(r"\d", password):
        raise ValueError("Password needs a digit.")
    if not re.search(r"[^A-Za-z0-9]", password):
        raise ValueError("Password needs a special character.")


def main():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT u.username, u.email,
                       EXISTS (
                           SELECT 1
                           FROM user_roles ur
                           JOIN roles r ON r.role_id = ur.role_id
                           WHERE ur.user_id = u.user_id
                             AND LOWER(r.name) = 'admin'
                       ) AS is_admin
                FROM users u
                WHERE u.user_id = %s
                FOR UPDATE;
                """,
                (ADMIN_USER_ID,),
            )
            user = cur.fetchone()

            if not user:
                raise RuntimeError("Admin user ID 4 was not found.")

            username, email, is_admin = user

            if not is_admin:
                raise RuntimeError(
                    "User ID 4 does not have the admin role. "
                    "No changes were made."
                )

            print(f"Account: {username}")
            print(f"Email: {email}")
            print("Admin role verified.")

            new_password = getpass("Enter a new admin password: ")
            confirm_password = getpass("Confirm the new password: ")

            if new_password != confirm_password:
                raise ValueError("Passwords do not match.")

            validate_password(new_password)
            new_hash = password_hash.hash(new_password)

            cur.execute(
                """
                UPDATE users
                SET password_hash = %s
                WHERE user_id = %s;
                """,
                (new_hash, ADMIN_USER_ID),
            )

            cur.execute(
                """
                UPDATE user_sessions
                SET revoked_at = CURRENT_TIMESTAMP
                WHERE user_id = %s
                  AND revoked_at IS NULL;
                """,
                (ADMIN_USER_ID,),
            )

    print("Admin password reset successfully.")
    print("Existing sessions for this admin account were revoked.")
    print("Log in again with the verified username and new password.")


if __name__ == "__main__":
    main()
