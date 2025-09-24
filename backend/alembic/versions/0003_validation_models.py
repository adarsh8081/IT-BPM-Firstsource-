"""Create validation job and result models

Revision ID: 0003
Revises: 0002
Create Date: 2024-01-15 15:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0003'
down_revision = '0002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create validation_status enum
    validation_status = postgresql.ENUM('pending', 'in_progress', 'completed', 'failed', 'cancelled', name='validationstatus')
    validation_status.create(op.get_bind())
    
    # Create validation_jobs table
    op.create_table('validation_jobs',
        sa.Column('job_id', postgresql.UUID(as_uuid=True), nullable=False, comment='Unique job identifier'),
        sa.Column('provider_id', postgresql.UUID(as_uuid=True), nullable=True, comment='Provider being validated (null for batch jobs)'),
        sa.Column('job_type', sa.String(length=50), nullable=False, comment='Type of validation job (single, batch, bulk)'),
        sa.Column('status', validation_status, nullable=False, comment='Current job status'),
        sa.Column('priority', sa.String(length=20), nullable=False, comment='Job priority (low, normal, high, urgent)'),
        sa.Column('validation_config', postgresql.JSON(astext_type=sa.Text()), nullable=True, comment='JSON configuration for validation rules'),
        sa.Column('requested_validations', postgresql.JSON(astext_type=sa.Text()), nullable=True, comment='Array of validation types to perform'),
        sa.Column('progress_percentage', sa.Float(), nullable=True, comment='Job progress percentage (0-100)'),
        sa.Column('current_step', sa.String(length=100), nullable=True, comment='Current validation step'),
        sa.Column('total_steps', sa.String(length=100), nullable=True, comment='Total number of steps'),
        sa.Column('results_summary', postgresql.JSON(astext_type=sa.Text()), nullable=True, comment='Summary of validation results'),
        sa.Column('error_message', sa.Text(), nullable=True, comment='Error message if job failed'),
        sa.Column('started_at', sa.DateTime(), nullable=True, comment='Job start timestamp'),
        sa.Column('completed_at', sa.DateTime(), nullable=True, comment='Job completion timestamp'),
        sa.Column('created_by', sa.String(length=100), nullable=True, comment='User or system that created the job'),
        sa.Column('created_at', sa.DateTime(), nullable=False, comment='Job creation timestamp'),
        sa.Column('updated_at', sa.DateTime(), nullable=False, comment='Last update timestamp'),
        sa.ForeignKeyConstraint(['provider_id'], ['providers.provider_id'], ),
        sa.PrimaryKeyConstraint('job_id')
    )
    
    # Create validation_results table
    op.create_table('validation_results',
        sa.Column('result_id', postgresql.UUID(as_uuid=True), nullable=False, comment='Unique result identifier'),
        sa.Column('job_id', postgresql.UUID(as_uuid=True), nullable=False, comment='Associated validation job'),
        sa.Column('provider_id', postgresql.UUID(as_uuid=True), nullable=False, comment='Provider that was validated'),
        sa.Column('validation_type', sa.String(length=50), nullable=False, comment='Type of validation performed'),
        sa.Column('validation_source', sa.String(length=100), nullable=True, comment='Source of validation (NPI API, Google Places, etc.)'),
        sa.Column('field_name', sa.String(length=100), nullable=True, comment='Specific field that was validated'),
        sa.Column('is_valid', sa.String(length=10), nullable=False, comment='Validation result (valid, invalid, warning, error)'),
        sa.Column('confidence_score', sa.Float(), nullable=True, comment='Confidence score for this validation (0-1)'),
        sa.Column('raw_response', postgresql.JSON(astext_type=sa.Text()), nullable=True, comment='Raw response from validation source'),
        sa.Column('validation_details', postgresql.JSON(astext_type=sa.Text()), nullable=True, comment='Detailed validation information'),
        sa.Column('suggested_corrections', postgresql.JSON(astext_type=sa.Text()), nullable=True, comment='Suggested corrections if validation failed'),
        sa.Column('flags', postgresql.JSON(astext_type=sa.Text()), nullable=True, comment='Validation flags and warnings'),
        sa.Column('validation_duration_ms', sa.Float(), nullable=True, comment='Validation duration in milliseconds'),
        sa.Column('validated_at', sa.DateTime(), nullable=False, comment='Validation timestamp'),
        sa.ForeignKeyConstraint(['job_id'], ['validation_jobs.job_id'], ),
        sa.ForeignKeyConstraint(['provider_id'], ['providers.provider_id'], ),
        sa.PrimaryKeyConstraint('result_id')
    )
    
    # Create indexes for validation tables
    op.create_index('idx_validation_job_provider', 'validation_jobs', ['provider_id'])
    op.create_index('idx_validation_job_status', 'validation_jobs', ['status'])
    op.create_index('idx_validation_job_priority', 'validation_jobs', ['priority'])
    op.create_index('idx_validation_job_created', 'validation_jobs', ['created_at'])
    
    op.create_index('idx_validation_result_job', 'validation_results', ['job_id'])
    op.create_index('idx_validation_result_provider', 'validation_results', ['provider_id'])
    op.create_index('idx_validation_result_type', 'validation_results', ['validation_type'])
    op.create_index('idx_validation_result_valid', 'validation_results', ['is_valid'])
    op.create_index('idx_validation_result_confidence', 'validation_results', ['confidence_score'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('idx_validation_result_confidence', table_name='validation_results')
    op.drop_index('idx_validation_result_valid', table_name='validation_results')
    op.drop_index('idx_validation_result_type', table_name='validation_results')
    op.drop_index('idx_validation_result_provider', table_name='validation_results')
    op.drop_index('idx_validation_result_job', table_name='validation_results')
    
    op.drop_index('idx_validation_job_created', table_name='validation_jobs')
    op.drop_index('idx_validation_job_priority', table_name='validation_jobs')
    op.drop_index('idx_validation_job_status', table_name='validation_jobs')
    op.drop_index('idx_validation_job_provider', table_name='validation_jobs')
    
    # Drop tables
    op.drop_table('validation_results')
    op.drop_table('validation_jobs')
    
    # Drop enum
    validation_status = postgresql.ENUM(name='validationstatus')
    validation_status.drop(op.get_bind())
