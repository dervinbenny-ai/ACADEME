"""Add staff phone numbers to user accounts.

Revision ID: 20261012_user_phone
Revises: 20261011_role_accounts
Create Date: 2026-10-12
"""
from alembic import op
import sqlalchemy as sa


revision = '20261012_user_phone'
down_revision = '20261011_role_accounts'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('users', sa.Column('phone', sa.String(length=16), nullable=True))


def downgrade():
    op.drop_column('users', 'phone')
