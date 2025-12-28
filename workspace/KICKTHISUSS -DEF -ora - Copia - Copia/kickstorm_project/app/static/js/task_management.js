// Task Management Functions for Suggested Tasks

/**
 * Activate a suggested task
 */
function activateTask(taskId) {
    if (!confirm('Vuoi attivare questo task suggerito?')) {
        return;
    }

    // Show loading state
    const button = document.querySelector(`button.btn-activate-task[data-task-id="${taskId}"]`);
    if (button) {
        button.disabled = true;
        button.innerHTML = '<span class="material-icons text-xs animate-spin">refresh</span> Attivazione...';
    }

    fetch(`/api/task/${taskId}/activate`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest'
        }
    })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Show success message
                showNotification('Task attivato con successo!', 'success');

                // Reload page to update task cards
                setTimeout(() => {
                    window.location.reload();
                }, 1000);
            } else {
                showNotification(data.error || 'Errore durante l\'attivazione del task', 'error');
                if (button) {
                    button.disabled = false;
                    button.innerHTML = 'Attiva';
                }
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showNotification('Errore di connessione', 'error');
            if (button) {
                button.disabled = false;
                button.innerHTML = 'Attiva';
            }
        });
}

/**
 * Open edit modal for a suggested task
 */
function editTaskModal(taskId) {
    // Fetch task details
    fetch(`/api/task/${taskId}/details`, {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest'
        }
    })
        .then(response => response.json())
        .then(task => {
            // Create and show modal
            showTaskEditModal(task);
        })
        .catch(error => {
            console.error('Error:', error);
            showNotification('Errore nel caricamento dei dettagli del task', 'error');
        });
}

/**
 * Show task edit modal with form
 */
function showTaskEditModal(task) {
    // Create modal HTML
    const modalHTML = `
        <div id="editTaskModal" class="fixed inset-0 bg-black bg-opacity-75 flex items-center justify-center z-50 p-4">
            <div class="bg-gray-900 rounded-xl border border-gray-800 max-w-2xl w-full max-h-[90vh] overflow-y-auto">
                <div class="p-6 border-b border-gray-800 flex justify-between items-center">
                    <h3 class="text-xl font-bold text-white">Modifica Task Suggerito</h3>
                    <button onclick="closeTaskEditModal()" class="text-gray-400 hover:text-white">
                        <span class="material-icons">close</span>
                    </button>
                </div>
                
                <form id="editTaskForm" class="p-6 space-y-4">
                    <div>
                        <label class="block text-sm font-bold text-gray-400 mb-2">Titolo</label>
                        <input type="text" name="title" value="${task.title || ''}" 
                               class="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded text-white focus:border-blue-500 focus:outline-none" required>
                    </div>
                    
                    <div>
                        <label class="block text-sm font-bold text-gray-400 mb-2">Descrizione</label>
                        <textarea name="description" rows="4" 
                                  class="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded text-white focus:border-blue-500 focus:outline-none" required>${task.description || ''}</textarea>
                    </div>
                    
                    <div class="grid grid-cols-2 gap-4">
                        <div>
                            <label class="block text-sm font-bold text-gray-400 mb-2">Tipo Task</label>
                            <select name="task_type" class="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded text-white focus:border-blue-500 focus:outline-none">
                                <option value="proposal" ${task.task_type === 'proposal' ? 'selected' : ''}>Proposta</option>
                                <option value="implementation" ${task.task_type === 'implementation' ? 'selected' : ''}>Implementazione</option>
                                <option value="validation" ${task.task_type === 'validation' ? 'selected' : ''}>Validazione</option>
                            </select>
                        </div>
                        
                        <div>
                            <label class="block text-sm font-bold text-gray-400 mb-2">Difficoltà</label>
                            <select name="difficulty" class="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded text-white focus:border-blue-500 focus:outline-none">
                                <option value="Easy" ${task.difficulty === 'Easy' ? 'selected' : ''}>Facile</option>
                                <option value="Medium" ${task.difficulty === 'Medium' ? 'selected' : ''}>Media</option>
                                <option value="Hard" ${task.difficulty === 'Hard' ? 'selected' : ''}>Difficile</option>
                            </select>
                        </div>
                    </div>
                    
                    <div class="grid grid-cols-2 gap-4">
                        <div>
                            <label class="block text-sm font-bold text-gray-400 mb-2">Equity Reward</label>
                            <input type="number" name="equity_reward" value="${task.equity_reward || 1.0}" step="0.1" min="0.1"
                                   class="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded text-white focus:border-blue-500 focus:outline-none" required>
                        </div>
                        
                        <div>
                            <label class="block text-sm font-bold text-gray-400 mb-2">Fase</label>
                            <select name="phase" class="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded text-white focus:border-blue-500 focus:outline-none">
                                <option value="Planning" ${task.phase === 'Planning' ? 'selected' : ''}>Pianificazione</option>
                                <option value="Development" ${task.phase === 'Development' ? 'selected' : ''}>Sviluppo</option>
                                <option value="Testing" ${task.phase === 'Testing' ? 'selected' : ''}>Testing</option>
                                <option value="Deployment" ${task.phase === 'Deployment' ? 'selected' : ''}>Deployment</option>
                            </select>
                        </div>
                    </div>
                    
                    <div class="flex items-center gap-2">
                        <input type="checkbox" name="is_private" id="taskIsPrivate" ${task.is_private ? 'checked' : ''}
                               class="w-4 h-4 bg-gray-800 border-gray-700 rounded">
                        <label for="taskIsPrivate" class="text-sm text-gray-400">Task Privato</label>
                    </div>
                    
                    <div class="flex justify-end gap-3 pt-4 border-t border-gray-800">
                        <button type="button" onclick="closeTaskEditModal()" 
                                class="px-4 py-2 bg-gray-800 hover:bg-gray-700 text-white rounded transition-colors">
                            Annulla
                        </button>
                        <button type="submit" class="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded transition-colors">
                            Salva e Attiva
                        </button>
                    </div>
                </form>
            </div>
        </div>
    `;

    // Add modal to page
    document.body.insertAdjacentHTML('beforeend', modalHTML);

    // Add form submit handler
    document.getElementById('editTaskForm').addEventListener('submit', function (e) {
        e.preventDefault();
        submitTaskUpdate(task.id, new FormData(this));
    });
}

