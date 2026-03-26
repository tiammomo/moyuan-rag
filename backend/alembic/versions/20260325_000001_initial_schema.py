"""initial schema

Revision ID: 20260325_000001
Revises:
Create Date: 2026-03-25 00:00:01
"""

from __future__ import annotations

from alembic import op


revision = "20260325_000001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS rag_user (
            id BIGINT NOT NULL AUTO_INCREMENT,
            username VARCHAR(50) NOT NULL,
            email VARCHAR(100) NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            avatar_url VARCHAR(255) NULL,
            role VARCHAR(20) NOT NULL DEFAULT 'user',
            status INTEGER NOT NULL DEFAULT 1,
            password_changed_at DATETIME NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (id),
            UNIQUE KEY uq_rag_user_username (username),
            UNIQUE KEY uq_rag_user_email (email),
            KEY ix_rag_user_username (username),
            KEY ix_rag_user_email (email)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS rag_llm (
            id BIGINT NOT NULL AUTO_INCREMENT,
            user_id BIGINT NOT NULL,
            name VARCHAR(100) NOT NULL,
            model_type VARCHAR(20) NOT NULL,
            provider VARCHAR(50) NOT NULL,
            model_name VARCHAR(100) NOT NULL,
            base_url VARCHAR(255) NULL,
            api_version VARCHAR(50) NULL,
            max_tokens INTEGER DEFAULT 4096,
            description VARCHAR(1000) NULL,
            status INTEGER DEFAULT 1,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS rag_apikey (
            id BIGINT NOT NULL AUTO_INCREMENT,
            user_id BIGINT NOT NULL,
            llm_id BIGINT NOT NULL,
            alias VARCHAR(100) NOT NULL,
            api_key_encrypted TEXT NOT NULL,
            description VARCHAR(500) NULL,
            status INTEGER DEFAULT 1,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (id),
            KEY idx_apikey_llm (llm_id),
            KEY idx_apikey_user (user_id),
            KEY ix_rag_apikey_llm_id (llm_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS rag_knowledge (
            id BIGINT NOT NULL AUTO_INCREMENT,
            user_id BIGINT NOT NULL,
            name VARCHAR(100) NOT NULL,
            description VARCHAR(500) NULL,
            avatar VARCHAR(255) NULL,
            embed_llm_id BIGINT NOT NULL,
            vector_collection_name VARCHAR(100) NOT NULL,
            chunk_size INTEGER DEFAULT 500,
            chunk_overlap INTEGER DEFAULT 50,
            document_count INTEGER DEFAULT 0,
            total_chunks INTEGER DEFAULT 0,
            status INTEGER DEFAULT 1,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (id),
            KEY idx_user (user_id),
            KEY ix_rag_knowledge_user_id (user_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS rag_document (
            id BIGINT NOT NULL AUTO_INCREMENT,
            knowledge_id BIGINT NOT NULL,
            file_name VARCHAR(255) NOT NULL,
            file_path VARCHAR(500) NOT NULL,
            file_extension VARCHAR(20) NOT NULL,
            file_size BIGINT DEFAULT 0,
            mime_type VARCHAR(100) NULL,
            width INTEGER NULL,
            height INTEGER NULL,
            status VARCHAR(20) DEFAULT 'uploading',
            chunk_count INTEGER DEFAULT 0,
            error_msg TEXT NULL,
            meta_data JSON NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (id),
            KEY idx_knowledge (knowledge_id),
            KEY ix_rag_document_knowledge_id (knowledge_id),
            KEY idx_status (status)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS rag_robot (
            id BIGINT NOT NULL AUTO_INCREMENT,
            user_id BIGINT NOT NULL,
            name VARCHAR(100) NOT NULL,
            avatar VARCHAR(255) NULL,
            chat_llm_id BIGINT NOT NULL,
            rerank_llm_id BIGINT NULL,
            description VARCHAR(500) NULL,
            system_prompt TEXT NULL,
            welcome_msg VARCHAR(500) NULL,
            suggested_questions JSON NULL,
            similarity_threshold FLOAT DEFAULT 0.6,
            top_k INTEGER DEFAULT 5,
            enable_rerank BOOLEAN DEFAULT FALSE,
            temperature FLOAT DEFAULT 0.7,
            max_tokens INTEGER DEFAULT 2000,
            status INTEGER DEFAULT 1,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (id),
            KEY idx_user (user_id),
            KEY ix_rag_robot_user_id (user_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS rag_robot_knowledge (
            id BIGINT NOT NULL AUTO_INCREMENT,
            robot_id BIGINT NOT NULL,
            knowledge_id BIGINT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (id),
            CONSTRAINT uk_robot_kb UNIQUE (robot_id, knowledge_id),
            KEY idx_kb (knowledge_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS rag_session (
            id BIGINT NOT NULL AUTO_INCREMENT,
            session_id VARCHAR(64) NOT NULL,
            user_id BIGINT NOT NULL,
            robot_id BIGINT NOT NULL,
            title VARCHAR(200) NULL,
            summary VARCHAR(500) NULL,
            message_count INTEGER NOT NULL DEFAULT 0,
            status VARCHAR(20) NOT NULL DEFAULT 'active',
            is_pinned INTEGER NOT NULL DEFAULT 0,
            last_message_at DATETIME NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            meta_data JSON NULL,
            PRIMARY KEY (id),
            UNIQUE KEY uq_rag_session_session_id (session_id),
            KEY ix_rag_session_session_id (session_id),
            KEY ix_rag_session_user_id (user_id),
            KEY ix_rag_session_robot_id (robot_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS rag_chat_history (
            id BIGINT NOT NULL AUTO_INCREMENT,
            session_id VARCHAR(64) NOT NULL,
            message_id VARCHAR(64) NOT NULL,
            role VARCHAR(20) NOT NULL,
            content TEXT NOT NULL,
            retrieved_contexts JSON NULL,
            referenced_doc_ids JSON NULL,
            prompt_tokens INTEGER NOT NULL DEFAULT 0,
            completion_tokens INTEGER NOT NULL DEFAULT 0,
            total_tokens INTEGER NOT NULL DEFAULT 0,
            retrieval_time_ms INTEGER NOT NULL DEFAULT 0,
            generation_time_ms INTEGER NOT NULL DEFAULT 0,
            total_time_ms INTEGER NOT NULL DEFAULT 0,
            feedback INTEGER NULL,
            feedback_comment VARCHAR(500) NULL,
            sequence INTEGER NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            meta_data JSON NULL,
            PRIMARY KEY (id),
            UNIQUE KEY uq_rag_chat_history_message_id (message_id),
            KEY ix_rag_chat_history_session_id (session_id),
            KEY ix_rag_chat_history_message_id (message_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS rag_chat_history")
    op.execute("DROP TABLE IF EXISTS rag_session")
    op.execute("DROP TABLE IF EXISTS rag_robot_knowledge")
    op.execute("DROP TABLE IF EXISTS rag_robot")
    op.execute("DROP TABLE IF EXISTS rag_document")
    op.execute("DROP TABLE IF EXISTS rag_knowledge")
    op.execute("DROP TABLE IF EXISTS rag_apikey")
    op.execute("DROP TABLE IF EXISTS rag_llm")
    op.execute("DROP TABLE IF EXISTS rag_user")
