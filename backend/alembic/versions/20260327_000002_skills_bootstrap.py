"""skills bootstrap schema

Revision ID: 20260327_000002
Revises: 20260325_000001
Create Date: 2026-03-27 00:00:02
"""

from __future__ import annotations

from alembic import op


revision = "20260327_000002"
down_revision = "20260325_000001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS rag_robot_skill_binding (
            id BIGINT NOT NULL AUTO_INCREMENT,
            robot_id BIGINT NOT NULL,
            skill_slug VARCHAR(100) NOT NULL,
            skill_version VARCHAR(50) NOT NULL,
            binding_config JSON NULL,
            priority INTEGER NOT NULL DEFAULT 100,
            status VARCHAR(20) NOT NULL DEFAULT 'active',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (id),
            CONSTRAINT uk_robot_skill UNIQUE (robot_id, skill_slug),
            KEY idx_robot_skill_robot (robot_id),
            KEY idx_robot_skill_slug (skill_slug)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS rag_robot_skill_binding")
