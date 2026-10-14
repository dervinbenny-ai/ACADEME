"""Add role-specific account tables.

Revision ID: 20261011_role_accounts
Revises: 20260929_workflows
Create Date: 2026-10-11
"""
from alembic import op
import sqlalchemy as sa


revision = '20261011_role_accounts'
down_revision = '20260929_workflows'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'admin_accounts',
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('user_id'),
    )
    op.create_table(
        'teacher_accounts',
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('user_id'),
    )
    connection = op.get_bind()
    connection.execute(sa.text(
        "INSERT INTO admin_accounts (user_id, created_at) "
        "SELECT users.id, users.created_at FROM users "
        "JOIN roles ON roles.id = users.role_id "
        "WHERE roles.name IN ('ADMIN', 'SUPER_ADMIN')"
    ))
    connection.execute(sa.text(
        "INSERT INTO teacher_accounts (user_id, created_at) "
        "SELECT users.id, users.created_at FROM users "
        "JOIN roles ON roles.id = users.role_id WHERE roles.name = 'TEACHER'"
    ))


def downgrade():
    op.drop_table('teacher_accounts')
    op.drop_table('admin_accounts')