(() => {
    const getCsrfToken = () => {
        const meta = document.querySelector('meta[name="csrf-token"]');
        return meta ? meta.getAttribute('content') : '';
    };

    const notify = (message, type = 'info') => {
        if (typeof window.showToast === 'function') {
            window.showToast({ message, type });
        } else if (message) {
            window.alert(message);
        }
    };

    const formatBytes = (bytes = 0) => {
        if (!bytes || bytes <= 0) return '0 B';
        const units = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(1024));
        return `${(bytes / Math.pow(1024, i)).toFixed(i === 0 ? 0 : 1)} ${units[i]}`;
    };

    const encodePath = (relativePath = '') =>
        relativePath.split('/').map(encodeURIComponent).join('/');

    const extensionOf = (path = '') => {
        const parts = path.split('.');
        return parts.length > 1 ? parts.pop().toLowerCase() : '';
    };

    class WorkspaceManager {
        constructor(rootEl) {
            this.root = rootEl;
            this.projectId = rootEl.dataset.projectId;
            this.zipUrl = rootEl.dataset.zipUrl;
            this.fileUrl = rootEl.dataset.fileUrl;
            this.finalizeUrl = rootEl.dataset.finalizeUrl;
            this.cancelUrlTemplate = rootEl.dataset.cancelUrlTemplate;
            this.statusUrl = rootEl.dataset.statusUrl;
            this.treeUrl = rootEl.dataset.treeUrl;
            this.signUrl = rootEl.dataset.signUrl;
            this.downloadBase = rootEl.dataset.downloadBase;
            this.canManage = rootEl.dataset.canManage === 'true';
            this.enabled = rootEl.dataset.enabled !== 'false';
            this.previewLimit = 2 * 1024 * 1024;
            this.zipLimitMb = parseInt(rootEl.dataset.zipLimitMb || '0', 10);
            this.fileLimitMb = parseInt(rootEl.dataset.fileLimitMb || '0', 10);

            if (!this.zipUrl) {
                console.warn('Workspace ZIP URL non configurato. Le funzionalità di upload saranno disabilitate.');
            }
            this.zipBtn = document.getElementById('workspace-upload-zip-btn');
            this.fileBtn = document.getElementById('workspace-upload-file-btn');
            this.zipInput = document.getElementById('workspace-zip-input');
            this.fileInput = document.getElementById('workspace-file-input');
            this.cliToggle = document.getElementById('workspace-cli-toggle');
            this.cliPanel = document.getElementById('workspace-cli-panel');
            this.sessionsList = document.getElementById('workspace-sessions-list');
            this.historyList = document.getElementById('workspace-history-list');
            this.fileTreeEl = document.getElementById('workspace-file-tree');
            this.fileViewerEl = document.getElementById('workspace-file-viewer');
            this.viewerTitleEl = document.getElementById('workspace-viewer-title');
            this.viewerActionsEl = document.getElementById('workspace-viewer-actions');
            this.refreshTreeBtn = document.getElementById('workspace-refresh-tree');
            this.progressContainer = document.getElementById('workspace-upload-progress');
            this.progressBar = document.getElementById('workspace-upload-progress-bar');
            this.progressLabel = document.getElementById('workspace-upload-progress-label');
            this.uploadLockMessage = document.getElementById('workspace-upload-lock');
            this.activeSessions = [];
            this.lastSessions = [];

            if (rootEl.dataset.sessions) {
                try {
                    const initialSessions = JSON.parse(rootEl.dataset.sessions) || [];
                    this.lastSessions = initialSessions;
                    this.activeSessions = initialSessions.filter((s) => {
                        const status = s.status || 'pending';
                        return !['completed', 'error'].includes(status);
                    });
                } catch (error) {
                    console.warn('Impossibile analizzare le sessioni iniziali del workspace', error);
                }
            }
            if (this.enabled) {
                this.bindEvents();
                this.refresh();
                if (this.fileTreeEl) {
                    this.loadFileTree();
                }
            }

            this.updateUploadButtonsState();
        }

        bindEvents() {
            if (this.zipBtn && this.zipInput) {
                this.zipBtn.addEventListener('click', () => this.zipInput.click());
                this.zipInput.addEventListener('change', (evt) => {
                    const file = evt.target.files?.[0];
                    if (file) {
                        this.uploadZip(file);
                        this.zipInput.value = '';
                    }
                });
            }

            if (this.fileBtn && this.fileInput) {
                this.fileBtn.addEventListener('click', () => this.fileInput.click());
                this.fileInput.addEventListener('change', (evt) => {
                    const file = evt.target.files?.[0];
                    if (file) {
                        this.uploadFile(file, file.name);
                        this.fileInput.value = '';
                    }
                });
            }

            if (this.cliToggle && this.cliPanel) {
                this.cliToggle.addEventListener('click', () => this.cliPanel.classList.toggle('hidden'));
            }

            if (this.refreshTreeBtn) {
                this.refreshTreeBtn.addEventListener('click', () => this.loadFileTree());
            }

            if (this.fileTreeEl) {
                this.fileTreeEl.addEventListener('click', (event) => {
                    const link = event.target.closest('.workspace-file-link');
                    if (link) {
                        event.preventDefault();
                        this.previewFile(link.dataset.path, parseInt(link.dataset.size || '0', 10), link.dataset.mime || '');
                    }
                });
            }

            this.root.addEventListener('click', (event) => {
                const finalizeBtn = event.target.closest('.workspace-finalize-btn');
                if (finalizeBtn && this.canManage) {
                    event.preventDefault();
                    const sessionId = finalizeBtn.dataset.sessionId;
                    if (sessionId) {
                        this.finalizeSession(sessionId, finalizeBtn);
                    }
                    return;
                }

                const cancelBtn = event.target.closest('.workspace-cancel-btn');
                if (cancelBtn && this.canManage) {
                    event.preventDefault();
                    const sessionId = cancelBtn.dataset.sessionId;
                    if (sessionId) {
                        this.cancelSession(sessionId, cancelBtn);
                    }
                }
            });
        }

        async uploadZip(file) {
            if (!this.zipUrl) {
                notify('Endpoint di upload ZIP non disponibile', 'error');
                return;
            }

            await this.refresh();
            if (this.isUploadLocked()) {
                notify('Esiste già una sessione attiva. Completa o annulla prima di caricare un nuovo ZIP.', 'warning');
                return;
            }

            this.activeSessions = [{ session_id: 'uploading', status: 'in_progress' }];
            this.updateUploadButtonsState();

            const formData = new FormData();
            formData.append('file', file, file.name);
            try {
                this.showProgress(`ZIP • ${file.name}`);
                const { status, payload } = await this.uploadWithProgress(this.zipUrl, formData, (value) => this.updateProgress(value));

                if (status === 413 && this.zipLimitMb) {
                    throw new Error(`Il file ZIP supera il limite consentito (${this.zipLimitMb} MB).`);
                }
                if (status < 200 || status >= 300 || !payload?.success) {
                    throw new Error(payload?.error || `Caricamento ZIP fallito (status ${status})`);
                }

                // Show success message with GitHub sync status if available
                let successMessage = `ZIP caricato (${payload.file_count} file)`;
                if (payload.github_sync) {
                    if (payload.github_sync.async) {
                        // Async sync (Celery fallback)
                        successMessage += ` • ⏳ ${payload.github_sync.message}`;
                    } else if (payload.github_sync.success) {
                        // Sync completato (git o API)
                        const method = payload.github_sync.method === 'git' ? 'Git' : 'GitHub';
                        const commitInfo = payload.github_sync.commit_url 
                            ? ` • <a href="${payload.github_sync.commit_url}" target="_blank">Vedi commit</a>`
                            : '';
                        successMessage += ` • ✅ Sincronizzato su GitHub via ${method} (${payload.github_sync.files_synced || 0} file)${commitInfo}`;
                    } else {
                        successMessage += ` • ⚠️ Sync GitHub fallito: ${payload.github_sync.error || payload.github_sync.message}`;
                    }
                }
                notify(successMessage, 'success');

                // Start polling if async sync is running
                if (payload.github_sync && payload.github_sync.async) {
                    this.startPolling(payload.session_id);
                }

                await this.hydrateSessionFromServer(payload.session_id, 'extracted', payload);

                await new Promise((resolve) => setTimeout(resolve, 750));
                await this.refresh();
                if (this.fileTreeEl) {
                    this.loadFileTree();
                }
            } catch (error) {
                console.error('Upload ZIP fallito:', error);
                notify(error.message, 'error');
            } finally {
                // Only clear active sessions if NOT polling
                if (!this.pollingInterval) {
                    this.activeSessions = [];
                    this.updateUploadButtonsState();
                }
                this.hideProgress();
            }
        }

        startPolling(sessionId) {
            if (this.pollingInterval) clearInterval(this.pollingInterval);

            let attempts = 0;
            const maxAttempts = 60; // 2 minutes (2s interval)

            this.pollingInterval = setInterval(async () => {
                attempts++;
                try {
                    await this.refresh();

                    // Find session
                    const session = this.lastSessions.find(s => s.session_id === sessionId);
                    if (!session) {
                        if (attempts > 5) this.stopPolling(); // Session disappeared?
                        return;
                    }

                    if (['completed', 'error'].includes(session.status)) {
                        this.stopPolling();
                        this.activeSessions = [];
                        this.updateUploadButtonsState();

                        if (session.status === 'completed') {
                            notify('✅ Sincronizzazione GitHub completata!', 'success');
                            if (this.fileTreeEl) this.loadFileTree();
                        } else {
                            notify(`⚠️ Sincronizzazione fallita: ${session.error || 'Errore sconosciuto'}`, 'error');
                        }
                    } else if (attempts >= maxAttempts) {
                        this.stopPolling();
                        notify('⚠️ Timeout attesa sincronizzazione (controlla più tardi)', 'warning');
                        this.activeSessions = [];
                        this.updateUploadButtonsState();
                    }
                } catch (e) {
                    console.error("Polling error:", e);
                }
            }, 2000);
        }

        stopPolling() {
            if (this.pollingInterval) {
                clearInterval(this.pollingInterval);
                this.pollingInterval = null;
            }
        }

        async uploadFile(file, relativePath) {
            if (!this.fileUrl) {
                notify('Endpoint di upload file non disponibile', 'error');
                return;
            }

            await this.refresh();
            if (this.isUploadLocked()) {
                notify('Esiste già una sessione attiva. Completa o annulla prima di caricare un nuovo file.', 'warning');
                return;
            }

            this.activeSessions = [{ session_id: 'uploading-file', status: 'in_progress' }];
            this.updateUploadButtonsState();

            const formData = new FormData();
            formData.append('file', file, file.name);
            formData.append('relative_path', relativePath);
            try {
                this.showProgress(`File • ${relativePath}`);
                const { status, payload } = await this.uploadWithProgress(this.fileUrl, formData, (value) => this.updateProgress(value));

                if (status === 413 && this.fileLimitMb) {
                    throw new Error(`Il file supera il limite consentito (${this.fileLimitMb} MB).`);
                }
                if (status < 200 || status >= 300 || !payload?.success) {
                    throw new Error(payload?.error || `Upload file fallito (status ${status})`);
                }
                notify(`File caricato: ${relativePath}`, 'info');

                await this.hydrateSessionFromServer(payload.session_id, 'in_progress', {
                    file_count: payload.file_count || 1,
                    total_size: payload.total_size || file.size
                });
                await this.refresh();
                if (this.fileTreeEl) {
                    this.loadFileTree();
                }
            } catch (error) {
                console.error('Upload file fallito:', error);
                notify(error.message, 'error');
            } finally {
                this.activeSessions = [];
                this.updateUploadButtonsState();
                this.hideProgress();
            }
        }

        async finalizeSession(sessionId, button) {
            if (button) {
                button.disabled = true;
                button.textContent = 'Sincronizzazione...';
            }
            try {
                const response = await fetch(this.finalizeUrl, {
                    method: 'POST',
                    credentials: 'include',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRF-Token': getCsrfToken()
                    },
                    body: JSON.stringify({ session_id: sessionId })
                });
                const payload = await WorkspaceManager.parseJsonResponse(response);
                if (!response.ok || !payload?.success) {
                    throw new Error(payload?.error || `Finalizzazione fallita (status ${response.status})`);
                }
                
                // Mostra messaggio appropriato in base al metodo di sync
                let message = '';
                if (payload.status === 'completed' && payload.method === 'git') {
                    const commitInfo = payload.commit_url 
                        ? ` • <a href="${payload.commit_url}" target="_blank" class="underline">Vedi commit</a>`
                        : '';
                    message = `✅ Sincronizzato via Git (${payload.files_synced || 0} file)${commitInfo}`;
                } else if (payload.status === 'syncing' && payload.method === 'celery') {
                    message = '⏳ Sincronizzazione avviata in background (Celery). Controlla lo stato tra pochi secondi.';
                    this.startPolling(sessionId);
                } else {
                    message = 'Sync avviato. Controlla lo stato tra pochi secondi.';
                }
                
                notify(message, 'success');
                await this.refresh();
                if (this.fileTreeEl) {
                    this.loadFileTree();
                }
            } catch (error) {
                console.error(error);
                notify(error.message, 'error');
            } finally {
                if (button) {
                    button.disabled = false;
                    button.textContent = 'Finalizza e sincronizza →';
                }
            }
        }

        buildCancelUrl(sessionId) {
            if (!this.cancelUrlTemplate) return '';
            return this.cancelUrlTemplate.replace('__SESSION__', encodeURIComponent(sessionId));
        }

        async cancelSession(sessionId, button) {
            if (!this.cancelUrlTemplate) return;
            if (!window.confirm('Vuoi davvero annullare questa sessione di upload? I file caricati andranno persi.')) {
                return;
            }
            const url = this.buildCancelUrl(sessionId);
            const originalContent = button.innerHTML;
            button.disabled = true;
            button.textContent = 'Annullamento…';
            try {
                const response = await fetch(url, {
                    method: 'DELETE',
                    credentials: 'include',
                    headers: {
                        'X-CSRF-Token': getCsrfToken()
                    }
                });
                const payload = await WorkspaceManager.parseJsonResponse(response);
                if (!response.ok || !payload?.success) {
                    throw new Error(payload?.error || `Impossibile annullare la sessione (status ${response.status})`);
                }
                notify('Sessione annullata', 'info');
                await this.refresh();
            } catch (error) {
                console.error(error);
                notify(error.message, 'error');
            } finally {
                button.disabled = false;
                button.innerHTML = originalContent;
            }
        }

        async refresh() {
            try {
                const response = await fetch(this.statusUrl, { credentials: 'include' });
                const payload = await response.json();

                if (!response.ok || !payload.success) {
                    throw new Error(payload.error || 'Impossibile aggiornare lo stato workspace');
                }
                if (payload.sessions && payload.sessions.length) {
                    this.lastSessions = payload.sessions;
                    this.updateSessions(payload.sessions);
                } else {
                    this.updateSessions(this.lastSessions);
                }
                this.updateHistory(payload.history, payload.sessions || []);
            } catch (error) {
                console.error('Workspace status update failed', error);
            }
        }

        updateSessions(sessions = []) {
            if (!this.sessionsList) return;

            this.activeSessions = sessions.filter((session) => {
                const status = session.status || 'pending';
                return !['completed', 'error'].includes(status);
            });
            this.updateUploadButtonsState();

            if (!sessions.length) {
                this.sessionsList.innerHTML = '<p class="text-gray-500 text-sm">Nessuna sessione aperta.</p>';
                return;
            }
            this.sessionsList.innerHTML = sessions.map((session) => {
                const status = session.status || 'pending';
                const labelClass = {
                    ready: 'bg-blue-100 text-blue-700',
                    completed: 'bg-green-100 text-green-700',
                    error: 'bg-red-100 text-red-700',
                    syncing: 'bg-purple-100 text-purple-700',
                    pending: 'bg-gray-100 text-gray-600',
                    in_progress: 'bg-yellow-100 text-yellow-700',
                    extracted: 'bg-blue-100 text-blue-700',
                }[status] || 'bg-gray-100 text-gray-600';
                const actions = [];
                if (this.canManage) {
                    if (['in_progress', 'extracted', 'ready'].includes(status)) {
                        actions.push(`<button type="button" class="workspace-finalize-btn text-sm font-semibold text-primary-600 hover:text-primary-700 focus-ring-subtle" data-session-id="${session.session_id}">
                            Finalizza e sincronizza →
                        </button>`);
                    }
                    if (!['syncing', 'completed'].includes(status)) {
                        actions.push(`<button type="button" class="workspace-cancel-btn text-sm font-semibold text-gray-500 hover:text-red-600 focus-ring-subtle" data-session-id="${session.session_id}">
                            Annulla
                        </button>`);
                    }
                }
                return `
                    <div class="border border-dashed border-gray-300 rounded-lg p-3 text-sm">
                        <div class="flex justify-between items-center mb-1">
                            <span class="font-semibold">#${(session.session_id || '').slice(0, 8)}…</span>
                            <span class="text-xs px-2 py-0.5 rounded-full ${labelClass}">
                                ${status}
                            </span>
                        </div>
                        <p class="text-gray-600">${session.file_count || 0} file · ${formatBytes(session.total_size)}</p>
                        ${actions.length ? `<div class="mt-2 flex flex-wrap gap-2">${actions.join('')}</div>` : ''}
                    </div>
                `;
            }).join('');
        }

        updateHistory(history = [], fallbackSessions = []) {
            if (!this.historyList) return;
            if (!history.length) {
                if (fallbackSessions.length) {
                    this.historyList.innerHTML = fallbackSessions.map((session) => {
                        const status = session.status || 'pending';
                        const label = status.charAt(0).toUpperCase() + status.slice(1);
                        const timestamp = session.sync_finished_at || session.updated_at || session.created_at || '';
                        return `
                            <div class="text-sm border border-dashed border-gray-300 rounded-lg p-3">
                                <p class="font-semibold text-gray-800">${label} · ${session.file_count || 0} file</p>
                                <p class="text-xs text-gray-500">${timestamp}</p>
                            </div>
                        `;
                    }).join('');
                    return;
                }
                this.historyList.innerHTML = '<p class="text-gray-500 text-sm">Nessun sync registrato.</p>';
                return;
            }
            this.historyList.innerHTML = history.map((event) => `
                <div class="text-sm border border-dashed border-gray-300 rounded-lg p-3">
                    <p class="font-semibold text-gray-800">
                        ${(event.status || '').charAt(0).toUpperCase() + (event.status || '').slice(1)} · ${event.file_count || 0} file
                    </p>
                    <p class="text-xs text-gray-500">${event.completed_at || event.created_at || ''}</p>
                    ${event.error ? `<p class="text-xs text-red-600 mt-1">Errore: ${event.error}</p>` : ''}
                </div>
            `).join('');
        }

        async uploadWithProgress(url, formData, onProgress) {
            return new Promise((resolve, reject) => {
                const xhr = new XMLHttpRequest();
                xhr.open('POST', url);
                xhr.withCredentials = true;
                const csrf = getCsrfToken();
                if (csrf) {
                    xhr.setRequestHeader('X-CSRF-Token', csrf);
                }
                if (xhr.upload && typeof onProgress === 'function') {
                    xhr.upload.addEventListener('progress', (event) => {
                        if (event.lengthComputable) {
                            const progress = event.loaded / event.total;
                            console.log(`[WORKSPACE] Upload progress: ${(progress * 100).toFixed(0)}%`);
                            onProgress(progress);
                        }
                    });
                }
                xhr.onload = async () => {
                    const payload = await WorkspaceManager.parseJsonResponseFromXHR(xhr);
                    resolve({ status: xhr.status, payload });
                };
                xhr.onerror = (error) => {
                    reject(new Error('Errore di rete durante il caricamento'));
                };
                xhr.onabort = () => {
                    reject(new Error('Upload annullato'));
                };
                xhr.ontimeout = () => {
                    reject(new Error('Timeout durante upload'));
                };
                xhr.send(formData);
            });
        }

        static safeJsonParse(text) {
            try {
                return text ? JSON.parse(text) : null;
            } catch {
                return null;
            }
        }

        showProgress(label = '') {
            if (!this.progressContainer) return;
            this.progressContainer.classList.remove('hidden');
            this.progressContainer.style.display = 'block';
            if (this.progressLabel) {
                this.progressLabel.textContent = label || 'Caricamento in corso...';
            }
            this.updateProgress(0);
        }

        updateProgress(value = 0) {
            if (!this.progressBar) return;
            const clamped = Math.min(Math.max(value, 0), 1);
            const percentage = (clamped * 100).toFixed(0);
            this.progressBar.style.width = `${percentage}%`;
            this.progressBar.setAttribute('aria-valuenow', percentage);
            this.progressBar.setAttribute('aria-valuemin', '0');
            this.progressBar.setAttribute('aria-valuemax', '100');
            // Aggiorna anche il label con la percentuale
            if (this.progressLabel && value > 0 && value < 1) {
                const currentText = this.progressLabel.textContent.split(' • ')[0];
                this.progressLabel.textContent = `${currentText} • ${percentage}%`;
            }
        }

        hideProgress() {
            if (!this.progressContainer) return;
            // Attendi un po' prima di nascondere per mostrare il 100%
            setTimeout(() => {
                if (this.progressContainer) {
                    this.progressContainer.classList.add('hidden');
                    this.progressContainer.style.display = 'none';
                    this.updateProgress(0);
                    if (this.progressLabel) {
                        this.progressLabel.textContent = '';
                    }
                }
            }, 500);
        }

        isUploadLocked() {
            return Array.isArray(this.activeSessions) && this.activeSessions.length > 0;
        }

        updateUploadButtonsState() {
            const locked = this.isUploadLocked();
            [this.zipBtn, this.fileBtn].forEach((btn) => {
                if (btn) {
                    btn.disabled = locked;
                    if (locked) {
                        btn.classList.add('opacity-50', 'cursor-not-allowed');
                    } else {
                        btn.classList.remove('opacity-50', 'cursor-not-allowed');
                    }
                }
            });
            if (this.uploadLockMessage) {
                if (locked && this.activeSessions.length > 0) {
                    const activeCount = this.activeSessions.length;
                    const current = this.activeSessions[0];
                    let label = '';
                    if (activeCount > 1) {
                        label = `${activeCount} sessioni attive in corso`;
                    } else if (current?.session_id && current.session_id !== 'uploading') {
                        label = `Sessione #${current.session_id.slice(0, 8)}… in corso`;
                    } else {
                        label = 'Upload in corso';
                    }
                    const textNode = this.uploadLockMessage.querySelector('span:last-child');
                    if (textNode) {
                        textNode.textContent = `${label}. Completa o annulla prima di caricare altro.`;
                    }
                    this.uploadLockMessage.classList.remove('hidden');
                } else {
                    this.uploadLockMessage.classList.add('hidden');
                }
            }
        }

        async loadFileTree() {
            if (!this.fileTreeEl || !this.treeUrl) return;
            this.fileTreeEl.innerHTML = '<p class="text-gray-500 text-sm py-3">Caricamento file…</p>';
            try {
                const response = await fetch(this.treeUrl, { credentials: 'include' });
                const payload = await response.json();
                if (!response.ok || !payload.success) {
                    throw new Error(payload.error || 'Impossibile caricare la lista file');
                }
                this.renderFileTree(payload.files || []);
            } catch (error) {
                console.error(error);
                this.fileTreeEl.innerHTML = `<p class="text-red-600 text-sm py-3">${error.message}</p>`;
            }
        }

        renderFileTree(files = []) {
            if (!files.length) {
                this.fileTreeEl.innerHTML = '<p class="text-gray-500 text-sm py-3">Nessun file sincronizzato ancora.</p>';
                return;
            }
            const iconFor = (path) => {
                const ext = extensionOf(path);
                if (['png', 'jpg', 'jpeg', 'gif', 'webp', 'svg'].includes(ext)) return 'image';
                if (['pdf'].includes(ext)) return 'picture_as_pdf';
                if (['glb', 'gltf', 'obj', 'stl'].includes(ext)) return 'view_in_ar';
                if (['md', 'txt'].includes(ext)) return 'description';
                return 'article';
            };
            this.fileTreeEl.innerHTML = files.map((file) => `
                <button class="workspace-file-link w-full flex items-center justify-between gap-3 py-2 px-3 hover:bg-gray-50 transition text-left"
                        data-path="${file.path}"
                        data-size="${file.size || 0}"
                        data-mime="${file.mime || ''}">
                    <span class="flex items-center gap-2 text-gray-700">
                        <span class="material-icons text-base text-gray-500">${iconFor(file.path)}</span>
                        <span class="truncate">${file.path}</span>
                    </span>
                    <span class="text-xs text-gray-400 flex-shrink-0">${formatBytes(file.size)}</span>
                </button>
            `).join('');
        }

        async previewFile(relativePath, size = 0, mime = '') {
            if (!this.fileViewerEl || !this.signUrl) return;
            this.setViewerState('Caricamento preview…');
            try {
                const token = await this.requestFileToken(relativePath);
                const downloadUrl = this.buildDownloadUrl(relativePath, token);
                const actionsHtml = `
                    <a href="${downloadUrl}" target="_blank" rel="noopener" class="text-primary-500 font-semibold hover:text-primary-600 flex items-center gap-1">
                        <span class="material-icons text-base">download</span>
                        Scarica
                    </a>
                `;
                if (this.viewerActionsEl) this.viewerActionsEl.innerHTML = actionsHtml;
                if (this.viewerTitleEl) this.viewerTitleEl.textContent = relativePath;

                if (size > this.previewLimit) {
                    this.setViewerState('File troppo grande per la preview. Usa il link Download.', false);
                    return;
                }

                if (mime.startsWith('image/')) {
                    this.fileViewerEl.innerHTML = `<img src="${downloadUrl}" alt="${relativePath}" class="max-h-[420px] w-full object-contain rounded-lg">`;
                    return;
                }

                const ext = extensionOf(relativePath);
                if (ext === 'pdf') {
                    this.fileViewerEl.innerHTML = `<iframe src="${downloadUrl}" class="w-full h-[420px] rounded-lg border" loading="lazy"></iframe>`;
                    return;
                }

                if (['glb', 'gltf', 'obj', 'stl'].includes(ext) && window.customElements?.get('model-viewer')) {
                    this.fileViewerEl.innerHTML = `<model-viewer src="${downloadUrl}" camera-controls autoplay style="width:100%;height:420px;background:#0f172a;border-radius:0.75rem;"></model-viewer>`;
                    return;
                }

                if (ext === 'md' || mime === 'text/markdown') {
                    const response = await fetch(downloadUrl, { credentials: 'include' });
                    const text = await response.text();
                    const html = window.marked ? window.marked.parse(text) : text;
                    this.fileViewerEl.innerHTML = `<div class="prose prose-slate max-w-none">${html}</div>`;
                    return;
                }

                if (['txt', 'py', 'js', 'ts', 'json', 'html', 'css', 'java', 'c', 'cpp', 'rs', 'go', 'rb', 'php', 'swift'].includes(ext)) {
                    const response = await fetch(downloadUrl, { credentials: 'include' });
                    const text = await response.text();
                    const language = this.mapLanguage(ext);
                    const codeBlock = document.createElement('pre');
                    codeBlock.className = 'rounded-lg bg-slate-900 text-slate-100 p-4 overflow-x-auto text-sm';
                    codeBlock.innerHTML = `<code class="language-${language}">${this.escapeHtml(text)}</code>`;
                    this.fileViewerEl.innerHTML = '';
                    this.fileViewerEl.appendChild(codeBlock);
                    if (window.hljs) {
                        window.hljs.highlightElement(codeBlock.querySelector('code'));
                    }
                    return;
                }

                const response = await fetch(downloadUrl, { credentials: 'include' });
                const text = await response.text();
                this.fileViewerEl.innerHTML = `<pre class="bg-gray-50 border rounded-lg p-3 text-xs overflow-x-auto">${this.escapeHtml(text)}</pre>`;
            } catch (error) {
                console.error(error);
                this.setViewerState(error.message || 'Impossibile caricare il file', true);
            }
        }

        async requestFileToken(relativePath) {
            const response = await fetch(this.signUrl, {
                method: 'POST',
                credentials: 'include',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRF-Token': getCsrfToken()
                },
                body: JSON.stringify({ path: relativePath })
            });
            const payload = await WorkspaceManager.parseJsonResponse(response);
            if (!response.ok || !payload?.success) {
                throw new Error(payload?.error || 'Impossibile generare il token');
            }
            return payload.token;
        }

        buildDownloadUrl(relativePath, token) {
            if (!this.downloadBase) return '#';
            const base = this.downloadBase.endsWith('/') ? this.downloadBase.slice(0, -1) : this.downloadBase;
            const encoded = encodePath(relativePath);
            return `${base}/${encoded}?token=${encodeURIComponent(token)}`;
        }

        setViewerState(message, isError = false) {
            if (this.viewerTitleEl) this.viewerTitleEl.textContent = isError ? 'Errore' : 'Preview';
            if (this.viewerActionsEl) this.viewerActionsEl.innerHTML = '';
            if (this.fileViewerEl) {
                this.fileViewerEl.innerHTML = `<p class="${isError ? 'text-red-600' : 'text-gray-500'} text-sm">${message}</p>`;
            }
        }

        mapLanguage(ext) {
            const mapping = {
                js: 'javascript',
                ts: 'typescript',
                py: 'python',
                rb: 'ruby',
                rs: 'rust',
                c: 'c',
                cpp: 'cpp',
                h: 'c',
                java: 'java',
                go: 'go',
                php: 'php',
                html: 'html',
                css: 'css',
                json: 'json',
                md: 'markdown'
            };
            return mapping[ext] || 'plaintext';
        }

        escapeHtml(text) {
            return text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
        }

        unshiftSession(session) {
            if (!session?.session_id) return;
            this.lastSessions = [
                session,
                ...this.lastSessions.filter((existing) => existing.session_id !== session.session_id)
            ].slice(0, 10);
            this.updateSessions(this.lastSessions);
        }

        async hydrateSessionFromServer(sessionId, fallbackStatus = 'pending', fallback = {}) {
            if (!sessionId || !this.statusUrl) {
                return;
            }

            try {
                const url = new URL(this.statusUrl, window.location.origin);
                url.searchParams.set('session_id', sessionId);
                const response = await fetch(url.toString(), { credentials: 'include' });
                if (!response.ok) {
                    throw new Error(`Impossibile recuperare la sessione (status ${response.status})`);
                }
                const payload = await response.json();
                const sessionMeta = WorkspaceManager.normalizeSessionMetadata(payload.metadata) ||
                    WorkspaceManager.normalizeSessionMetadata({
                        session_id: sessionId,
                        status: fallbackStatus,
                        file_count: fallback.file_count,
                        total_size: fallback.total_size,
                        created_at: new Date().toISOString(),
                        updated_at: new Date().toISOString()
                    });
                if (sessionMeta) {
                    this.unshiftSession(sessionMeta);
                }
            } catch (error) {
                console.warn('Impossibile recuperare la sessione aggiornata:', error);
                const sessionMeta = WorkspaceManager.normalizeSessionMetadata({
                    session_id: sessionId,
                    status: fallbackStatus,
                    file_count: fallback.file_count,
                    total_size: fallback.total_size,
                    created_at: new Date().toISOString(),
                    updated_at: new Date().toISOString()
                });
                if (sessionMeta) {
                    this.unshiftSession(sessionMeta);
                }
            }
        }

        static normalizeSessionMetadata(metadata = {}) {
            if (!metadata.session_id) return null;
            const fileCount = metadata.file_count || (metadata.files ? metadata.files.length : 0);
            const totalSize = metadata.total_size || (metadata.files
                ? metadata.files.reduce((sum, file) => sum + (file.size || 0), 0)
                : 0
            );
            return {
                session_id: metadata.session_id,
                status: metadata.status || 'pending',
                type: metadata.type || (metadata.upload_type || 'zip'),
                file_count: fileCount,
                total_size: totalSize,
                created_at: metadata.created_at || new Date().toISOString(),
                updated_at: metadata.updated_at || metadata.created_at || new Date().toISOString(),
                finalized_at: metadata.finalized_at || null
            };
        }

        static async parseJsonResponse(response) {
            const contentType = response.headers.get('content-type') || '';
            if (contentType.includes('application/json')) {
                return response.json().catch(() => null);
            }
            const text = await response.text();
            try {
                return text ? JSON.parse(text) : null;
            } catch {
                console.error('Impossibile interpretare la risposta JSON:', text);
                return null;
            }
        }

        static async parseJsonResponseFromXHR(xhr) {
            const responseText = xhr.responseText;
            if (xhr.responseType === 'json' && xhr.response) {
                return xhr.response;
            }
            try {
                return responseText ? JSON.parse(responseText) : null;
            } catch {
                console.error('Impossibile interpretare la risposta JSON dall\'XHR:', responseText);
                return null;
            }
        }
    }

    document.addEventListener('DOMContentLoaded', () => {
        console.log('[WORKSPACE] DOM loaded, cercando #project-workspace...');
        const root = document.getElementById('project-workspace');
        if (root) {
            console.log('[WORKSPACE] Elemento trovato, inizializzazione WorkspaceManager...');
            new WorkspaceManager(root);
        } else {
            console.error('[WORKSPACE] ERRORE: elemento #project-workspace non trovato!');
            alert('ERRORE: Workspace non trovato nella pagina!');
        }
    });
})();

