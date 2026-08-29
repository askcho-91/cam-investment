from app.core.db_config import async_session
import asyncio
from dotenv import load_dotenv
from app.modules.users.services import create_user as user_create_user

load_dotenv()  # Load environment variables from .env file

user_data = {
    "email": "test@gmail.com",
    "first_name": "Test",
    "last_name": "User",
}


async def create_user():
    user = User(**user_data)
    async with async_session() as session:
        async with session.begin():
            session.add(user)
        await session.commit()


asyncio.run(create_user())