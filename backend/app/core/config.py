"""Application settings loaded from environment variables."""

from __future__ import annotations

from typing import List
from urllib.parse import quote_plus

from pydantic import Field
from pydantic_settings import BaseSettings


EXAMPLE_JWT_SECRET = "replace-with-a-long-random-jwt-secret"
EXAMPLE_AES_ENCRYPTION_KEY = "ReplaceThisWith32ByteSecretKey!!"
EXAMPLE_ADMIN_PASSWORDS = {"Admin@123", "CHANGE_ME", "CHANGE_ME_NOW"}


class Settings(BaseSettings):
    APP_NAME: str = "RAG Backend API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    API_V1_PREFIX: str = "/api/v1"

    DB_HOST: str = "localhost"
    DB_PORT: int = 3306
    DB_USER: str = "rag_admin"
    DB_PASSWORD: str = "rag_jin"
    DB_NAME: str = "rag_system"

    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_RECYCLE: int = 3600

    @property
    def DATABASE_URL(self) -> str:
        encoded_password = quote_plus(self.DB_PASSWORD)
        return (
            f"mysql+pymysql://{self.DB_USER}:{encoded_password}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}?charset=utf8mb4"
        )

    @property
    def ASYNC_DATABASE_URL(self) -> str:
        encoded_password = quote_plus(self.DB_PASSWORD)
        return (
            f"mysql+aiomysql://{self.DB_USER}:{encoded_password}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}?charset=utf8mb4"
        )

    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: str = ""

    @property
    def REDIS_URL(self) -> str:
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    SESSION_CONTEXT_TTL: int = 7200
    SESSION_ACTIVE_TTL: int = 86400
    MAX_CONTEXT_TURNS: int = 10
    MAX_CONTEXT_TOKENS: int = 4000
    SESSION_ARCHIVE_DAYS: int = 7
    SESSION_DELETE_DAYS: int = 30

    ES_HOST: str = "http://localhost:9200"
    ES_INDEX_NAME: str = "rag_document_chunks"

    MILVUS_HOST: str = "localhost"
    MILVUS_PORT: int = 19530

    JWT_SECRET_KEY: str = Field(..., min_length=32)
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_HOURS: int = 24
    AES_ENCRYPTION_KEY: str = Field(..., min_length=32, max_length=32)

    FILE_STORAGE_PATH: str = "./data/files"
    MAX_FILE_SIZE: int = 52428800
    SKILL_INSTALL_ROOT: str = "./data/skills"
    ENABLE_REMOTE_SKILL_INSTALL: bool = False
    SKILL_REMOTE_ALLOWED_HOSTS: str = ""
    SKILL_REMOTE_REQUIRE_CHECKSUM: bool = True
    SKILL_REMOTE_REQUIRE_SIGNATURE: bool = False
    SKILL_REMOTE_MAX_PACKAGE_MB: int = 20
    SKILL_REMOTE_DOWNLOAD_TIMEOUT_SECONDS: int = 60
    SKILL_REMOTE_ED25519_PUBLIC_KEY: str = ""

    EMBEDDING_MODEL_PATH: str = "./models/Qwen/Qwen3-Embedding-0___6B"
    EMBEDDING_BATCH_SIZE: int = 32
    EMBEDDING_DEVICE: str = "auto"

    DEFAULT_CHUNK_SIZE: int = 500
    DEFAULT_CHUNK_OVERLAP: int = 50

    CORS_ORIGINS: str = "http://localhost:33004,http://127.0.0.1:33004,http://localhost:8080"
    CORS_ALLOW_CREDENTIALS: bool = True
    PUBLIC_BACKEND_URL: str = "http://localhost:38084"
    PUBLIC_FRONTEND_URL: str = "http://localhost:33004"

    @property
    def CORS_ORIGINS_LIST(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]

    @property
    def SKILL_REMOTE_ALLOWED_HOSTS_LIST(self) -> List[str]:
        return [host.strip().lower() for host in self.SKILL_REMOTE_ALLOWED_HOSTS.split(",") if host.strip()]

    USE_CELERY: bool = False
    CELERY_TASK_QUEUE: str = "rag_tasks"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/1"

    KAFKA_BOOTSTRAP_SERVERS: str = "localhost:9094"
    KAFKA_CONSUMER_GROUP: str = "rag_group"
    KAFKA_CONNECTION_MAX_RETRIES: int = 20
    KAFKA_CONNECTION_RETRY_BACKOFF_SEC: float = 3.0
    KAFKA_DEAD_LETTER_SUFFIX: str = ".dlq"

    INIT_DB_ON_STARTUP: bool = False
    CREATE_DEFAULT_ADMIN: bool = False
    DEFAULT_ADMIN_USERNAME: str = "admin"
    DEFAULT_ADMIN_EMAIL: str = "admin@example.com"
    DEFAULT_ADMIN_PASSWORD: str = "CHANGE_ME_NOW"

    def validate_startup_configuration(self) -> None:
        if self.JWT_SECRET_KEY == EXAMPLE_JWT_SECRET:
            raise ValueError("JWT_SECRET_KEY is still using the example value. Replace it with a strong random secret.")

        if self.AES_ENCRYPTION_KEY == EXAMPLE_AES_ENCRYPTION_KEY:
            raise ValueError("AES_ENCRYPTION_KEY is still using the example value. Replace it with a unique 32-byte key.")

        if not self.DEBUG and self.INIT_DB_ON_STARTUP:
            raise ValueError("INIT_DB_ON_STARTUP must stay disabled outside DEBUG environments.")

        if not self.DEBUG and self.CREATE_DEFAULT_ADMIN:
            raise ValueError("CREATE_DEFAULT_ADMIN must stay disabled outside DEBUG environments.")

        if self.CREATE_DEFAULT_ADMIN and self.DEFAULT_ADMIN_PASSWORD in EXAMPLE_ADMIN_PASSWORDS:
            raise ValueError("CREATE_DEFAULT_ADMIN is enabled, but DEFAULT_ADMIN_PASSWORD still uses a placeholder value.")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


settings = Settings()
