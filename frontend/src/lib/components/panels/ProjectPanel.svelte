<script lang="ts">
	import type { Tag, Project } from '$lib/types';
	import { projects, loadProjects } from '$lib/stores/projects';
	import { tags, loadTags, entityTagsVersion } from '$lib/stores/tags';
	import { activities } from '$lib/stores/activities';
	import { dateFilter, isItemVisible, selectedFilterTags, isTagVisible, isEntitySourceOfFilterTag, showArchived, showActiveRelated, activeEntityTagIds, isActiveRelated } from '$lib/stores/dateFilter';
	import { setLastUsedTags } from '$lib/stores/lastUsedTags';
	import { deleteProject, updateProject, activateProject, deactivateProject, archiveProject } from '$lib/api/projects';
	import { getEntityTags, attachTag, detachTag } from '$lib/api/tags';
	import PanelContainer from '../shared/PanelContainer.svelte';
	import ConfirmDialog from '../shared/ConfirmDialog.svelte';
	import ProjectForm from '../forms/ProjectForm.svelte';
	import TagInput from '../shared/TagInput.svelte';
	import TagBadge from '../shared/TagBadge.svelte';
	import Timestamp from '../shared/Timestamp.svelte';
	import { selectEntity } from '$lib/stores/selectedEntity';
	import { selectable } from '$lib/actions/selectable';


	// Panel-level tag filter state
	let panelSelectedTagIds = $state<number[]>([]);
	let panelFilterMode = $state<'or' | 'and'>('or');

	let availablePanelTags = $derived(() => {
		const tagMap = new Map<number, Tag>();
		for (const project of $projects) {
			const projectTags = entityTags[project.id] || [];
			for (const tag of projectTags) {
				tagMap.set(tag.id, tag);
			}
		}
		return Array.from(tagMap.values()).sort((a, b) =>
			`${a.category}:${a.name}`.localeCompare(`${b.category}:${b.name}`)
		);
	});

	function passesPanelFilter(itemTags: Tag[]): boolean {
		if (panelSelectedTagIds.length === 0) return true;
		if (panelFilterMode === 'or') {
			return itemTags.some(t => panelSelectedTagIds.includes(t.id));
		} else {
			return panelSelectedTagIds.every(id => itemTags.some(t => t.id === id));
		}
	}

	let filteredProjects = $derived($projects.filter(p =>
		($showArchived || !p.is_archived) &&
		isItemVisible(p, $dateFilter) &&
		(isTagVisible(entityTags[p.id] || [], $selectedFilterTags) || isEntitySourceOfFilterTag('project', p.id, $selectedFilterTags)) &&
		passesPanelFilter(entityTags[p.id] || []) &&
		(!$showActiveRelated || isActiveRelated(entityTags[p.id] || [], $activeEntityTagIds, p.is_active))
	));

	let showForm = $state(false);
	let editingIds = $state<Set<number>>(new Set());
	let confirmDelete: number | null = $state(null);
	let expandedId: number | null = $state(null);
	let entityTags = $state<Record<number, Tag[]>>({});

	function handlePanelTagToggle(tagId: number) {
		if (panelSelectedTagIds.includes(tagId)) {
			panelSelectedTagIds = panelSelectedTagIds.filter(id => id !== tagId);
		} else {
			panelSelectedTagIds = [...panelSelectedTagIds, tagId];
		}
	}

	function handlePanelModeToggle() {
		panelFilterMode = panelFilterMode === 'or' ? 'and' : 'or';
	}

	const PROJECT_STATUS_CYCLE = ['planned', 'in_progress', 'done', 'on_hold', 'cancelled'];

	function formatStatus(status: string): string {
		return status.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
	}

	async function cycleProjectStatus(project: Project) {
		const idx = PROJECT_STATUS_CYCLE.indexOf(project.status);
		const next = PROJECT_STATUS_CYCLE[(idx + 1) % PROJECT_STATUS_CYCLE.length];
		await updateProject(project.id, { status: next });
		await loadProjects();
	}

	async function handleDelete(id: number) {
		await deleteProject(id);
		await Promise.all([loadProjects(), loadTags()]);
		confirmDelete = null;
	}

	async function toggleActive(id: number, isActive: boolean) {
		if (isActive) { await deactivateProject(id); } else { await activateProject(id); }
		await loadProjects();
	}

	async function handleArchive(id: number) {
		await archiveProject(id);
		await loadProjects();
	}

	async function toggleExpand(id: number) {
		if (expandedId === id) { expandedId = null; return; }
		expandedId = id;
		if (!entityTags[id]) {
			entityTags[id] = await getEntityTags('project', id);
		}
	}

	async function handleAttach(projectId: number, tag: Tag) {
		await attachTag(tag.id, 'project', projectId);
		entityTags[projectId] = await getEntityTags('project', projectId);
		setLastUsedTags('project', entityTags[projectId]);
	}

	async function handleDetach(projectId: number, tag: Tag) {
		await detachTag(tag.id, 'project', projectId);
		entityTags[projectId] = await getEntityTags('project', projectId);
		setLastUsedTags('project', entityTags[projectId]);
	}

	async function handleCreate(projectId: number) {
		// Get tags for active projects and activities
		const activeProjectIds = $projects.filter(p => p.is_active && !p.is_archived).map(p => p.id);
		const activeActivityIds = $activities.filter(a => a.is_active && !a.is_archived).map(a => a.id);

		const activeEntityTags = $tags.filter(t =>
			(t.entity_type === 'project' && t.entity_id && activeProjectIds.includes(t.entity_id)) ||
			(t.entity_type === 'activity' && t.entity_id && activeActivityIds.includes(t.entity_id))
		);

		for (const tag of activeEntityTags) {
			try {
				await attachTag(tag.id, 'project', projectId);
			} catch (e) {
				console.warn(`Failed to attach tag ${tag.id} to project ${projectId}:`, e);
			}
		}

		if (activeEntityTags.length > 0) {
			entityTags[projectId] = await getEntityTags('project', projectId);
		}
	}

	async function loadAllTags() {
		const entries = await Promise.all(
			$projects.map(async (project) => [project.id, await getEntityTags('project', project.id)] as const)
		);
		const updated: Record<number, Tag[]> = {};
		for (const [id, tags] of entries) updated[id] = tags;
		entityTags = updated;
	}

	$effect(() => {
		const _ = $entityTagsVersion;  // Subscribe to version changes
		if ($projects) loadAllTags();
	});
