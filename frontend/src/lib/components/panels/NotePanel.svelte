<script lang="ts">
	import type { Tag, Note } from '$lib/types';
	import { notes, loadNotes } from '$lib/stores/notes';
	import { tags, loadTags, entityTagsVersion } from '$lib/stores/tags';
	import { projects } from '$lib/stores/projects';
	import { activities } from '$lib/stores/activities';
	import { dateFilter, isItemVisible, selectedFilterTags, isTagVisible, showArchived, showActiveRelated, activeEntityTagIds, isActiveRelated } from '$lib/stores/dateFilter';
	import { getLastUsedTags, setLastUsedTags } from '$lib/stores/lastUsedTags';
	import { deleteNote, archiveNote } from '$lib/api/notes';
	import { getEntityTags, attachTag, detachTag } from '$lib/api/tags';
	import PanelContainer from '../shared/PanelContainer.svelte';
	import ConfirmDialog from '../shared/ConfirmDialog.svelte';
	import QuickNoteForm from '../forms/QuickNoteForm.svelte';
	import TagInput from '../shared/TagInput.svelte';
	import TagBadge from '../shared/TagBadge.svelte';
	import RichContent from '../shared/RichContent.svelte';
	import Timestamp from '../shared/Timestamp.svelte';
	import { selectEntity } from '$lib/stores/selectedEntity';
	import { selectable } from '$lib/actions/selectable';

	// Panel-level tag filter state
	let panelSelectedTagIds = $state<number[]>([]);
	let panelFilterMode = $state<'or' | 'and'>('or');

	// Get unique tags available in this panel
	let availablePanelTags = $derived(() => {
		const tagMap = new Map<number, Tag>();
		for (const note of $notes) {
			const noteTags = entityTags[note.id] || [];
			for (const tag of noteTags) {
				tagMap.set(tag.id, tag);
			}
		}
		return Array.from(tagMap.values()).sort((a, b) =>
			`${a.category}:${a.name}`.localeCompare(`${b.category}:${b.name}`)
		);
	});

	// Check if item passes panel-level tag filter
	function passesPanelFilter(itemTags: Tag[]): boolean {
		if (panelSelectedTagIds.length === 0) return true;
		if (panelFilterMode === 'or') {
			return itemTags.some(t => panelSelectedTagIds.includes(t.id));
		} else {
			return panelSelectedTagIds.every(id => itemTags.some(t => t.id === id));
		}
	}

	let filteredNotes = $derived($notes.filter(n =>
		($showArchived || !n.is_archived) &&
		isItemVisible(n, $dateFilter) &&
		isTagVisible(entityTags[n.id] || [], $selectedFilterTags) &&
		passesPanelFilter(entityTags[n.id] || []) &&
		(!$showActiveRelated || isActiveRelated(entityTags[n.id] || [], $activeEntityTagIds))
	));

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

	async function handleDelete(id: number) {
		await deleteNote(id);
		await Promise.all([loadNotes(), loadTags()]);
		confirmDelete = null;
	}

	async function handleArchive(id: number) {
		await archiveNote(id);
		await loadNotes();
	}

	async function toggleExpand(id: number) {
		if (expandedId === id) { expandedId = null; return; }
		expandedId = id;
		if (!entityTags[id]) {
			entityTags[id] = await getEntityTags('note', id);
		}
	}

	async function handleAttach(noteId: number, tag: Tag) {
		await attachTag(tag.id, 'note', noteId);
		entityTags[noteId] = await getEntityTags('note', noteId);
		// Update last-used tags
		setLastUsedTags('note', entityTags[noteId]);
	}

	async function handleDetach(noteId: number, tag: Tag) {
		await detachTag(tag.id, 'note', noteId);
		entityTags[noteId] = await getEntityTags('note', noteId);
		// Update last-used tags
		setLastUsedTags('note', entityTags[noteId]);
	}

	async function handleCreate(noteId: number) {
		// Get tags for active projects and activities
		const activeProjectIds = $projects.filter(p => p.is_active).map(p => p.id);
		const activeActivityIds = $activities.filter(a => a.is_active).map(a => a.id);

		const activeEntityTags = $tags.filter(t =>
			(t.entity_type === 'project' && t.entity_id && activeProjectIds.includes(t.entity_id)) ||
			(t.entity_type === 'activity' && t.entity_id && activeActivityIds.includes(t.entity_id))
		);

		// Also get last-used tags (filtering out inactive ones)
		const activeProjectsList = $projects.filter(p => p.is_active);
		const activeActivitiesList = $activities.filter(a => a.is_active);
		const lastUsed = getLastUsedTags('note', activeProjectsList, activeActivitiesList);

		// Combine and deduplicate
		const allTags = [...activeEntityTags];
		for (const tag of lastUsed) {
			if (!allTags.some(t => t.id === tag.id)) {
				allTags.push(tag);
			}
		}

		for (const tag of allTags) {
			try {
				await attachTag(tag.id, 'note', noteId);
			} catch (e) {
				console.warn(`Failed to attach tag ${tag.id} to note ${noteId}:`, e);
			}
		}

		if (allTags.length > 0) {
			entityTags[noteId] = await getEntityTags('note', noteId);
		}
	}

	async function loadAllTags() {
		const entries = await Promise.all(
			$notes.map(async (note) => [note.id, await getEntityTags('note', note.id)] as const)
		);
		const updated: Record<number, Tag[]> = {};
		for (const [id, tags] of entries) updated[id] = tags;
		entityTags = updated;
	}

	$effect(() => {
		const _ = $entityTagsVersion;  // Subscribe to version changes
		if ($notes) loadAllTags();
	});
