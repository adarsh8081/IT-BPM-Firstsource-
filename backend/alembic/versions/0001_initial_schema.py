"""Initial schema

Revision ID: 0001
Revises: 
Create Date: 2024-01-15 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create providers table
    op.create_table('providers',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('npi', sa.String(length=10), nullable=False),
        sa.Column('first_name', sa.String(length=100), nullable=False),
        sa.Column('last_name', sa.String(length=100), nullable=False),
        sa.Column('middle_name', sa.String(length=100), nullable=True),
        sa.Column('suffix', sa.String(length=10), nullable=True),
        sa.Column('specialty', sa.String(length=200), nullable=True),
        sa.Column('organization', sa.String(length=200), nullable=True),
        sa.Column('organization_npi', sa.String(length=10), nullable=True),
        sa.Column('email', sa.String(length=255), nullable=True),
        sa.Column('phone', sa.String(length=20), nullable=True),
        sa.Column('address_line1', sa.String(length=255), nullable=True),
        sa.Column('address_line2', sa.String(length=255), nullable=True),
        sa.Column('city', sa.String(length=100), nullable=True),
        sa.Column('state', sa.String(length=2), nullable=True),
        sa.Column('zip_code', sa.String(length=10), nullable=True),
        sa.Column('country', sa.String(length=2), nullable=True),
        sa.Column('license_number', sa.String(length=50), nullable=True),
        sa.Column('license_state', sa.String(length=2), nullable=True),
        sa.Column('license_expiry', sa.DateTime(), nullable=True),
        sa.Column('status', sa.Enum('PENDING', 'VALID', 'INVALID', 'WARNING', name='providerstatus'), nullable=True),
        sa.Column('validation_score', sa.Float(), nullable=True),
        sa.Column('last_validated', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_providers_npi'), 'providers', ['npi'], unique=True)
    
    # Create validation_jobs table
    op.create_table('validation_jobs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('provider_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('priority', sa.Enum('LOW', 'MEDIUM', 'HIGH', name='validationjobpriority'), nullable=True),
        sa.Column('status', sa.Enum('PENDING', 'RUNNING', 'COMPLETED', 'FAILED', 'CANCELLED', name='validationjobstatus'), nullable=True),
        sa.Column('validate_npi', sa.Boolean(), nullable=True),
        sa.Column('validate_address', sa.Boolean(), nullable=True),
        sa.Column('validate_license', sa.Boolean(), nullable=True),
        sa.Column('progress', sa.Integer(), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('retry_count', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['provider_id'], ['providers.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_validation_jobs_provider_id'), 'validation_jobs', ['provider_id'], unique=False)
    
    # Create validation_results table
    op.create_table('validation_results',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('provider_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('job_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('npi_valid', sa.Boolean(), nullable=True),
        sa.Column('npi_details', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('address_valid', sa.Boolean(), nullable=True),
        sa.Column('address_details', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('address_suggestions', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('license_valid', sa.Boolean(), nullable=True),
        sa.Column('license_details', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('overall_score', sa.Float(), nullable=True),
        sa.Column('validation_summary', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('errors', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('warnings', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['provider_id'], ['providers.id'], ),
        sa.ForeignKeyConstraint(['job_id'], ['validation_jobs.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_validation_results_provider_id'), 'validation_results', ['provider_id'], unique=False)
    op.create_index(op.f('ix_validation_results_job_id'), 'validation_results', ['job_id'], unique=False)


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_index(op.f('ix_validation_results_job_id'), table_name='validation_results')
    op.drop_index(op.f('ix_validation_results_provider_id'), table_name='validation_results')
    op.drop_table('validation_results')
    op.drop_index(op.f('ix_validation_jobs_provider_id'), table_name='validation_jobs')
    op.drop_table('validation_jobs')
    op.drop_index(op.f('ix_providers_npi'), table_name='providers')
    op.drop_table('providers')
    
    # Drop enums
    op.execute('DROP TYPE IF EXISTS validationjobstatus')
    op.execute('DROP TYPE IF EXISTS validationjobpriority')
    op.execute('DROP TYPE IF EXISTS providerstatus')
