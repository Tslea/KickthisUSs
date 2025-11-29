import io
import os
import json
import shutil
import zipfile

from app.extensions import db
from tests.factories import ProjectFactory
from app.services.managed_repo_service import ManagedRepoService


def _create_zip_bytes(file_count: int = 1, forbidden_count: int = 0):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w') as zf:
        for idx in range(file_count):
            zf.writestr(f'src/file_{idx}.py', f'print("file {idx}")')
        for idx in range(forbidden_count):
            zf.writestr(f'node_modules/lib{idx}/index.js', 'console.log("skip me");')
    buffer.seek(0)
    return buffer


def test_upload_zip_session_visibility(app, authenticated_client, auth_user):
    """
    Uploads a ZIP file and ensures the created session appears in sync-status results.
    """
    zip_buffer = _create_zip_bytes(file_count=3)
    with app.app_context():
        project = ProjectFactory(creator=auth_user)
        db.session.add(project)
        db.session.commit()
        project_id = project.id
        ManagedRepoService().initialize_managed_repository(project)

    upload_resp = authenticated_client.post(
        f'/api/projects/{project_id}/upload-zip',
        data={'file': (zip_buffer, 'workspace.zip')},
        content_type='multipart/form-data'
    )
    assert upload_resp.status_code == 200, upload_resp.get_data(as_text=True)
    payload = upload_resp.get_json()
    assert payload['success'] is True
    session_id = payload['session_id']
    assert session_id

    status_resp = authenticated_client.get(f'/api/projects/{project_id}/sync-status')
    assert status_resp.status_code == 200, status_resp.get_data(as_text=True)
    status_payload = status_resp.get_json()
    sessions = status_payload.get('sessions', [])
    assert any(s.get('session_id') == session_id for s in sessions), (
        f"Session {session_id} not found in sync-status response {sessions}"
    )

    shutil.rmtree(app.config['PROJECT_WORKSPACE_ROOT'], ignore_errors=True)


def test_upload_zip_endpoint_authenticated(app, authenticated_client, auth_user):
    zip_buffer = _create_zip_bytes()
    with app.app_context():
        project = ProjectFactory(creator=auth_user)
        db.session.add(project)
        db.session.commit()
        project_id = project.id
        ManagedRepoService().initialize_managed_repository(project)
    response = authenticated_client.post(
        f'/api/projects/{project_id}/upload-zip',
        data={'file': (zip_buffer, 'code.zip')},
        content_type='multipart/form-data'
    )
    assert response.status_code == 200, response.get_data(as_text=True)
    payload = response.get_json()
    assert payload['success'] is True
    session_id = payload['session_id']
    assert session_id

    session_dir = os.path.join(app.config['PROJECT_WORKSPACE_ROOT'], str(project_id), 'incoming', session_id)
    metadata_path = os.path.join(session_dir, 'metadata.json')
    assert os.path.exists(metadata_path)
    with open(metadata_path, 'r', encoding='utf-8') as handle:
        metadata = json.load(handle)
    assert metadata['file_count'] == 1
    assert metadata['status'] == 'extracted'

    shutil.rmtree(app.config['PROJECT_WORKSPACE_ROOT'], ignore_errors=True)


def test_upload_zip_respects_file_limit(app, authenticated_client, auth_user):
    app.config['PROJECT_WORKSPACE_MAX_FILES'] = 5
    zip_buffer = _create_zip_bytes(file_count=7)
    with app.app_context():
        project = ProjectFactory(creator=auth_user)
        db.session.add(project)
        db.session.commit()
        project_id = project.id
        ManagedRepoService().initialize_managed_repository(project)
    response = authenticated_client.post(
        f'/api/projects/{project_id}/upload-zip',
        data={'file': (zip_buffer, 'too_many.zip')},
        content_type='multipart/form-data'
    )
    assert response.status_code == 400
    assert 'Troppi file' in response.get_data(as_text=True)
    shutil.rmtree(app.config['PROJECT_WORKSPACE_ROOT'], ignore_errors=True)


def test_upload_zip_ignores_forbidden_paths_for_limit(app, authenticated_client, auth_user):
    app.config['PROJECT_WORKSPACE_MAX_FILES'] = 5
    zip_buffer = _create_zip_bytes(file_count=4, forbidden_count=50)
    with app.app_context():
        project = ProjectFactory(creator=auth_user)
        db.session.add(project)
        db.session.commit()
        project_id = project.id
        ManagedRepoService().initialize_managed_repository(project)
    response = authenticated_client.post(
        f'/api/projects/{project_id}/upload-zip',
        data={'file': (zip_buffer, 'with_node_modules.zip')},
        content_type='multipart/form-data'
    )
    assert response.status_code == 200, response.get_data(as_text=True)
    payload = response.get_json()
    assert payload['file_count'] == 4
    shutil.rmtree(app.config['PROJECT_WORKSPACE_ROOT'], ignore_errors=True)


