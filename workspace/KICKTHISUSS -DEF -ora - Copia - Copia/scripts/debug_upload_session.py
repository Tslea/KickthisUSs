import io
import zipfile

from app import create_app
from app.extensions import db
from app.models import User, Project
from werkzeug.security import generate_password_hash


def ensure_user():
    user = User.query.filter_by(email='test_upload@example.com').first()
    if user:
        return user
    user = User(
        email='test_upload@example.com',
        username='testupload',
        password_hash=generate_password_hash('password')
    )
    db.session.add(user)
    db.session.commit()
    return user


def ensure_project(user):
    project = Project.query.filter_by(name='Upload Debug Project', creator_id=user.id).first()
    if project:
        return project
    project = Project(name='Upload Debug Project', slug='upload-debug-project', creator_id=user.id)
    db.session.add(project)
    db.session.commit()
    return project


def main():
    app = create_app()
    with app.app_context():
        user = ensure_user()
        project = ensure_project(user)
        client = app.test_client()

        login_resp = client.post('/login', data={'email': user.email, 'password': 'password'}, follow_redirects=True)
        assert login_resp.status_code == 200

        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, 'w') as zf:
            zf.writestr('src/app.py', "print('debug upload')")
            zf.writestr('README.md', '# debug upload')
        buffer.seek(0)

        upload_resp = client.post(
            f'/api/projects/{project.id}/upload-zip',
            data={'file': (buffer, 'debug.zip')},
            content_type='multipart/form-data'
        )
        print('Upload status:', upload_resp.status_code)
        print('Upload body:', upload_resp.get_data(as_text=True))

        status_resp = client.get(f'/api/projects/{project.id}/sync-status')
        print('Sync status:', status_resp.status_code)
        print('Sync body:', status_resp.get_data(as_text=True))


if __name__ == '__main__':
    main()
import io
import zipfile

from app import create_app
from app.extensions import db
from app.models import User, Project
from werkzeug.security import generate_password_hash


def ensure_user():
    user = User.query.filter_by(email='test_upload@example.com').first()
    if user:
        return user
    user = User(
        email='test_upload@example.com',
        username='testupload',
        password_hash=generate_password_hash('password')
    )
    db.session.add(user)
    db.session.commit()
    return user


def ensure_project(user):
    project = Project.query.filter_by(name='Upload Debug Project', creator_id=user.id).first()
    if project:
        return project
    project = Project(name='Upload Debug Project', slug='upload-debug-project', creator_id=user.id)
    db.session.add(project)
    db.session.commit()
    return project


def main():
    app = create_app()
    with app.app_context():
        user = ensure_user()
        project = ensure_project(user)
        client = app.test_client()

        login_resp = client.post('/login', data={'email': user.email, 'password': 'password'}, follow_redirects=True)
        assert login_resp.status_code == 200

        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, 'w') as zf:
            zf.writestr('src/app.py', "print('debug upload')")
            zf.writestr('README.md', '# debug upload')
        buffer.seek(0)

        upload_resp = client.post(
            f'/api/projects/{project.id}/upload-zip',
            data={'file': (buffer, 'debug.zip')},
            content_type='multipart/form-data'
        )
        print('Upload status:', upload_resp.status_code)
        print('Upload body:', upload_resp.get_data(as_text=True))

        status_resp = client.get(f'/api/projects/{project.id}/sync-status')
        print('Sync status:', status_resp.status_code)
        print('Sync body:', status_resp.get_data(as_text=True))


if __name__ == '__main__':
    main()

