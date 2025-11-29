# app/services/share_service.py
"""
Phantom Shares Distribution Service

Manages automatic share distribution when tasks are completed,
validates share constraints, and provides share tracking utilities.

This service replaces EquityService for projects using the new shares system.
Projects with total_shares=None continue using the old equity system (backward compatibility).
"""

from decimal import Decimal
from datetime import datetime, timezone
from flask import current_app
from ..extensions import db
from ..models import PhantomShare, Project, Task, Solution, Collaborator, ShareHistory
from ..utils import db_transaction


class ShareService:
    """Service for managing project phantom shares distribution"""
    
    DEFAULT_TOTAL_SHARES = Decimal('10000')  # Default: 10,000 shares per project
    
    @staticmethod
    def _log_share_change(project_id, user_id, action, shares_change, shares_before, shares_after,
                          percentage_before, percentage_after, reason, source_type, source_id=None, changed_by_user_id=None):
        """
        Internal method to log share changes to audit log.
        
        Args:
            project_id: Project ID
            user_id: User receiving share change
            action: Type of action ('grant', 'revoke', 'transfer', 'adjust', 'initial')
            shares_change: Amount of shares changed (positive or negative, Decimal)
            shares_before: Shares before change (Decimal)
            shares_after: Shares after change (Decimal)
            percentage_before: Percentage before change (float)
            percentage_after: Percentage after change (float)
            reason: Human-readable reason
            source_type: Type of source ('task_completion', 'manual', 'bonus', 'initial', 'investment')
            source_id: ID of related entity (optional)
            changed_by_user_id: User who made the change (optional, for manual changes)
        """
        history_entry = ShareHistory(
            project_id=project_id,
            user_id=user_id,
            action=action,
            shares_change=shares_change,
            shares_before=shares_before,
            shares_after=shares_after,
            percentage_before=percentage_before,
            percentage_after=percentage_after,
            reason=reason,
            source_type=source_type,
            source_id=source_id,
            changed_by_user_id=changed_by_user_id
        )
        
        db.session.add(history_entry)
        
        current_app.logger.info(
            f'Share change logged: {action} {shares_change} shares for user {user_id} in project {project_id} (source: {source_type})'
        )
    
    @staticmethod
    def initialize_project_shares(project, creator_shares_percentage=None, total_shares=None):
        """
        Initialize shares system for a new project.
        Sets total_shares and creates initial shares for creator.
        
        Args:
            project: Project instance
            creator_shares_percentage: Percentage of shares for creator (default: uses project.creator_equity)
            total_shares: Total shares to issue (default: 10,000)
            
        Returns:
            PhantomShare: Creator's share record
        """
        # Check if project already has shares system initialized
        if project.total_shares is not None:
            current_app.logger.warning(
                f'Project {project.id} already has shares system initialized'
            )
            existing = PhantomShare.query.filter_by(
                project_id=project.id,
                user_id=project.creator_id
            ).first()
            if existing:
                return existing
        
        # Set total shares (default: 10,000)
        if total_shares is None:
            total_shares = ShareService.DEFAULT_TOTAL_SHARES
        else:
            total_shares = Decimal(str(total_shares))
        
        project.total_shares = total_shares
        db.session.flush()
        
        # Calculate creator shares
        if creator_shares_percentage is None:
            # Use creator_equity percentage if available, otherwise default to 10%
            if project.creator_equity is not None:
                creator_shares_percentage = project.creator_equity
            else:
                creator_shares_percentage = 10.0  # Default: 10% al creatore
        
        creator_shares = (total_shares * Decimal(str(creator_shares_percentage))) / Decimal('100')
        
        # Create share record
        creator_share = PhantomShare(
            project_id=project.id,
            user_id=project.creator_id,
            shares_count=creator_shares,
            earned_from='initial_creator_allocation'  # Più descrittivo e chiaro
        )
        
        with db_transaction():
            db.session.add(creator_share)
            
            # Log to share history
            ShareService._log_share_change(
                project_id=project.id,
                user_id=project.creator_id,
                action='initial',
                shares_change=creator_shares,
                shares_before=Decimal('0'),
                shares_after=creator_shares,
                percentage_before=0.0,
                percentage_after=float(creator_shares_percentage),
                reason=f'Automatic initial allocation: {creator_shares_percentage}% ({creator_shares} shares) for project creator',
                source_type='initial',
                source_id=None,
                changed_by_user_id=project.creator_id
            )
        
        current_app.logger.info(
            f'Initialized project shares: {total_shares} total shares, {creator_shares} for creator (user {project.creator_id}) in project {project.id}'
        )
        
        return creator_share
    
    @staticmethod
    def distribute_task_completion_shares(solution):
        """
        Distribute shares when a task solution is approved.
        
        Args:
            solution: Solution instance (must be approved)
            
        Returns:
            PhantomShare: Updated share record, or None if no shares distributed
            
        Raises:
            ValueError: If shares cannot be distributed (insufficient available)
        """
        task = solution.task
        project = task.project
        solver_id = solution.submitted_by_user_id
        
        # Check if project uses shares system
        if not project.uses_shares_system():
            # Project uses old equity system, return None (let EquityService handle it)
            return None
        
        # Get equity reward from task (as percentage)
        equity_reward_percentage = task.equity_reward
        
        if equity_reward_percentage <= 0:
            current_app.logger.info(
                f'Task {task.id} has no equity reward, skipping share distribution'
            )
            return None
        
        # Convert percentage to shares
        total_shares = Decimal(str(project.total_shares))
        shares_reward = (total_shares * Decimal(str(equity_reward_percentage))) / Decimal('100')
        
        # Validate available shares
        if not project.can_distribute_shares(shares_reward):
            available = project.get_available_shares()
            raise ValueError(
                f'Cannot distribute {shares_reward} shares ({equity_reward_percentage}%). Only {available} shares available.'
            )
        
        # Get or create solver's share record
        solver_share = PhantomShare.query.filter_by(
            project_id=project.id,
            user_id=solver_id
        ).first()
        
        shares_before = Decimal('0')
        percentage_before = 0.0
        if not solver_share:
            solver_share = PhantomShare(
                project_id=project.id,
                user_id=solver_id,
                shares_count=Decimal('0'),
                earned_from=''
            )
            db.session.add(solver_share)
        else:
            shares_before = Decimal(str(solver_share.shares_count))
            percentage_before = solver_share.get_percentage()
        
        # Distribute shares
        solver_share.shares_count += shares_reward
        shares_after = Decimal(str(solver_share.shares_count))
        percentage_after = solver_share.get_percentage()
        
        # Update earned_from
        source = f'task_{task.id}'
        if solver_share.earned_from:
            existing_sources = [s for s in solver_share.earned_from.split(',') if s]
            if source not in existing_sources:
                solver_share.earned_from = solver_share.earned_from + f',{source}'
        else:
            solver_share.earned_from = source
        
        solver_share.last_updated = datetime.now(timezone.utc)
        
        with db_transaction():
            # Log to share history
            ShareService._log_share_change(
                project_id=project.id,
                user_id=solver_id,
                action='grant',
                shares_change=shares_reward,
                shares_before=shares_before,
                shares_after=shares_after,
                percentage_before=percentage_before,
                percentage_after=percentage_after,
                reason=f'Task {task.id} completion: {task.title}',
                source_type='task_completion',
                source_id=task.id,
                changed_by_user_id=None  # System automated
            )
        
        current_app.logger.info(
            f'Distributed {shares_reward} shares ({equity_reward_percentage}%) to user {solver_id} for completing task {task.id}'
        )
        
        return solver_share
    
    @staticmethod
    def distribute_investment_shares(project, investor_id, equity_percentage):
        """
        Distribute shares when an investment is made.
        
        Args:
            project: Project instance
            investor_id: User ID making investment
            equity_percentage: Percentage of equity being purchased
            
        Returns:
            PhantomShare: Updated share record
            
        Raises:
            ValueError: If shares cannot be distributed
        """
        if not project.uses_shares_system():
            return None
        
        # Convert percentage to shares
        total_shares = Decimal(str(project.total_shares))
        shares_amount = (total_shares * Decimal(str(equity_percentage))) / Decimal('100')
        
        # Validate available shares
        if not project.can_distribute_shares(shares_amount):
            available = project.get_available_shares()
            raise ValueError(
                f'Cannot distribute {shares_amount} shares ({equity_percentage}%). Only {available} shares available.'
            )
        
        # Get or create investor's share record
        investor_share = PhantomShare.query.filter_by(
            project_id=project.id,
            user_id=investor_id
        ).first()
        
        shares_before = Decimal('0')
        percentage_before = 0.0
        if not investor_share:
            investor_share = PhantomShare(
                project_id=project.id,
                user_id=investor_id,
                shares_count=Decimal('0'),
                earned_from=''
            )
            db.session.add(investor_share)
        else:
            shares_before = Decimal(str(investor_share.shares_count))
            percentage_before = investor_share.get_percentage()
        
        # Distribute shares
        investor_share.shares_count += shares_amount
        shares_after = Decimal(str(investor_share.shares_count))
        percentage_after = investor_share.get_percentage()
        
        # Update earned_from
        source = 'investment'
        if investor_share.earned_from:
            existing_sources = [s for s in investor_share.earned_from.split(',') if s]
            if source not in existing_sources:
                investor_share.earned_from = investor_share.earned_from + f',{source}'
        else:
            investor_share.earned_from = source
        
        investor_share.last_updated = datetime.now(timezone.utc)
        
        with db_transaction():
            # Log to share history
            ShareService._log_share_change(
                project_id=project.id,
                user_id=investor_id,
                action='grant',
                shares_change=shares_amount,
                shares_before=shares_before,
                shares_after=shares_after,
                percentage_before=percentage_before,
                percentage_after=percentage_after,
                reason=f'Investment: {equity_percentage}% equity purchased',
                source_type='investment',
                source_id=None,
                changed_by_user_id=investor_id
            )
        
        current_app.logger.info(
            f'Distributed {shares_amount} shares ({equity_percentage}%) to investor {investor_id} in project {project.id}'
        )
        
        return investor_share
    
    @staticmethod
    def convert_equity_to_shares(project, equity_percentage):
        """
        Convert equity percentage to shares count.
        
        Args:
            project: Project instance (must have total_shares set)
            equity_percentage: Equity percentage to convert
            
        Returns:
            Decimal: Shares count
        """
        if not project.uses_shares_system():
            return None
        
        total_shares = Decimal(str(project.total_shares))
        shares = (total_shares * Decimal(str(equity_percentage))) / Decimal('100')
        return shares
    
    @staticmethod
    def convert_shares_to_percentage(project, shares_count):
        """
        Convert shares count to percentage.
        
        Args:
            project: Project instance (must have total_shares set)
            shares_count: Shares count to convert
            
        Returns:
            float: Percentage (0.0 to 100.0)
        """
        if not project.uses_shares_system() or not project.total_shares or project.total_shares == 0:
            return 0.0
        
        total_shares = Decimal(str(project.total_shares))
        shares = Decimal(str(shares_count))
        if total_shares == 0:
            return 0.0
        return float((shares / total_shares) * Decimal('100'))

