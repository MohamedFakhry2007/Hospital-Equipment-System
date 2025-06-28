"""Add OCM Equipment table

Revision ID: 1234567890ab
Revises: <previous_migration_id>
Create Date: 2025-06-27 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

# revision identifiers, used by Alembic.
revision = '1234567890ab'
down_revision = '34d25f5c0e1a'  # Points to the PPM equipment migration
branch_labels = None
depends_on = None

def upgrade():
    # Create the ocm_equipment table
    op.create_table('ocm_equipment',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('no', sa.Integer(), nullable=False),
        sa.Column('department', sa.String(length=100), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('model', sa.String(length=100), nullable=False),
        sa.Column('serial', sa.String(length=100), nullable=False, index=True, unique=True),
        sa.Column('manufacturer', sa.String(length=100), nullable=False),
        sa.Column('log_number', sa.String(length=50), nullable=False),
        sa.Column('installation_date', sa.Date(), nullable=True),
        sa.Column('warranty_end', sa.Date(), nullable=True),
        sa.Column('service_date', sa.Date(), nullable=True),
        sa.Column('engineer', sa.String(length=100), nullable=True),
        sa.Column('next_maintenance', sa.Date(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('(CURRENT_TIMESTAMP)')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('(CURRENT_TIMESTAMP)')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('serial', name='uq_ocm_equipment_serial')
    )

    # Create an index on the serial column for faster lookups
    op.create_index('ix_ocm_equipment_serial', 'ocm_equipment', ['serial'], unique=True)
    
    # Create an index on the status column for filtering
    op.create_index('ix_ocm_equipment_status', 'ocm_equipment', ['status'], unique=False)
    
    # Create an index on the department column for filtering
    op.create_index('ix_ocm_equipment_department', 'ocm_equipment', ['department'], unique=False)

def downgrade():
    # Drop the indexes first
    op.drop_index('ix_ocm_equipment_department', table_name='ocm_equipment')
    op.drop_index('ix_ocm_equipment_status', table_name='ocm_equipment')
    op.drop_index('ix_ocm_equipment_serial', table_name='ocm_equipment')
    
    # Drop the table
    op.drop_table('ocm_equipment')
