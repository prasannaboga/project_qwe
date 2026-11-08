"""Business logic and credential validation for authentication demo following OOP and SOLID principles.

Provides AuthDemoService which encapsulates loading users from CSV storage
and authenticating credentials using constant-time comparisons (`secrets.compare_digest`)
to protect against timing side-channel attacks.
"""

from dataclasses import dataclass
from pathlib import Path
import csv
import hashlib
import secrets

from project_qwe.schemas.auth_demo import UserProfile

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_USERS_FILE = PROJECT_ROOT / "data" / "demo_users_details.csv"


@dataclass(frozen=True)
class DemoUser:
    """Immutable demo user record loaded from CSV storage."""

    id: int
    username: str
    email: str
    password_hash: str
    role: str
    access_token: str
    api_key: str


class AuthDemoService:
    """Service handling credential verification and authentication against demo user data. 
    """

    def __init__(self, users_file: str | Path | None = None) -> None:
        if users_file is None:
            self._users_file = DEFAULT_USERS_FILE
        else:
            path = Path(users_file)
            self._users_file = path if path.is_absolute() else PROJECT_ROOT / path

        self._users: list[DemoUser] = []
        self.load_users()

    @property
    def users_file(self) -> Path:
        """Return the resolved path to the demo users CSV file."""
        return self._users_file

    @property
    def users(self) -> list[DemoUser]:
        """Return the loaded demo users."""
        return list(self._users)

    def load_users(self) -> None:
        """Load and parse demo users from the configured CSV file."""
        users: list[DemoUser] = []
        if not self._users_file.exists():
            self._users = []
            return

        with open(self._users_file, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    user = DemoUser(
                        id=int(row["id"].strip()),
                        username=row["username"].strip(),
                        email=row["email"].strip(),
                        password_hash=row["password_hash"].strip(),
                        role=row["role"].strip(),
                        access_token=row["access_token"].strip(),
                        api_key=row["api_key"].strip(),
                    )
                    users.append(user)
                except (KeyError, ValueError):
                    continue

        self._users = users

    def authenticate_bearer_token(self, token: str) -> UserProfile | None:
        """Validate a Bearer token against loaded demo users.

        Returns:
            UserProfile if token matches any user's access_token, None otherwise.
        """
        if not token:
            return None

        for user in self._users:
            if secrets.compare_digest(token, user.access_token):
                return UserProfile(
                    username=user.username,
                    email=user.email,
                    auth_method="bearer",
                    role=user.role,
                )
        return None

    def authenticate_api_key(self, api_key: str) -> UserProfile | None:
        """Validate an API key against loaded demo users.

        Returns:
            UserProfile if api_key matches any user's api_key, None otherwise.
        """
        if not api_key:
            return None

        for user in self._users:
            if secrets.compare_digest(api_key, user.api_key):
                return UserProfile(
                    username=user.username,
                    email=user.email,
                    auth_method="api_key",
                    role=user.role,
                )
        return None

    def authenticate_basic_credentials(
        self, username: str, password: str
    ) -> UserProfile | None:
        """Validate HTTP Basic credentials against loaded demo users.

        Compares username and checks password either as a plain password
        (hashing with SHA-256 for comparison) or matching precomputed hash.

        Returns:
            UserProfile if username and password match, None otherwise.
        """
        if not username or not password:
            return None

        computed_hash = hashlib.sha256(password.encode("utf-8")).hexdigest()

        for user in self._users:
            if secrets.compare_digest(username, user.username):
                password_valid = secrets.compare_digest(
                    computed_hash, user.password_hash
                ) or secrets.compare_digest(password, user.password_hash)

                if password_valid:
                    return UserProfile(
                        username=user.username,
                        email=user.email,
                        auth_method="basic",
                        role=user.role,
                    )
        return None


# Default service instance configured with default users CSV file
auth_demo_service = AuthDemoService()

# Module-level aliases for backwards compatibility
authenticate_bearer_token = auth_demo_service.authenticate_bearer_token
authenticate_api_key = auth_demo_service.authenticate_api_key
authenticate_basic_credentials = auth_demo_service.authenticate_basic_credentials
