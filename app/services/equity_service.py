# app/services/equity_service.py
"""
Equity Distribution Service

Manages automatic equity distribution when tasks are completed,
validates equity constraints, and provides equity tracking utilities.
"""

from datetime import datetime, timezone
from flask import current_app
from ..extensions import db
from ..models import ProjectEquity, Project, Task, Solution, Collaborator, EquityHistory


class EquityService:
    """Service for managing project equity distribution"""
    
    @staticmethod
    def _log_equity_change(project_id, user_id, action, equity_change, equity_before, equity_after, 
                          reason, source_type, source_id=None, changed_by_user_id=None):
        """
        Internal method to log equity changes to audit log.
        
        Args:
            project_id: Project ID
            user_id: User receiving equity change
            action: Type of action ('grant', 'revoke', 'transfer', 'adjust', 'initial')
            equity_change: Amount of equity changed (positive or negative)
            equity_before: Equity before change
            equity_after: Equity after change
            reason: Human-readable reason
            source_type: Type of source ('task_completion', 'manual', 'bonus', 'initial')
            source_id: ID of related entity (optional)
            changed_by_user_id: User who made the change (optional, for manual changes)
        """
        history_entry = EquityHistory(
            project_id=project_id,
            user_id=user_id,
            action=action,
            equity_change=equity_change,
            equity_before=equity_before,
            equity_after=equity_after,
            reason=reason,
            source_type=source_type,
            source_id=source_id,
            changed_by_user_id=changed_by_user_id
        )
        
        db.session.add(history_entry)
        
        current_app.logger.info(
            f'Equity change logged: {action} {equity_change}% for user {user_id} in project {project_id} (source: {source_type})'
        )
    
    @staticmethod
    def initialize_creator_equity(project):
        """
        Initialize equity for project creator.
        Called when a new project is created.
        
        Args:
            project: Project instance
            
        Returns:
            ProjectEquity: Creator's equity record
        """
        # Check if creator already has equity
        existing = ProjectEquity.query.filter_by(
            project_id=project.id,
            user_id=project.creator_id
        ).first()
        
        if existing:
            current_app.logger.warning(
                f'Creator equity already exists for project {project.id}'
            )
            return existing
        
        # 🎯 USE THE CREATOR_EQUITY VALUE SET BY THE CREATOR AT PROJECT CREATION
        # The creator decides this percentage when creating the project (stored in project.creator_equity)
        # Default is 5.0% if not specified, but can be any value from 0-100%
        initial_equity = project.creator_equity if project.creator_equity is not None else 5.0
        
        # Create equity record
        creator_equity = ProjectEquity(
            project_id=project.id,
            user_id=project.creator_id,
            equity_percentage=initial_equity,
            earned_from='creator'
        )
        
        db.session.add(creator_equity)
        
        # 📊 LOG TO EQUITY HISTORY
        EquityService._log_equity_change(
            project_id=project.id,
            user_id=project.creator_id,
            action='initial',
            equity_change=initial_equity,
            equity_before=0.0,
            equity_after=initial_equity,
            reason=f'Initial creator allocation for project {project.name}',
            source_type='initial',
            source_id=None,
            changed_by_user_id=project.creator_id
        )
        
        db.session.commit()
        
        current_app.logger.info(
            f'Initialized creator equity: {initial_equity}% for user {project.creator_id} in project {project.id}'
        )
        
        return creator_equity
    
    @staticmethod
    def distribute_task_completion_equity(solution):
        """
        Distribute equity when a task solution is approved.
        
        Args:
            solution: Solution instance (must be approved)
            
        Returns:
            ProjectEquity: Updated equity record, or None if no equity distributed
            
        Raises:
            ValueError: If equity cannot be distributed (insufficient available)
        """
        task = solution.task
        project = task.project
        solver_id = solution.submitted_by_user_id
        
        # Get equity reward from task
        equity_reward = task.equity_reward
        
        if equity_reward <= 0:
            current_app.logger.info(
                f'Task {task.id} has no equity reward, skipping distribution'
            )
            return None
        
        # Validate available equity
        if not project.can_distribute_equity(equity_reward):
            available = project.get_available_equity()
            raise ValueError(
                f'Cannot distribute {equity_reward}% equity. Only {available}% available.'
            )
        
        # Get or create solver's equity record
        solver_equity = ProjectEquity.query.filter_by(
            project_id=project.id,
            user_id=solver_id
        ).first()
        
        equity_before = 0.0
        if not solver_equity:
            solver_equity = ProjectEquity(
                project_id=project.id,
                user_id=solver_id,
                equity_percentage=0.0,
                earned_from=''
            )
            db.session.add(solver_equity)
        else:
            equity_before = solver_equity.equity_percentage
        
        # Distribute equity
        solver_equity.equity_percentage += equity_reward
        equity_after = solver_equity.equity_percentage
        
        # Track source of equity
        source = f'task_{task.id}'
        if solver_equity.earned_from:
            solver_equity.earned_from += f',{source}'
        else:
            solver_equity.earned_from = source
        
        solver_equity.last_updated = datetime.now(timezone.utc)
        
        # 📊 LOG TO EQUITY HISTORY
        EquityService._log_equity_change(
            project_id=project.id,
            user_id=solver_id,
            action='grant',
            equity_change=equity_reward,
            equity_before=equity_before,
            equity_after=equity_after,
            reason=f'Task "{task.title}" completed (solution #{solution.id})',
            source_type='task_completion',
            source_id=task.id,
            changed_by_user_id=None  # Automatic system action
        )
        
        # Also update Collaborator.equity_share for backward compatibility
        collaborator = Collaborator.query.filter_by(
            project_id=project.id,
            user_id=solver_id
        ).first()
        
        if collaborator:
            collaborator.equity_share = solver_equity.equity_percentage
        
        db.session.commit()
        
        current_app.logger.info(
            f'Distributed {equity_reward}% equity to user {solver_id} for completing task {task.id}'
        )
        
        return solver_equity

    @staticmethod
    def distribute_free_proposal_equity(proposal, changed_by_user_id=None):
        """Distribute equity when a free proposal is accepted."""
        project = proposal.project
        developer_id = proposal.developer_id
        equity_amount = proposal.equity_requested

        if equity_amount <= 0:
            current_app.logger.info(
                f'Free proposal {proposal.id} requests no equity, skipping distribution'
            )
            return None

        if not project.can_distribute_equity(equity_amount):
            available = project.get_available_equity()
            raise ValueError(
                f'Cannot distribute {equity_amount}% equity. Only {available}% available.'
            )

        equity_record = ProjectEquity.query.filter_by(
            project_id=project.id,
            user_id=developer_id
        ).first()

        equity_before = 0.0
        if not equity_record:
            equity_record = ProjectEquity(
                project_id=project.id,
                user_id=developer_id,
                equity_percentage=0.0,
                earned_from=''
            )
            db.session.add(equity_record)
        else:
            equity_before = equity_record.equity_percentage

        equity_record.equity_percentage += equity_amount
        equity_after = equity_record.equity_percentage
        equity_record.last_updated = datetime.now(timezone.utc)

        source = f'free_proposal_{proposal.id}'
        if equity_record.earned_from:
            existing_sources = [s for s in equity_record.earned_from.split(',') if s]
            if source not in existing_sources:
                equity_record.earned_from = equity_record.earned_from + f',{source}'
        else:
            equity_record.earned_from = source

        EquityService._log_equity_change(
            project_id=project.id,
            user_id=developer_id,
            action='grant',
            equity_change=equity_amount,
            equity_before=equity_before,
            equity_after=equity_after,
            reason=f'Free proposal "{proposal.title}" accepted',
            source_type='free_proposal',
            source_id=proposal.id,
            changed_by_user_id=changed_by_user_id
        )

        collaborator = Collaborator.query.filter_by(
            project_id=project.id,
            user_id=developer_id
        ).first()

        if collaborator:
            collaborator.equity_share = equity_record.equity_percentage

        db.session.commit()

        current_app.logger.info(
            f'Distributed {equity_amount}% equity to user {developer_id} for free proposal {proposal.id}'
        )

        return equity_record
    
    @staticmethod
    def get_cap_table(project):
        """
        Get complete cap table (equity distribution) for a project.
        
        Args:
            project: Project instance
            
        Returns:
            list: ProjectEquity records ordered by equity percentage (desc)
        """
        return ProjectEquity.query.filter_by(
            project_id=project.id
        ).order_by(ProjectEquity.equity_percentage.desc()).all()
    
    @staticmethod
    def get_user_total_equity():
        """
        Calculate total equity a user has across all projects.
        
        Args:
            user: User instance
            
        Returns:
            dict: {
                'total_projects': int,
                'total_equity': float,
                'projects': list of dicts with project info and equity
            }
        """
        from ..models import User
        
        # This would be called with a user parameter in actual usage
        # Placeholder implementation
        return {
            'total_projects': 0,
            'total_equity': 0.0,
            'projects': []
        }
    
    @staticmethod
    def calculate_user_total_equity(user):
        """
        Calculate total equity for a specific user across all projects.
        
        Args:
            user: User instance
            
        Returns:
            dict: Summary of user's equity holdings
        """
        equity_records = ProjectEquity.query.filter_by(user_id=user.id).all()
        
        projects_data = []
        total_equity = 0.0
        
        for equity in equity_records:
            projects_data.append({
                'project_id': equity.project_id,
                'project_name': equity.project.name,
                'equity_percentage': equity.equity_percentage,
                'earned_from': equity.earned_from.split(',') if equity.earned_from else [],
                'last_updated': equity.last_updated
            })
            total_equity += equity.equity_percentage
        
        return {
            'total_projects': len(equity_records),
            'total_equity_points': total_equity,  # Sum of all percentages
            'projects': projects_data
        }
    
    @staticmethod
    def sync_collaborator_equity(project_id):
        """
        Synchronize Collaborator.equity_share with ProjectEquity records.
        Useful for backward compatibility after migrations.
        
        Args:
            project_id: Project ID
            
        Returns:
            int: Number of collaborators synced
        """
        equity_records = ProjectEquity.query.filter_by(project_id=project_id).all()
        synced_count = 0
        
        for equity in equity_records:
            collaborator = Collaborator.query.filter_by(
                project_id=project_id,
                user_id=equity.user_id
            ).first()
            
            if collaborator:
                collaborator.equity_share = equity.equity_percentage
                synced_count += 1
        
        db.session.commit()
        
        current_app.logger.info(
            f'Synced {synced_count} collaborator equity records for project {project_id}'
        )
        
        return synced_count
    
    @staticmethod
    def validate_and_fix_equity(project):
        """
        Validate equity distribution for a project and attempt to fix issues.
        
        Args:
            project: Project instance
            
        Returns:
            dict: {
                'valid': bool,
                'issues': list of str (issue descriptions),
                'fixed': list of str (fixes applied)
            }
        """
        issues = []
        fixed = []
        
        # Check total equity
        total = project.get_total_equity_distributed()
        available = project.get_available_equity()
        
        # Get equity configuration
        config = project.equity_config if hasattr(project, 'equity_config') and project.equity_config else None
        # Handle equity_config as both single object and list (relationship behavior)
        if config and isinstance(config, list):
            config = config[0] if len(config) > 0 else None
        
        # Now config is either a single EquityConfiguration object or None
        max_allowed = config.team_percentage if (config and hasattr(config, 'team_percentage')) else (100.0 - project.platform_fee)
        
        if total > max_allowed:
            issues.append(f'Total equity ({total}%) exceeds maximum ({max_allowed}%)')
        
        if available < 0:
            issues.append(f'Negative available equity: {available}%')
        
        # Check for orphaned equity records (users not in collaborators)
        equity_records = ProjectEquity.query.filter_by(project_id=project.id).all()
        for equity in equity_records:
            if equity.user_id == project.creator_id:
                continue  # Creator is always valid
            
            collaborator = Collaborator.query.filter_by(
                project_id=project.id,
                user_id=equity.user_id
            ).first()
            
            if not collaborator:
                issues.append(
                    f'User {equity.user_id} has equity but is not a collaborator'
                )
        
        return {
            'valid': len(issues) == 0,
            'issues': issues,
            'fixed': fixed,
            'total_distributed': total,
            'available': available
        }
