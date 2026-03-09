from sqlalchemy import URL
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    __table_args__ = {'extend_existing': True}  # 允許重複定義時自動覆蓋
    def __repr__(self) -> str:
        keys = ", ".join(
            f"{column.key}={getattr(self, column.key)}"
            for column in self.__table__.columns
        )
        return f"{self.__class__.__name__}({keys})"


class Database:
    def __init__(self, database_name: str | None = None) -> None:
        # database_url = URL.create("sqlite+aiosqlite", database=database_name)
        database_url = "mysql+asyncmy://atural@localhost:3306/AturalBot"


        # 遷移到mysql後記得移除aiosqlite
        # if database_name is None:
        #     database_url = "sqlite+aiosqlite:///:memory:"
        # else:
        #     database_url = f"sqlite+aiosqlite:///{database_name}"

        self.engine = create_async_engine(database_url)
        self.session = async_sessionmaker(self.engine, expire_on_commit=False)

    async def initialise_database(self) -> None:
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
