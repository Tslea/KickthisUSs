
content = """{% extends "base.html" %}

{% block title %}{{ project.name }}{% endblock %}

{% block head_extra %}
<style>
.task-progress-bar-fill {
    width: var(--progress-value, 0%);
}
</style>
{% endblock %}

{% block content %}
<main class="bg-black min-h-screen text-white py-12">
    {% set is_creator = current_user.is_authenticated and current_user.id == project.creator_id %}
    {% set collaborator_entry = project.collaborators.filter_by(user_id=current_user.id).first() if current_user.is_authenticated else None %}
    {% set is_collaborator = collaborator_entry is not none %}
    
    <div class="max-w-7xl mx-auto px-6">
        
        {# 1. PROJECT HEADER - MINIMAL & BOLD #}
        <div class="mb-16">
            <div class="flex flex-col md:flex-row justify-between items-start md:items-end gap-6 mb-8">
                <div>
                    <div class="flex items-center gap-3 mb-4">
                        <span class="px-3 py-1 bg-gray-900 border border-gray-800 rounded-full text-xs font-medium text-gray-400 uppercase tracking-wider">
                            {{ project.category | title }}
                        </span>
                        {% if project.is_scientific %}
                        <span class="px-3 py-1 bg-blue-900/30 border border-blue-800 rounded-full text-xs font-medium text-blue-400 uppercase tracking-wider">
                            🔬 Ricerca
                        </span>
                        {% else %}
                        <span class="px-3 py-1 bg-green-900/30 border border-green-800 rounded-full text-xs font-medium text-green-400 uppercase tracking-wider">
                            ☀️ Commerciale
                        </span>
                        {% endif %}
                    </div>
                    
                    <h1 class="text-5xl md:text-7xl font-bold font-display leading-tight mb-2">
                        {{ project.name }}
                    </h1>
                    
                    <div class="flex items-center gap-2 text-gray-500">
                        <span>by</span>
                        <a href="{{ url_for('users.user_profile', username=project.creator.username) }}" class="text-white hover:underline font-medium">
                            {{ project.creator.username }}
                        </a>
                        <span class="mx-2">•</span>
                        <span>{{ project.created_at | format_datetime('%d %B %Y') }}</span>
                    </div>
                </div>

                <div class="flex gap-4">
                    {% if current_user.id == project.creator_id %}
                        <a href="{{ url_for('projects.edit_project_form', project_id=project.id) }}" 
                           class="px-6 py-3 bg-gray-900 border border-gray-800 text-white rounded-lg hover:bg-gray-800 transition-colors font-medium">
                            Modifica
                        </a>
                    {% endif %}
                    
                    {% if current_user.is_authenticated and not project.private %}
                        {% if not user_has_voted_this_month %}
                            <button data-project-id="{{ project.id }}"
                                    onclick="voteProject(this.dataset.projectId, this);"
                                    class="px-6 py-3 bg-accent text-white rounded-lg hover:bg-red-600 transition-colors font-bold shadow-glow">
                                Vota Progetto
                            </button>
                        {% else %}
                             <button class="px-6 py-3 bg-gray-800 text-gray-400 rounded-lg cursor-not-allowed font-medium">
                                Già Votato
                            </button>
                        {% endif %}
                    {% endif %}
                </div>
            </div>

            {# Pitch Section #}
            <div class="bg-gray-900 border border-gray-800 rounded-2xl p-8 md:p-10">
                <h3 class="text-xl font-bold font-display mb-4 text-gray-400">IL PITCH</h3>
                <p class="text-xl md:text-2xl leading-relaxed text-gray-200 font-light">
                    {% if project.rewritten_pitch %}
                        {{ project.rewritten_pitch | nl2br }}
                    {% else %}
                        {{ project.pitch }}
                    {% endif %}
                </p>
                
                {% if current_user.id == project.creator_id and not project.rewritten_pitch %}
                    <div class="mt-6">
                        <a href="{{ url_for('projects.edit_project_form', project_id=project.id) }}" class="text-accent hover:text-white transition-colors text-sm font-medium flex items-center gap-2">
                            <span class="material-icons text-sm">auto_awesome</span>
                            Migliora con AI
                        </a>
                    </div>
                {% endif %}
            </div>
        </div>

        <div class="grid grid-cols-1 lg:grid-cols-3 gap-12">
            
            {# LEFT COLUMN - MAIN CONTENT #}
            <div class="lg:col-span-2 space-y-12">
                
                {# Milestones / Roadmap #}
                {% if milestones %}
                <section>
                    <div class="flex justify-between items-end mb-6">
                        <h2 class="text-3xl font-bold font-display">Roadmap</h2>
                        <a href="{{ url_for('milestones.milestones_list', project_id=project.id) }}" class="text-gray-500 hover:text-white text-sm transition-colors">
                            Vedi tutte →
                        </a>
                    </div>
                    
                    <div class="space-y-4">
                        {% for milestone in milestones[:3] %}
                        <div class="group flex items-start gap-6 p-6 bg-gray-900 border border-gray-800 rounded-xl hover:border-gray-700 transition-colors">
                            <div class="flex-shrink-0 mt-1">
                                {% if milestone.completed %}
                                    <div class="w-6 h-6 rounded-full bg-green-500/20 border border-green-500 flex items-center justify-center">
                                        <div class="w-2 h-2 bg-green-500 rounded-full"></div>
                                    </div>
                                {% else %}
                                    <div class="w-6 h-6 rounded-full bg-gray-800 border border-gray-700 group-hover:border-gray-500 transition-colors"></div>
                                {% endif %}
                            </div>
                            <div>
                                <h3 class="text-lg font-bold text-white mb-1 {{ 'line-through text-gray-500' if milestone.completed }}">
                                    {{ milestone.title }}
                                </h3>
                                <p class="text-gray-400 text-sm mb-3">{{ milestone.description }}</p>
                                {% if milestone.target_date %}
                                    <div class="text-xs text-gray-600 font-mono">
                                        TARGET: {{ milestone.target_date.strftime('%d.%m.%Y') }}
                                    </div>
                                {% endif %}
                            </div>
                        </div>
                        {% endfor %}
                    </div>
                </section>
                {% endif %}

                {# Tasks Section #}
                <section>
                    <div class="flex justify-between items-end mb-6">
                        <h2 class="text-3xl font-bold font-display">Tasks Aperti</h2>
                        {% if is_creator %}
                        <a href="{{ url_for('tasks.create_task', project_id=project.id) }}" class="text-accent hover:text-white text-sm font-bold transition-colors">
                            + NUOVO TASK
                        </a>
                        {% endif %}
                    </div>

                    {# Filter Tabs (Simplified) #}
                    <div class="flex gap-4 mb-8 overflow-x-auto pb-2 border-b border-gray-800">
                        <a href="?status=open" class="text-white font-medium border-b-2 border-white pb-2">Aperti</a>
                        <a href="?status=in_progress" class="text-gray-500 hover:text-white transition-colors pb-2">In Corso</a>
                        <a href="?status=completed" class="text-gray-500 hover:text-white transition-colors pb-2">Completati</a>
                    </div>

                    <div class="grid gap-6">
                        {% for task in tasks %}
                            {% include 'partials/_task_card_tailwind.html' %}
                        {% else %}
                            <div class="text-center py-12 border border-dashed border-gray-800 rounded-xl">
                                <p class="text-gray-500">Nessun task attivo al momento.</p>
                            </div>
                        {% endfor %}
                    </div>
                </section>

            </div>

            {# RIGHT COLUMN - SIDEBAR #}
            <div class="space-y-8">
                
                {# Equity / Stats Card #}
                <div class="bg-gray-900 border border-gray-800 rounded-xl p-6">
                    <h3 class="text-sm font-bold text-gray-500 uppercase tracking-wider mb-6">Project Equity</h3>
                    
                    <div class="space-y-6">
                        <div>
                            <div class="text-3xl font-bold text-white font-display">{{ project.total_equity_distributed }}%</div>
                            <div class="text-sm text-gray-500">Equity Distribuita</div>
                        </div>
                        
                        <div>
                            <div class="text-3xl font-bold text-white font-display">{{ project.collaborators.count() }}</div>
                            <div class="text-sm text-gray-500">Collaboratori Attivi</div>
                        </div>
                    </div>

                    <div class="mt-8 pt-8 border-t border-gray-800">
                        <a href="{{ url_for('projects.project_equity', project_id=project.id) }}" class="block w-full py-3 bg-white text-black text-center font-bold rounded-lg hover:bg-gray-200 transition-colors">
                            Vedi Cap Table
                        </a>
                    </div>
                </div>

                {# Team / Collaborators #}
                <div>
                    <h3 class="text-sm font-bold text-gray-500 uppercase tracking-wider mb-4">Team</h3>
                    <div class="flex flex-wrap gap-2">
                        {% for collaborator in project.collaborators %}
                            <a href="{{ url_for('users.user_profile', username=collaborator.user.username) }}" 
                               class="w-10 h-10 rounded-full bg-gray-800 border border-gray-700 flex items-center justify-center text-xs font-bold text-white hover:border-white transition-colors"
                               title="{{ collaborator.user.username }}">
                                {{ collaborator.user.username[:2].upper() }}
                            </a>
                        {% endfor %}
                        {% if is_creator %}
                            <a href="{{ url_for('invites.manage_project_invites', project_id=project.id) }}" 
                               class="w-10 h-10 rounded-full border border-dashed border-gray-600 flex items-center justify-center text-gray-500 hover:text-white hover:border-white transition-colors">
                                +
                            </a>
                        {% endif %}
                    </div>
                </div>

                {# Free Proposals Link #}
                {% if is_creator or is_collaborator %}
                <div class="bg-blue-900/20 border border-blue-900/50 rounded-xl p-6">
                    <h3 class="text-sm font-bold text-blue-400 uppercase tracking-wider mb-2">Proposte Libere</h3>
                    <p class="text-sm text-blue-200 mb-4">Gestisci le idee ricevute dalla community.</p>
                    <a href="{{ url_for('free_proposals.my_proposals', view='received', project_id=project.id) }}" class="text-blue-400 hover:text-white text-sm font-bold flex items-center gap-2">
                        Vai alla dashboard →
                    </a>
                </div>
                {% endif %}

            </div>
        </div>
    </div>
</main>
{% endblock %}
"""

with open(r"c:\Kick this Uss\KICK\KICKTHISUSS -DEF -ora - Copia - Copia\kickstorm_project\app\templates\project_detail.html", "w", encoding="utf-8") as f:
    f.write(content)