/**
 * Close task edit modal
 */
function closeTaskEditModal() {
    const modal = document.getElementById('editTaskModal');
    if (modal) {
        modal.remove();
    }
}

/**
 * Submit task update
 */
function submitTaskUpdate(taskId, formData) {
    const submitButton = document.querySelector('#editTaskForm button[type="submit"]');
    if (submitButton) {
        submitButton.disabled = true;
        submitButton.innerHTML = '<span class="material-icons text-xs animate-spin">refresh</span> Salvataggio...';
    }

    fetch(`/api/task/${taskId}/update-and-activate`, {
        method: 'POST',
        body: formData
    })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showNotification('Task aggiornato e attivato con successo!', 'success');
                setTimeout(() => {
                    window.location.reload();
                }, 1000);
            } else {
                showNotification(data.error || 'Errore durante l\'aggiornamento del task', 'error');
                if (submitButton) {
                    submitButton.disabled = false;
                    submitButton.innerHTML = 'Salva e Attiva';
                }
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showNotification('Errore di connessione', 'error');
            if (submitButton) {
                submitButton.disabled = false;
                submitButton.innerHTML = 'Salva e Attiva';
            }
        });
}

/**
 * Show notification message
 */
function showNotification(message, type = 'info') {
    // Try to use existing flash system if available
    if (typeof window.showFlash === 'function') {
        window.showFlash(message, type);
        return;
    }

    // Fallback: create simple notification
    const notification = document.createElement('div');
    notification.className = `fixed top-4 right-4 px-6 py-3 rounded-lg text-white z-50 ${type === 'success' ? 'bg-green-600' : type === 'error' ? 'bg-red-600' : 'bg-blue-600'
        }`;
    notification.textContent = message;

    document.body.appendChild(notification);

    setTimeout(() => {
        notification.remove();
    }, 3000);
}

console.log('Task management functions loaded');