def test_upload_single_file_endpoint(app, authenticated_client, auth_user):
    data = {
        'relative_path': 'src/app.py',
        'file': (io.BytesIO(b"print('workspace')"), 'app.py')
    }
    with app.app_context():
        project = ProjectFactory(creator=auth_user)
        db.session.add(project)
        db.session.commit()
        project_id = project.id
        ManagedRepoService().initialize_managed_repository(project)
    response = authenticated_client.post(
        f'/api/projects/{project_id}/files',
        data=data,
        content_type='multipart/form-data'
    )
    assert response.status_code == 200, response.get_data(as_text=True)
    payload = response.get_json()
    assert payload['success'] is True
    session_id = payload['session_id']
    assert session_id

    session_dir = os.path.join(app.config['PROJECT_WORKSPACE_ROOT'], str(project_id), 'incoming', session_id)
    metadata_path = os.path.join(session_dir, 'metadata.json')
    assert os.path.exists(metadata_path)
    with open(metadata_path, 'r', encoding='utf-8') as handle:
        metadata = json.load(handle)
    assert metadata['type'] == 'manual'
    assert metadata['files'][0]['path'] == 'src/app.py'

    shutil.rmtree(app.config['PROJECT_WORKSPACE_ROOT'], ignore_errors=True)


def test_finalize_and_sync_status(app, authenticated_client, auth_user):
    with app.app_context():
        project = ProjectFactory(creator=auth_user)
        db.session.add(project)
        db.session.commit()
        project_id = project.id
        ManagedRepoService().initialize_managed_repository(project)

    upload_resp = authenticated_client.post(
        f'/api/projects/{project_id}/files',
        data={
            'relative_path': 'README.md',
            'file': (io.BytesIO(b"# KickthisUSs workspace"), 'README.md')
        },
        content_type='multipart/form-data'
    )
    session_id = upload_resp.get_json()['session_id']

    finalize_resp = authenticated_client.post(
        f'/api/projects/{project_id}/finalize-upload',
        json={'session_id': session_id}
    )
    assert finalize_resp.status_code == 200
    assert finalize_resp.get_json()['status'] in ('completed', 'ready')

    status_resp = authenticated_client.get(
        f'/api/projects/{project_id}/sync-status',
        query_string={'session_id': session_id}
    )
    assert status_resp.status_code == 200
    payload = status_resp.get_json()
    assert payload['metadata']['status'] in ('completed', 'ready')
    shutil.rmtree(app.config['PROJECT_WORKSPACE_ROOT'], ignore_errors=True)


def test_history_written_after_sync(app, authenticated_client, auth_user):
    with app.app_context():
        project = ProjectFactory(creator=auth_user)
        db.session.add(project)
        db.session.commit()
        project_id = project.id
        ManagedRepoService().initialize_managed_repository(project)

    upload_resp = authenticated_client.post(
        f'/api/projects/{project_id}/files',
        data={
            'relative_path': 'src/core.py',
            'file': (io.BytesIO(b"print('history')"), 'core.py')
        },
        content_type='multipart/form-data'
    )
    session_id = upload_resp.get_json()['session_id']

    authenticated_client.post(
        f'/api/projects/{project_id}/finalize-upload',
        json={'session_id': session_id}
    )

    history_path = os.path.join(app.config['PROJECT_WORKSPACE_ROOT'], str(project_id), 'history.json')
    assert os.path.exists(history_path)
    with open(history_path, 'r', encoding='utf-8') as handle:
        history = json.load(handle)
    assert history
    assert history[0]['session_id'] == session_id
    assert history[0]['file_count'] >= 1

    shutil.rmtree(app.config['PROJECT_WORKSPACE_ROOT'], ignore_errors=True)


