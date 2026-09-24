from getpass import getpass

from pydantic import ValidationError
from sqlmodel import Session, select

from app.database import create_db_and_tables, engine
from app.dtos.requests import UserCreateRequest
from app.enums import Role
from app.models import User
from app.security import hash_password


def create_admin(username, email, password):
    # Reuse UserCreateRequest so an admin obeys exactly the same rules as everyone else.
    details = UserCreateRequest(username=username, email=email, password=password)

    with Session(engine) as session:
        taken = session.exec(
            select(User).where((User.username == details.username) | (User.email == details.email))
        ).first()
        if taken:
            raise ValueError("A user with that username or email already exists")

        admin = User(
            username=details.username,
            email=details.email,
            hashed_password=hash_password(details.password),
            role=Role.admin,
        )
        session.add(admin)
        session.commit()
        session.refresh(admin)
        return admin


if __name__ == "__main__":
    create_db_and_tables()

    username = input("Admin username: ")
    email = input("Admin email: ")
    password = getpass("Admin password (nothing will show as you type): ")

    try:
        admin = create_admin(username, email, password)
    except ValidationError as error:  # must come BEFORE ValueError
        print("Could not create admin:")
        for problem in error.errors():
            print(f"  {problem['loc'][0]}: {problem['msg']}")
    except ValueError as error:
        print(f"Could not create admin: {error}")
    else:
        print(f"Created admin '{admin.username}' with id {admin.id}")