</script>

<PanelContainer
	title="Projects"
	panelId="project"
	color="#5c7a99"
	onAdd={() => (showForm = !showForm)}
	availableTags={availablePanelTags()}
	selectedTagIds={panelSelectedTagIds}
	filterMode={panelFilterMode}
	onTagToggle={handlePanelTagToggle}
	onModeToggle={handlePanelModeToggle}
>
	{#if showForm}
		<div class="inline-form">
			<ProjectForm onDone={() => (showForm = false)} onCreate={handleCreate} />
		</div>
	{/if}

	{#each filteredProjects as project (project.id)}
		{#if editingIds.has(project.id)}
			<div class="inline-form">
				<ProjectForm editData={project} onDone={() => { editingIds.delete(project.id); editingIds = new Set(editingIds); }} />
			</div>
		{:else}
			<div class="item" class:is-archived={project.is_archived} use:selectable={{ entityType: 'project', entityId: project.id }}>
				<div class="item-actions">
					<button class="btn-tags" onclick={() => toggleExpand(project.id)}>Tags</button>
					<button class="btn-active" class:active={project.is_active} onclick={() => toggleActive(project.id, project.is_active)}>
						{project.is_active ? 'Active' : 'Inactive'}
					</button>
					<button class="btn-archive" onclick={() => handleArchive(project.id)}>Archive</button>
					<button class="btn-delete" onclick={() => (confirmDelete = project.id)}>Delete</button>
				</div>
				<div class="item-card" ondblclick={() => selectEntity('project', project.id, project.title)} role="button" tabindex="-1">
					<div class="item-header">
						<button class="item-title" ondblclick={() => { editingIds.add(project.id); editingIds = new Set(editingIds); }}>{project.title}</button>
						{#if project.is_archived}<span class="archived-badge">archived</span>{/if}
						<button class="status-btn" class:status-planned={project.status === 'planned'} class:status-done={project.status === 'done'} class:status-in-progress={project.status === 'in_progress'} class:status-on-hold={project.status === 'on_hold'} class:status-cancelled={project.status === 'cancelled'} onclick={(e) => { e.stopPropagation(); cycleProjectStatus(project); }}>{formatStatus(project.status)}</button>
					</div>
					{#if project.description}
						<p class="item-desc">{project.description}</p>
					{/if}
					{#if entityTags[project.id]?.length}
						<div class="tag-badges">
							{#each entityTags[project.id] as tag (tag.id)}
								<TagBadge {tag} removable onRemove={() => handleDetach(project.id, tag)} />
							{/each}
						</div>
					{/if}
					<Timestamp date={project.created_at} />
				</div>
				{#if expandedId === project.id}
					<div class="tag-section">
						<TagInput
							attachedTags={entityTags[project.id] || []}
							targetType="project"
							targetId={project.id}
							onAttach={(tag) => handleAttach(project.id, tag)}
							onDetach={(tag) => handleDetach(project.id, tag)}
							onClose={() => (expandedId = null)}
						/>
					</div>
				{/if}
			</div>
		{/if}
	{/each}

	{#if $projects.length === 0}
		<p class="empty">No projects yet.</p>
	{:else if filteredProjects.length === 0}
		<p class="empty">No projects match current filters.</p>
	{/if}
</PanelContainer>

<ConfirmDialog
	open={confirmDelete !== null}
	message="Delete this project? Its tag will be removed from all entities."
	onConfirm={() => confirmDelete && handleDelete(confirmDelete)}
	onCancel={() => (confirmDelete = null)}
/>

<style>
	.inline-form { padding: 10px; background: #eff6ff; border: 1px solid #bfdbfe; border-radius: 8px; margin-bottom: 12px; }
	.item { padding: 12px 0; border-bottom: 1px solid #e5e7eb; }
	.item-actions { display: flex; gap: 6px; margin-bottom: 6px; }
	.item-card { padding: 10px 12px; background: #fafafa; border: 1px solid #e5e7eb; border-radius: 8px; }
	.item-header { display: flex; align-items: center; gap: 8px; }
	.item-title { flex: 1; background: none; border: none; cursor: pointer; font-weight: 500; font-size: 0.9rem; text-align: left; padding: 0; color: #111827; }
	.item-desc { font-size: 0.8rem; color: #6b7280; margin: 8px 0 0; }
	.status-btn { font-size: 0.65rem; padding: 2px 6px; background: #e5e7eb; border-radius: 4px; color: #374151; flex-shrink: 0; border: 1px solid transparent; cursor: pointer; font-weight: 500; }
	.status-btn:hover { filter: brightness(0.95); }
	.status-btn.status-planned { background: #f3f4f6; color: #9ca3af; }
	.status-btn.status-done { background: #dcfce7; color: #16a34a; }
	.status-btn.status-in-progress { background: #fef3c7; color: #d97706; }
	.status-btn.status-on-hold { background: #fef9c3; color: #a16207; }
	.status-btn.status-cancelled { background: #fee2e2; color: #dc2626; }
	.btn-active { font-size: 0.7rem; padding: 2px 8px; border-radius: 4px; border: 1px solid #d1d5db; cursor: pointer; background: #f3f4f6; color: #6b7280; }
	.btn-active.active { background: #dcfce7; color: #16a34a; border-color: #bbf7d0; }
	.tag-badges { display: flex; flex-wrap: wrap; gap: 4px; margin-top: 8px; }
	.btn-tags { font-size: 0.7rem; padding: 2px 8px; border-radius: 4px; border: 1px solid #d1d5db; cursor: pointer; background: #f9fafb; color: #6b7280; }
	.btn-archive { font-size: 0.7rem; padding: 2px 8px; border-radius: 4px; border: 1px solid #d1d5db; cursor: pointer; background: #fef3c7; color: #92400e; }
	.btn-delete { font-size: 0.75rem; padding: 2px 8px; background: #fee2e2; color: #ef4444; border: 1px solid #fecaca; border-radius: 4px; cursor: pointer; }
	.tag-section { margin-top: 8px; padding: 8px; background: #f9fafb; border-radius: 6px; }
	.empty { text-align: center; color: #9ca3af; font-size: 0.875rem; }
	.is-archived .item-card { opacity: 0.55; border-style: dashed; }
	.archived-badge { font-size: 0.55rem; padding: 1px 5px; background: #fef2f2; color: #b91c1c; border: 1px solid #fecaca; border-radius: 3px; text-transform: uppercase; letter-spacing: 0.3px; font-weight: 600; flex-shrink: 0; }
	.btn-icon-nav { width: 24px; height: 24px; display: flex; align-items: center; justify-content: center; border: 1px solid #d1d5db; border-radius: 4px; background: white; cursor: pointer; color: #9ca3af; transition: all 0.15s; }
	.btn-icon-nav:hover { border-color: #9ca3af; color: #6b7280; background: #f3f4f6; }
</style>