def test_sync_status_without_session_returns_summary(app, authenticated_client, auth_user):
    with app.app_context():
        project = ProjectFactory(creator=auth_user)
        db.session.add(project)
        db.session.commit()
        project_id = project.id
        ManagedRepoService().initialize_managed_repository(project)

    upload_resp = authenticated_client.post(
        f'/api/projects/{project_id}/files',
        data={
            'relative_path': 'src/ui.js',
            'file': (io.BytesIO(b"console.log('ui');"), 'ui.js')
        },
        content_type='multipart/form-data'
    )
    session_id = upload_resp.get_json()['session_id']

    authenticated_client.post(
        f'/api/projects/{project_id}/finalize-upload',
        json={'session_id': session_id}
    )

    status_resp = authenticated_client.get(f'/api/projects/{project_id}/sync-status')
    assert status_resp.status_code == 200
    payload = status_resp.get_json()
    assert payload['success'] is True
    assert isinstance(payload['history'], list)
    assert isinstance(payload['sessions'], list)

    shutil.rmtree(app.config['PROJECT_WORKSPACE_ROOT'], ignore_errors=True)


def test_cancel_upload_session_removes_directory(app, authenticated_client, auth_user):
    with app.app_context():
        project = ProjectFactory(creator=auth_user)
        db.session.add(project)
        db.session.commit()
        project_id = project.id
        ManagedRepoService().initialize_managed_repository(project)

    upload_resp = authenticated_client.post(
        f'/api/projects/{project_id}/files',
        data={
            'relative_path': 'src/temp.txt',
            'file': (io.BytesIO(b'cancel me'), 'temp.txt')
        },
        content_type='multipart/form-data'
    )
    session_id = upload_resp.get_json()['session_id']

    session_dir = os.path.join(app.config['PROJECT_WORKSPACE_ROOT'], str(project_id), 'incoming', session_id)
    assert os.path.isdir(session_dir)

    delete_resp = authenticated_client.delete(f'/api/projects/{project_id}/sessions/{session_id}')
    assert delete_resp.status_code == 200, delete_resp.get_data(as_text=True)
    payload = delete_resp.get_json()
    assert payload['success'] is True

    assert not os.path.exists(session_dir)
    shutil.rmtree(app.config['PROJECT_WORKSPACE_ROOT'], ignore_errors=True)


def test_file_tree_and_download_flow(app, authenticated_client, auth_user):
    with app.app_context():
        project = ProjectFactory(creator=auth_user)
        db.session.add(project)
        db.session.commit()
        project_id = project.id
        ManagedRepoService().initialize_managed_repository(project)

    file_content = b"print('preview test')"
    upload_resp = authenticated_client.post(
        f'/api/projects/{project_id}/files',
        data={
            'relative_path': 'src/preview.py',
            'file': (io.BytesIO(file_content), 'preview.py')
        },
        content_type='multipart/form-data'
    )
    session_id = upload_resp.get_json()['session_id']

    authenticated_client.post(
        f'/api/projects/{project_id}/finalize-upload',
        json={'session_id': session_id}
    )

    tree_resp = authenticated_client.get(f'/api/projects/{project_id}/files/tree')
    assert tree_resp.status_code == 200
    files_payload = tree_resp.get_json()
    assert files_payload['success'] is True
    assert any(item['path'] == 'src/preview.py' for item in files_payload['files'])

    sign_resp = authenticated_client.post(
        f'/api/projects/{project_id}/files/sign',
        json={'path': 'src/preview.py'}
    )
    assert sign_resp.status_code == 200
    token = sign_resp.get_json()['token']

    download_resp = authenticated_client.get(
        f'/api/projects/{project_id}/files/src/preview.py',
        query_string={'token': token}
    )
    assert download_resp.status_code == 200
    assert download_resp.data == file_content

    shutil.rmtree(app.config['PROJECT_WORKSPACE_ROOT'], ignore_errors=True)


def test_download_rejects_invalid_token(app, authenticated_client, auth_user):
    with app.app_context():
        project = ProjectFactory(creator=auth_user)
        db.session.add(project)
        db.session.commit()
        project_id = project.id
        ManagedRepoService().initialize_managed_repository(project)

    upload_resp = authenticated_client.post(
        f'/api/projects/{project_id}/files',
        data={
            'relative_path': 'docs/info.txt',
            'file': (io.BytesIO(b"info"), 'info.txt')
        },
        content_type='multipart/form-data'
    )
    session_id = upload_resp.get_json()['session_id']
    authenticated_client.post(
        f'/api/projects/{project_id}/finalize-upload',
        json={'session_id': session_id}
    )

    download_resp = authenticated_client.get(
        f'/api/projects/{project_id}/files/docs/info.txt',
        query_string={'token': 'invalid'}
    )
    assert download_resp.status_code == 400

    shutil.rmtree(app.config['PROJECT_WORKSPACE_ROOT'], ignore_errors=True)

