# app/services/notification_service.py

"""
Servizio centralizzato per la gestione delle notifiche.
Fornisce funzioni helper per creare notifiche in modo consistente.
"""

from datetime import datetime, timezone
from typing import List, Optional
from ..models import Notification, Project, Task, Solution, Collaborator, User
from ..extensions import db


class NotificationService:
    """Servizio per gestire le notifiche del sistema"""
    
    # Tipi di notifiche supportati
    TYPES = {
        'task_created': 'Task Creato',
        'task_updated': 'Task Aggiornato',
        'task_completed': 'Task Completato',
        'solution_published': 'Soluzione Pubblicata',
        'solution_approved': 'Soluzione Approvata',
        'solution_rejected': 'Soluzione Rifiutata',
        'project_invite': 'Invito Progetto',
        'project_invite_accepted': 'Invito Accettato',
        'project_invite_declined': 'Invito Rifiutato',
        'collaborator_added': 'Collaboratore Aggiunto',
        'wiki_page_created': 'Pagina Wiki Creata',
        'wiki_page_updated': 'Pagina Wiki Aggiornata',
        'free_proposal_submitted': 'Proposta Libera Inviata',
        'free_proposal_accepted': 'Proposta Libera Accettata',
        'free_proposal_rejected': 'Proposta Libera Rifiutata',
        'investment_made': 'Investimento Effettuato',
        'project_voted': 'Progetto Votato',
        'equity_granted': 'Equity Assegnata',
        'comment_added': 'Commento Aggiunto',
        'workspace_upload_ready': 'Workspace Upload Pronto',
        'workspace_sync_completed': 'Workspace Sync Completato',
        'workspace_sync_failed': 'Workspace Sync Fallito',
    }
    
    @staticmethod
    def create_notification(
        user_id: int,
        notification_type: str,
        message: str,
        project_id: Optional[int] = None,
        task_id: Optional[int] = None,
        solution_id: Optional[int] = None
    ) -> Notification:
        """
        Crea una singola notifica.
        
        Args:
            user_id: ID dell'utente destinatario
            notification_type: Tipo di notifica (deve essere in TYPES)
            message: Messaggio della notifica
            project_id: ID del progetto correlato (opzionale)
            task_id: ID del task correlato (opzionale)
            solution_id: ID della soluzione correlata (opzionale)
        
        Returns:
            Notification: Istanza della notifica creata
        """
        if notification_type not in NotificationService.TYPES:
            raise ValueError(f"Tipo notifica non valido: {notification_type}")
        
        notification = Notification(
            user_id=user_id,
            type=notification_type,
            message=message,
            project_id=project_id,
            timestamp=datetime.now(timezone.utc)
        )
        
        db.session.add(notification)
        return notification
    
    @staticmethod
    def notify_project_collaborators(
        project_id: int,
        notification_type: str,
        message: str,
        exclude_user_id: Optional[int] = None
    ) -> List[Notification]:
        """
        Notifica tutti i collaboratori di un progetto (incluso il creatore).
        
        Args:
            project_id: ID del progetto
            notification_type: Tipo di notifica
            message: Messaggio della notifica
            exclude_user_id: ID utente da escludere (es. chi ha generato l'evento)
        
        Returns:
            List[Notification]: Lista delle notifiche create
        """
        project = Project.query.get_or_404(project_id)
        
        # Raccogli tutti gli ID dei collaboratori
        # Optimize: Use database query to get only user_ids instead of loading full objects
        collaborator_ids = db.session.query(Collaborator.user_id).filter_by(
            project_id=project_id
        ).all()
        collaborator_ids = [user_id for (user_id,) in collaborator_ids]
        
        # Aggiungi il creatore se non è già nella lista
        if project.creator_id not in collaborator_ids:
            collaborator_ids.append(project.creator_id)
        
        notifications = []
        for user_id in set(collaborator_ids):
            if exclude_user_id and user_id == exclude_user_id:
                continue
            
            notification = NotificationService.create_notification(
                user_id=user_id,
                notification_type=notification_type,
                message=message,
                project_id=project_id
            )
            notifications.append(notification)
        
        return notifications
    
    @staticmethod
    def notify_task_created(task: Task, project: Project, creator_id: int):
        """Notifica la creazione di un nuovo task"""
        task_type_text = "privato" if task.is_private else "pubblico"
        message = f"È stato creato un nuovo task {task_type_text} '{task.title}' nel progetto '{project.name}'."
        
        NotificationService.notify_project_collaborators(
            project_id=project.id,
            notification_type='task_created',
            message=message,
            exclude_user_id=creator_id
        )
    
    @staticmethod
    def notify_solution_published(solution: Solution, task: Task, project: Project, submitter_id: int):
        """Notifica la pubblicazione di una nuova soluzione"""
        message = f"È stata pubblicata una nuova soluzione per il task '{task.title}' nel progetto '{project.name}'."
        
        NotificationService.notify_project_collaborators(
            project_id=project.id,
            notification_type='solution_published',
            message=message,
            exclude_user_id=submitter_id
        )
        
        # Notifica specifica al creatore del task
        if task.creator_id != submitter_id:
            NotificationService.create_notification(
                user_id=task.creator_id,
                notification_type='solution_published',
                message=f"Una nuova soluzione è stata pubblicata per il tuo task '{task.title}'.",
                project_id=project.id
            )
    
    @staticmethod
    def notify_solution_approved(solution: Solution, task: Task, project: Project):
        """Notifica l'approvazione di una soluzione"""
        # Notifica al submitter
        NotificationService.create_notification(
            user_id=solution.submitted_by_user_id,
            notification_type='solution_approved',
            message=f"La tua soluzione per il task '{task.title}' nel progetto '{project.name}' è stata approvata! 🎉",
            project_id=project.id
        )
        
        # Notifica ai collaboratori
        message = f"La soluzione per il task '{task.title}' nel progetto '{project.name}' è stata approvata."
        NotificationService.notify_project_collaborators(
            project_id=project.id,
            notification_type='solution_approved',
            message=message
        )
    
    @staticmethod
    def notify_project_invite(project: Project, invitee_id: int, inviter: User):
        """Notifica un invito a un progetto"""
        message = f"Sei stato invitato a collaborare al progetto '{project.name}' da {inviter.username}."
        
        NotificationService.create_notification(
            user_id=invitee_id,
            notification_type='project_invite',
            message=message,
            project_id=project.id
        )
    
    @staticmethod
    def notify_invite_accepted(project: Project, user: User):
        """Notifica quando un invito viene accettato"""
        message = f"{user.username} ha accettato l'invito al progetto '{project.name}'."
        
        NotificationService.notify_project_collaborators(
            project_id=project.id,
            notification_type='project_invite_accepted',
            message=message,
            exclude_user_id=user.id
        )
    
    @staticmethod
    def notify_wiki_page_created(project: Project, page_title: str, creator_id: int):
        """Notifica la creazione di una nuova pagina wiki"""
        message = f"È stata creata una nuova pagina Wiki '{page_title}' nel progetto '{project.name}'."
        
        NotificationService.notify_project_collaborators(
            project_id=project.id,
            notification_type='wiki_page_created',
            message=message,
            exclude_user_id=creator_id
        )
    
    @staticmethod
    def notify_wiki_page_updated(project: Project, page_title: str, editor_id: int):
        """Notifica l'aggiornamento di una pagina wiki"""
        message = f"La pagina Wiki '{page_title}' nel progetto '{project.name}' è stata aggiornata."
        
        NotificationService.notify_project_collaborators(
            project_id=project.id,
            notification_type='wiki_page_updated',
            message=message,
            exclude_user_id=editor_id
        )
    
    @staticmethod
    def notify_free_proposal_submitted(project: Project, proposal_title: str, submitter_id: int):
        """Notifica l'invio di una proposta libera"""
        message = f"È stata inviata una nuova proposta libera '{proposal_title}' per il progetto '{project.name}'."
        
        NotificationService.notify_project_collaborators(
            project_id=project.id,
            notification_type='free_proposal_submitted',
            message=message,
            exclude_user_id=submitter_id
        )
    
    @staticmethod
    def notify_free_proposal_decision(project: Project, proposal_title: str, decision: str, developer_id: int):
        """Notifica la decisione su una proposta libera"""
        decision_text = "accettata" if decision == 'accepted' else "rifiutata"
        message = f"La tua proposta libera '{proposal_title}' per il progetto '{project.name}' è stata {decision_text}."
        
        NotificationService.create_notification(
            user_id=developer_id,
            notification_type=f'free_proposal_{decision}',
            message=message,
            project_id=project.id
        )
    
    @staticmethod
    def get_unread_count(user_id: int) -> int:
        """Ottiene il numero di notifiche non lette per un utente"""
        return Notification.query.filter_by(
            user_id=user_id,
            is_read=False
        ).count()
    
    @staticmethod
    def mark_as_read(notification_id: int, user_id: int) -> bool:
        """Marca una notifica come letta"""
        notification = Notification.query.filter_by(
            id=notification_id,
            user_id=user_id
        ).first()
        
        if notification:
            notification.is_read = True
            db.session.commit()
            return True
        return False
    
    @staticmethod
    def mark_all_as_read(user_id: int) -> int:
        """Marca tutte le notifiche di un utente come lette"""
        count = Notification.query.filter_by(
            user_id=user_id,
            is_read=False
        ).update({'is_read': True})
        
        db.session.commit()
        return count
    
    @staticmethod
    def notify_milestone_created(project: Project, milestone_title: str, creator_id: int):
        """Notifica la creazione di una milestone"""
        message = f"È stata creata una nuova milestone '{milestone_title}' nel progetto '{project.name}'."
        
        NotificationService.notify_project_collaborators(
            project_id=project.id,
            notification_type='milestone_created',
            message=message,
            exclude_user_id=creator_id
        )
    
    @staticmethod
    def notify_milestone_updated(project: Project, milestone_title: str, editor_id: int):
        """Notifica l'aggiornamento di una milestone"""
        message = f"La milestone '{milestone_title}' nel progetto '{project.name}' è stata aggiornata."
        
        NotificationService.notify_project_collaborators(
            project_id=project.id,
            notification_type='milestone_updated',
            message=message,
            exclude_user_id=editor_id
        )
    
    @staticmethod
    def notify_milestone_completed(project: Project, milestone_title: str, completer_id: int):
        """Notifica il completamento di una milestone"""
        message = f"La milestone '{milestone_title}' nel progetto '{project.name}' è stata completata!"
        
        NotificationService.notify_project_collaborators(
            project_id=project.id,
            notification_type='milestone_completed',
            message=message,
            exclude_user_id=completer_id
        )

    @staticmethod
    def notify_workspace_upload_ready(project: Project, metadata: dict, initiator_id: int):
        """Notifica i collaboratori quando una sessione di upload è pronta per il sync"""
        file_count = metadata.get('file_count') or len(metadata.get('files') or [])
        message = (
            f"Nuovo upload ({metadata.get('type', 'manual')}) pronto al sync in '{project.name}' "
            f"({file_count} file)."
        )
        NotificationService.notify_project_collaborators(
            project_id=project.id,
            notification_type='workspace_upload_ready',
            message=message,
            exclude_user_id=initiator_id
        )

    @staticmethod
    def notify_workspace_sync_completed(project: Project, metadata: dict, initiator_id: Optional[int] = None):
        """Notifica il completamento di una sincronizzazione workspace"""
        file_count = metadata.get('file_count') or len(metadata.get('files') or [])
        message = (
            f"Sync completata per '{project.name}': {file_count} file inviati al repository gestito."
        )
        NotificationService.notify_project_collaborators(
            project_id=project.id,
            notification_type='workspace_sync_completed',
            message=message,
            exclude_user_id=initiator_id
        )

    @staticmethod
    def notify_workspace_sync_failed(project: Project, metadata: dict, initiator_id: Optional[int] = None):
        """Notifica un errore durante la sincronizzazione workspace"""
        error = metadata.get('error') or 'Errore sconosciuto'
        message = (
            f"Sync fallita per '{project.name}': {error}."
        )
        NotificationService.notify_project_collaborators(
            project_id=project.id,
            notification_type='workspace_sync_failed',
            message=message,
            exclude_user_id=initiator_id
        )

