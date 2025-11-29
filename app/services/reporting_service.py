# app/services/reporting_service.py
"""
Transparency Reporting Service

Generates public transparency reports, dashboards, and exports
for projects. All data is publicly accessible for verification.
"""

from decimal import Decimal
from datetime import datetime, timezone, timedelta
from flask import current_app
from sqlalchemy import func, desc
import json

from ..extensions import db
from ..models import (
    Project, PhantomShare, ShareHistory, ProjectRevenue, 
    RevenueDistribution, TransparencyReport, User
)


class ReportingService:
    """Service for generating transparency reports and dashboards"""
    
    @staticmethod
    def get_transparency_data(project, include_private_info=False, anonymize_holders=False):
        """
        Get all transparency data for a project.
        
        Args:
            project: Project instance
            include_private_info: If True, include private data (for creator/collaborators)
            anonymize_holders: If True, anonymize holder names
            
        Returns:
            dict: Complete transparency data
        """
        # Check if project uses shares system
        uses_shares = project.uses_shares_system()
        
        # Shares data
        if uses_shares:
            total_shares = float(project.total_shares) if project.total_shares else 0
            distributed_shares = float(project.get_total_shares_distributed() or Decimal('0'))
            available_shares = float(project.get_available_shares() or Decimal('0'))
            
            # Get all holders
            holders_query = PhantomShare.query.filter_by(project_id=project.id).order_by(desc(PhantomShare.shares_count))
            holders = holders_query.all()
            
            holders_list = []
            for holder in holders:
                user = holder.user
                percentage = holder.get_percentage()
                
                holder_data = {
                    'shares_count': float(holder.shares_count),
                    'percentage': percentage,
                    'earned_from': holder.earned_from or '',
                    'joined_at': holder.created_at.isoformat() if holder.created_at else None,
                    'is_creator': holder.user_id == project.creator_id  # Flag per identificare creatore
                }
                
                # Formatta earned_from per display più chiaro
                if holder_data['earned_from'] == 'initial_creator_allocation':
                    holder_data['earned_from_display'] = 'Allocazione iniziale automatica (10%)'
                elif holder_data['earned_from'].startswith('task_'):
                    task_id = holder_data['earned_from'].replace('task_', '')
                    holder_data['earned_from_display'] = f'Task #{task_id} completato'
                elif holder_data['earned_from'] == 'investment':
                    holder_data['earned_from_display'] = 'Investimento'
                else:
                    holder_data['earned_from_display'] = holder_data['earned_from'] or 'N/A'
                
                if anonymize_holders:
                    holder_data['user_id'] = None
                    holder_data['username'] = f'Holder #{holder.id}'
                    holder_data['is_anonymous'] = True
                else:
                    holder_data['user_id'] = user.id
                    holder_data['username'] = user.username
                    holder_data['is_anonymous'] = False
                
                holders_list.append(holder_data)
        else:
            # Old equity system
            total_shares = 0
            distributed_shares = 0
            available_shares = 0
            holders_list = []
        
        # Revenue data
        total_revenue = db.session.query(
            func.sum(ProjectRevenue.amount)
        ).filter_by(project_id=project.id).scalar() or Decimal('0')
        total_revenue = float(total_revenue)
        
        revenue_records = ProjectRevenue.query.filter_by(
            project_id=project.id
        ).order_by(desc(ProjectRevenue.recorded_at)).limit(50).all()
        
        revenue_history = []
        for rev in revenue_records:
            revenue_history.append({
                'amount': float(rev.amount),
                'currency': rev.currency,
                'source': rev.source or 'unknown',
                'description': rev.description,
                'recorded_at': rev.recorded_at.isoformat() if rev.recorded_at else None
            })
        
        # Distribution data
        total_distributed = db.session.query(
            func.sum(RevenueDistribution.amount)
        ).filter_by(project_id=project.id).scalar() or Decimal('0')
        total_distributed = float(total_distributed)
        
        distributions_count = RevenueDistribution.query.filter_by(
            project_id=project.id
        ).count()
        
        distributions_history = RevenueDistribution.query.filter_by(
            project_id=project.id
        ).order_by(desc(RevenueDistribution.distributed_at)).limit(50).all()
        
        distributions_list = []
        for dist in distributions_history:
            dist_data = {
                'amount': float(dist.amount),
                'currency': dist.currency,
                'shares_count': float(dist.shares_count),
                'percentage': dist.percentage,
                'distributed_at': dist.distributed_at.isoformat() if dist.distributed_at else None
            }
            
            if anonymize_holders:
                dist_data['user_id'] = None
                dist_data['username'] = f'Holder #{dist.user_id}'
                dist_data['is_anonymous'] = True
            else:
                dist_data['user_id'] = dist.user_id
                dist_data['username'] = dist.user.username if dist.user else 'Unknown'
                dist_data['is_anonymous'] = False
            
            distributions_list.append(dist_data)
        
        # Growth metrics
        if uses_shares:
            # New holders this month
            this_month_start = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            new_holders_this_month = PhantomShare.query.filter(
                PhantomShare.project_id == project.id,
                PhantomShare.created_at >= this_month_start
            ).count()
        else:
            new_holders_this_month = 0
        
        return {
            'project_id': project.id,
            'project_name': project.name,
            'uses_shares_system': uses_shares,
            
            # Shares data
            'shares': {
                'total': total_shares,
                'distributed': distributed_shares,
                'available': available_shares,
                'holders_count': len(holders_list),
                'holders': holders_list
            },
            
            # Revenue data
            'revenue': {
                'total': total_revenue,
                'currency': 'EUR',  # Default
                'records_count': len(revenue_history),
                'history': revenue_history
            },
            
            # Distribution data
            'distributions': {
                'total': total_distributed,
                'count': distributions_count,
                'history': distributions_list
            },
            
            # Growth metrics
            'growth': {
                'new_holders_this_month': new_holders_this_month
            },
            
            # Metadata
            'generated_at': datetime.now(timezone.utc).isoformat(),
            'is_public': True
        }
    
    @staticmethod
    def generate_monthly_report(project, month, year):
        """
        Generate monthly transparency report.
        
        Args:
            project: Project instance
            month: Month (1-12)
            year: Year
            
        Returns:
            TransparencyReport: Generated report
        """
        # Calculate month date range
        month_start = datetime(year, month, 1, tzinfo=timezone.utc)
        if month == 12:
            month_end = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
        else:
            month_end = datetime(year, month + 1, 1, tzinfo=timezone.utc)
        
        # Get revenue for the month
        month_revenue = db.session.query(
            func.sum(ProjectRevenue.amount)
        ).filter(
            ProjectRevenue.project_id == project.id,
            ProjectRevenue.recorded_at >= month_start,
            ProjectRevenue.recorded_at < month_end
        ).scalar() or Decimal('0')
        
        # Get distributions for the month
        month_distributions = db.session.query(
            func.sum(RevenueDistribution.amount)
        ).filter(
            RevenueDistribution.project_id == project.id,
            RevenueDistribution.distributed_at >= month_start,
            RevenueDistribution.distributed_at < month_end
        ).scalar() or Decimal('0')
        
        # Get new holders for the month
        if project.uses_shares_system():
            new_holders = PhantomShare.query.filter(
                PhantomShare.project_id == project.id,
                PhantomShare.created_at >= month_start,
                PhantomShare.created_at < month_end
            ).count()
        else:
            new_holders = 0
        
        # Build report data
        report_data = {
            'month': month,
            'year': year,
            'project_id': project.id,
            'project_name': project.name,
            'revenue': {
                'total': float(month_revenue),
                'currency': 'EUR',
                'records': []
            },
            'distributions': {
                'total': float(month_distributions),
                'count': 0,
                'records': []
            },
            'growth': {
                'new_holders': new_holders
            },
            'generated_at': datetime.now(timezone.utc).isoformat()
        }
        
        # Get detailed revenue records
        revenue_records = ProjectRevenue.query.filter(
            ProjectRevenue.project_id == project.id,
            ProjectRevenue.recorded_at >= month_start,
            ProjectRevenue.recorded_at < month_end
        ).all()
        
        for rev in revenue_records:
            report_data['revenue']['records'].append({
                'amount': float(rev.amount),
                'source': rev.source,
                'description': rev.description,
                'recorded_at': rev.recorded_at.isoformat() if rev.recorded_at else None
            })
        
        # Get detailed distribution records
        dist_records = RevenueDistribution.query.filter(
            RevenueDistribution.project_id == project.id,
            RevenueDistribution.distributed_at >= month_start,
            RevenueDistribution.distributed_at < month_end
        ).all()
        
        report_data['distributions']['count'] = len(dist_records)
        for dist in dist_records:
            report_data['distributions']['records'].append({
                'user_id': dist.user_id,
                'amount': float(dist.amount),
                'shares_count': float(dist.shares_count),
                'percentage': dist.percentage,
                'distributed_at': dist.distributed_at.isoformat() if dist.distributed_at else None
            })
        
        # Check if report already exists
        existing_report = TransparencyReport.query.filter_by(
            project_id=project.id,
            report_month=month,
            report_year=year
        ).first()
        
        if existing_report:
            # Update existing report
            existing_report.report_data = json.dumps(report_data)
            existing_report.total_revenue = month_revenue
            existing_report.total_distributions = month_distributions
            existing_report.new_holders_count = new_holders
            existing_report.generated_at = datetime.now(timezone.utc)
            db.session.commit()
            return existing_report
        else:
            # Create new report
            new_report = TransparencyReport(
                project_id=project.id,
                report_month=month,
                report_year=year,
                report_data=json.dumps(report_data),
                total_revenue=month_revenue,
                total_distributions=month_distributions,
                new_holders_count=new_holders,
                generated_by_system=True
            )
            db.session.add(new_report)
            db.session.commit()
            return new_report
    
    @staticmethod
    def export_transparency_data(project, format='json', anonymize_holders=False):
        """
        Export transparency data in CSV or JSON format.
        
        Args:
            project: Project instance
            format: 'json' or 'csv'
            anonymize_holders: If True, anonymize holder names
            
        Returns:
            str: Exported data as string
        """
        data = ReportingService.get_transparency_data(project, anonymize_holders=anonymize_holders)
        
        if format == 'json':
            return json.dumps(data, indent=2, default=str)
        elif format == 'csv':
            # Generate CSV
            import csv
            import io
            
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Header
            writer.writerow(['Project Transparency Data'])
            writer.writerow(['Project:', project.name])
            writer.writerow(['Generated:', datetime.now(timezone.utc).isoformat()])
            writer.writerow([])
            
            # Shares summary
            writer.writerow(['SHARES SUMMARY'])
            writer.writerow(['Total Shares', data['shares']['total']])
            writer.writerow(['Distributed', data['shares']['distributed']])
            writer.writerow(['Available', data['shares']['available']])
            writer.writerow(['Holders Count', data['shares']['holders_count']])
            writer.writerow([])
            
            # Holders
            writer.writerow(['HOLDERS'])
            writer.writerow(['User ID', 'Username', 'Shares', 'Percentage', 'Earned From', 'Is Creator'])
            for holder in data['shares']['holders']:
                writer.writerow([
                    holder.get('user_id', 'N/A'),
                    holder.get('username', 'N/A'),
                    holder['shares_count'],
                    holder['percentage'],
                    holder.get('earned_from_display', holder.get('earned_from', '')),
                    'Yes' if holder.get('is_creator') else 'No'
                ])
            writer.writerow([])
            
            # Revenue summary
            writer.writerow(['REVENUE SUMMARY'])
            writer.writerow(['Total Revenue', data['revenue']['total'], data['revenue']['currency']])
            writer.writerow([])
            
            # Revenue history
            writer.writerow(['REVENUE HISTORY'])
            writer.writerow(['Date', 'Amount', 'Currency', 'Source', 'Description'])
            for rev in data['revenue']['history']:
                writer.writerow([
                    rev.get('recorded_at', ''),
                    rev['amount'],
                    rev['currency'],
                    rev.get('source', ''),
                    rev.get('description', '')
                ])
            writer.writerow([])
            
            # Distributions summary
            writer.writerow(['DISTRIBUTIONS SUMMARY'])
            writer.writerow(['Total Distributed', data['distributions']['total']])
            writer.writerow(['Count', data['distributions']['count']])
            writer.writerow([])
            
            # Distributions history
            writer.writerow(['DISTRIBUTIONS HISTORY'])
            writer.writerow(['Date', 'User ID', 'Username', 'Amount', 'Currency', 'Shares', 'Percentage'])
            for dist in data['distributions']['history']:
                writer.writerow([
                    dist.get('distributed_at', ''),
                    dist.get('user_id', 'N/A'),
                    dist.get('username', 'N/A'),
                    dist['amount'],
                    dist['currency'],
                    dist['shares_count'],
                    dist['percentage']
                ])
            
            return output.getvalue()
        else:
            raise ValueError(f"Unsupported format: {format}")

