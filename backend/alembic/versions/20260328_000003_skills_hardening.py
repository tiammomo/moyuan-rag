"""skills hardening schema

Revision ID: 20260328_000003
Revises: 20260327_000002
Create Date: 2026-03-28 00:00:03
"""

from __future__ import annotations

from alembic import op


revision = "20260328_000003"
down_revision = "20260327_000002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS rag_skill_install_task (
            id BIGINT NOT NULL AUTO_INCREMENT,
            source_type VARCHAR(20) NOT NULL DEFAULT 'local',
            package_name VARCHAR(255) NULL,
            package_url VARCHAR(500) NULL,
            package_checksum VARCHAR(128) NULL,
            package_signature TEXT NULL,
            signature_algorithm VARCHAR(50) NULL,
            requested_by_user_id BIGINT NULL,
            requested_by_username VARCHAR(50) NULL,
            status VARCHAR(20) NOT NULL DEFAULT 'pending',
            installed_skill_slug VARCHAR(100) NULL,
            installed_skill_version VARCHAR(50) NULL,
            error_message TEXT NULL,
            details JSON NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            finished_at DATETIME NULL,
            PRIMARY KEY (id),
            KEY idx_skill_install_task_user (requested_by_user_id),
            KEY idx_skill_install_task_status (status),
            KEY idx_skill_install_task_slug (installed_skill_slug)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS rag_skill_audit_log (
            id BIGINT NOT NULL AUTO_INCREMENT,
            action VARCHAR(50) NOT NULL,
            target_type VARCHAR(50) NOT NULL,
            status VARCHAR(20) NOT NULL DEFAULT 'success',
            actor_user_id BIGINT NULL,
            actor_username VARCHAR(50) NULL,
            actor_role VARCHAR(20) NULL,
            robot_id BIGINT NULL,
            skill_slug VARCHAR(100) NULL,
            skill_version VARCHAR(50) NULL,
            install_task_id BIGINT NULL,
            message TEXT NULL,
            details JSON NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (id),
            KEY idx_skill_audit_action (action),
            KEY idx_skill_audit_status (status),
            KEY idx_skill_audit_user (actor_user_id),
            KEY idx_skill_audit_robot (robot_id),
            KEY idx_skill_audit_slug (skill_slug),
            KEY idx_skill_audit_task (install_task_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS rag_skill_audit_log")
    op.execute("DROP TABLE IF EXISTS rag_skill_install_task")