</script>

<PanelContainer
	title="Notes"
	panelId="note"
	color="#6b8e6b"
	grow
	availableTags={availablePanelTags()}
	selectedTagIds={panelSelectedTagIds}
	filterMode={panelFilterMode}
	onTagToggle={handlePanelTagToggle}
	onModeToggle={handlePanelModeToggle}
>
	<QuickNoteForm onCreate={handleCreate} />

	{#each filteredNotes as note (note.id)}
		{#if editingIds.has(note.id)}
			<QuickNoteForm editData={note} onDone={() => { editingIds.delete(note.id); editingIds = new Set(editingIds); }} />
		{:else}
			<div class="item" class:is-archived={note.is_archived} use:selectable={{ entityType: 'note', entityId: note.id }}>
				<div class="item-actions">
					<button class="btn-tags" onclick={() => toggleExpand(note.id)}>Tags</button>
					<button class="btn-archive" onclick={() => handleArchive(note.id)}>Archive</button>
					<button class="btn-delete" onclick={() => (confirmDelete = note.id)}>Delete</button>
				</div>
				<div class="item-card" ondblclick={() => selectEntity('note', note.id, note.title)} role="button" tabindex="-1">
					<div class="item-header">
						<button class="item-title" ondblclick={() => { editingIds.add(note.id); editingIds = new Set(editingIds); }}>{note.title}</button>
						{#if note.is_archived}<span class="archived-badge">archived</span>{/if}
					</div>
					{#if note.content}
						<p class="item-desc"><RichContent text={note.content} /></p>
					{/if}
					{#if entityTags[note.id]?.length}
						<div class="tag-badges">
							{#each entityTags[note.id] as tag (tag.id)}
								<TagBadge {tag} removable onRemove={() => handleDetach(note.id, tag)} />
							{/each}
						</div>
					{/if}
					<Timestamp date={note.created_at} />
				</div>
				{#if expandedId === note.id}
					<div class="tag-section">
						<TagInput
							attachedTags={entityTags[note.id] || []}
							targetType="note"
							targetId={note.id}
							onAttach={(tag) => handleAttach(note.id, tag)}
							onDetach={(tag) => handleDetach(note.id, tag)}
							onClose={() => (expandedId = null)}
						/>
					</div>
				{/if}
			</div>
		{/if}
	{/each}

	{#if $notes.length === 0}
		<p class="empty">No notes yet.</p>
	{:else if filteredNotes.length === 0}
		<p class="empty">No notes match current filters.</p>
	{/if}
</PanelContainer>

<ConfirmDialog
	open={confirmDelete !== null}
	message="Delete this note?"
	onConfirm={() => confirmDelete && handleDelete(confirmDelete)}
	onCancel={() => (confirmDelete = null)}
/>

<style>
	.item { padding: 12px 0; border-bottom: 1px solid #e5e7eb; }
	.item-actions { display: flex; gap: 6px; margin-bottom: 6px; }
	.item-card { padding: 10px 12px; background: #fafafa; border: 1px solid #e5e7eb; border-radius: 8px; }
	.item-header { display: flex; align-items: center; gap: 8px; }
	.item-title { flex: 1; background: none; border: none; cursor: pointer; font-weight: 500; font-size: 0.9rem; text-align: left; padding: 0; color: #111827; }
	.item-desc { font-size: 0.8rem; color: #6b7280; margin: 8px 0 0; white-space: pre-wrap; }
	.tag-badges { display: flex; flex-wrap: wrap; gap: 4px; margin-top: 8px; }
	.btn-tags { font-size: 0.7rem; padding: 2px 8px; border-radius: 4px; border: 1px solid #d1d5db; cursor: pointer; background: #f9fafb; color: #6b7280; }
	.btn-archive { font-size: 0.7rem; padding: 2px 8px; border-radius: 4px; border: 1px solid #d1d5db; cursor: pointer; background: #fef3c7; color: #92400e; }
	.btn-delete { font-size: 0.75rem; padding: 2px 8px; background: #fee2e2; color: #ef4444; border: 1px solid #fecaca; border-radius: 4px; cursor: pointer; }
	.tag-section { margin-top: 8px; padding: 8px; background: #f9fafb; border-radius: 6px; }
	.empty { text-align: center; color: #9ca3af; font-size: 0.875rem; }
	.is-archived .item-card { opacity: 0.55; border-style: dashed; }
	.archived-badge { font-size: 0.55rem; padding: 1px 5px; background: #fef2f2; color: #b91c1c; border: 1px solid #fecaca; border-radius: 3px; text-transform: uppercase; letter-spacing: 0.3px; font-weight: 600; flex-shrink: 0; }
</style>
