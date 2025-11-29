#!/usr/bin/env python
"""
Migration Script: Convert Existing Equity to Phantom Shares

This script migrates existing projects from the equity percentage system
to the new phantom shares system.

Process:
1. Find all projects without total_shares (using old equity system)
2. Initialize shares system for each project (default: 10,000 shares)
3. Convert ProjectEquity records to PhantomShare records
4. Convert EquityHistory records to ShareHistory records
5. Mark projects as migrated

Usage:
    python migrate_equity_to_shares.py [--dry-run] [--project-id PROJECT_ID]
"""

import sys
import os
from decimal import Decimal

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models import Project, ProjectEquity, EquityHistory, PhantomShare, ShareHistory
from app.services.share_service import ShareService
from flask import current_app

DEFAULT_TOTAL_SHARES = Decimal('10000')


def migrate_project(project, dry_run=False):
    """
    Migrate a single project from equity to shares system.
    
    Args:
        project: Project instance
        dry_run: If True, only show what would be done without making changes
    """
    print(f"\n{'[DRY RUN] ' if dry_run else ''}Migrating Project {project.id}: {project.name}")
    
    # Check if already migrated
    if project.total_shares is not None:
        print(f"  [WARN] Project {project.id} already uses shares system (total_shares={project.total_shares})")
        return False
    
    # Get all equity records for this project
    equity_records = ProjectEquity.query.filter_by(project_id=project.id).all()
    if not equity_records:
        print(f"  [INFO] No equity records found for project {project.id}, initializing empty shares system")
        if not dry_run:
            project.total_shares = DEFAULT_TOTAL_SHARES
            db.session.commit()
        return True
    
    total_equity = sum(eq.equity_percentage for eq in equity_records)
    print(f"  [INFO] Found {len(equity_records)} equity holders, total equity: {total_equity:.2f}%")
    
    if not dry_run:
        # Initialize shares system
        project.total_shares = DEFAULT_TOTAL_SHARES
        db.session.flush()
        
        # Convert each equity record to shares
        shares_created = 0
        for equity_record in equity_records:
            # Calculate shares from percentage
            shares_count = (DEFAULT_TOTAL_SHARES * Decimal(str(equity_record.equity_percentage))) / Decimal('100')
            
            # Check if share record already exists
            existing_share = PhantomShare.query.filter_by(
                project_id=project.id,
                user_id=equity_record.user_id
            ).first()
            
            if existing_share:
                print(f"    [WARN] Share record already exists for user {equity_record.user_id}, skipping")
                continue
            
            # Create PhantomShare record
            phantom_share = PhantomShare(
                project_id=project.id,
                user_id=equity_record.user_id,
                shares_count=shares_count,
                earned_from=equity_record.earned_from or 'migration',
                created_at=equity_record.created_at,
                last_updated=equity_record.last_updated
            )
            db.session.add(phantom_share)
            shares_created += 1
            
            percentage = float((shares_count / DEFAULT_TOTAL_SHARES) * Decimal('100'))
            print(f"    [OK] User {equity_record.user_id}: {equity_record.equity_percentage}% -> {float(shares_count):.2f} shares ({percentage:.2f}%)")
        
        # Migrate equity history to share history
        equity_history_records = EquityHistory.query.filter_by(project_id=project.id).all()
        history_migrated = 0
        
        for hist in equity_history_records:
            # Check if share history already exists
            existing_share_hist = ShareHistory.query.filter_by(
                project_id=project.id,
                user_id=hist.user_id,
                created_at=hist.created_at
            ).first()
            
            if existing_share_hist:
                continue
            
            # Convert equity change to shares change
            shares_change = (DEFAULT_TOTAL_SHARES * Decimal(str(hist.equity_change))) / Decimal('100')
            shares_before = (DEFAULT_TOTAL_SHARES * Decimal(str(hist.equity_before))) / Decimal('100')
            shares_after = (DEFAULT_TOTAL_SHARES * Decimal(str(hist.equity_after))) / Decimal('100')
            
            share_history = ShareHistory(
                project_id=hist.project_id,
                user_id=hist.user_id,
                action=hist.action,
                shares_change=shares_change,
                shares_before=shares_before,
                shares_after=shares_after,
                percentage_before=hist.equity_before,
                percentage_after=hist.equity_after,
                reason=hist.reason or 'Migrated from equity system',
                source_type=hist.source_type,
                source_id=hist.source_id,
                changed_by_user_id=hist.changed_by_user_id,
                created_at=hist.created_at
            )
            db.session.add(share_history)
            history_migrated += 1
        
        db.session.commit()
        print(f"  [OK] Migrated {shares_created} share records and {history_migrated} history records")
        return True
    else:
        # Dry run: just show what would be done
        for equity_record in equity_records:
            shares_count = (DEFAULT_TOTAL_SHARES * Decimal(str(equity_record.equity_percentage))) / Decimal('100')
            percentage = float((shares_count / DEFAULT_TOTAL_SHARES) * Decimal('100'))
            print(f"    [WOULD CREATE] User {equity_record.user_id}: {equity_record.equity_percentage}% -> {float(shares_count):.2f} shares ({percentage:.2f}%)")
        
        hist_count = EquityHistory.query.filter_by(project_id=project.id).count()
        print(f"  [WOULD MIGRATE] {hist_count} history records")
        return True


def main():
    """Main migration function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Migrate equity system to phantom shares')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done without making changes')
    parser.add_argument('--project-id', type=int, help='Migrate only a specific project ID')
    args = parser.parse_args()
    
    app = create_app()
    
    with app.app_context():
        print("=" * 60)
        print("EQUITY TO PHANTOM SHARES MIGRATION")
        print("=" * 60)
        
        if args.dry_run:
            print("\n[DRY RUN MODE] No changes will be made\n")
        
        # Find projects to migrate
        if args.project_id:
            projects = Project.query.filter_by(id=args.project_id).all()
            if not projects:
                print(f"[ERROR] Project {args.project_id} not found")
                return 1
        else:
            # Find all projects without total_shares (old system)
            projects = Project.query.filter(Project.total_shares.is_(None)).all()
        
        if not projects:
            print("[OK] No projects to migrate (all projects already use shares system)")
            return 0
        
        print(f"\nFound {len(projects)} project(s) to migrate\n")
        
        migrated = 0
        skipped = 0
        errors = 0
        
        for project in projects:
            try:
                if migrate_project(project, dry_run=args.dry_run):
                    migrated += 1
                else:
                    skipped += 1
            except Exception as e:
                errors += 1
                print(f"  [ERROR] Error migrating project {project.id}: {e}")
                import traceback
                traceback.print_exc()
                if not args.dry_run:
                    db.session.rollback()
        
        print("\n" + "=" * 60)
        print("MIGRATION SUMMARY")
        print("=" * 60)
        print(f"[OK] Migrated: {migrated}")
        print(f"[SKIP] Skipped: {skipped}")
        print(f"[ERROR] Errors: {errors}")
        print("=" * 60)
        
        if args.dry_run:
            print("\n[INFO] This was a DRY RUN. Run without --dry-run to apply changes.")
        
        return 0 if errors == 0 else 1


if __name__ == '__main__':
    sys.exit(main())

