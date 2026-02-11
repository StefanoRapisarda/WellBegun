<script lang="ts">
	import type { Tag, LearningTrack, LearningTrackItem, LearningGoal } from '$lib/types';
	import { learningTracks, loadLearningTracks } from '$lib/stores/learningTracks';
	import { sources } from '$lib/stores/sources';
	import { loadTags } from '$lib/stores/tags';
	import { dateFilter, isItemVisible } from '$lib/stores/dateFilter';
	import { deleteLearningTrack, activateLearningTrack, deactivateLearningTrack, addItem, updateItem, removeItem, addGoal, toggleGoal, removeGoal } from '$lib/api/learningTracks';
	import { getEntityTags, attachTag, detachTag } from '$lib/api/tags';
	import PanelContainer from '../shared/PanelContainer.svelte';
	import ConfirmDialog from '../shared/ConfirmDialog.svelte';
	import LearningTrackForm from '../forms/LearningTrackForm.svelte';
	import TagInput from '../shared/TagInput.svelte';
	import TagBadge from '../shared/TagBadge.svelte';
	import { selectEntity } from '$lib/stores/selectedEntity';
	import { selectable } from '$lib/actions/selectable';

	const STATUS_CYCLE = ['not_started', 'in_progress', 'completed'];
	const STATUS_COLORS: Record<string, string> = {
		not_started: '#9ca3af',
		in_progress: '#f59e0b',
		completed: '#10b981',
	};
	const STATUS_LABELS: Record<string, string> = {
		not_started: 'Not Started',
		in_progress: 'In Progress',
		completed: 'Completed',
	};

	let filteredTracks = $derived($learningTracks.filter(lt => isItemVisible(lt, $dateFilter)));
	let showForm = $state(false);
	let editingIds = $state<Set<number>>(new Set());
	let confirmDelete: number | null = $state(null);
	let expandedId: number | null = $state(null);
	let entityTags = $state<Record<number, Tag[]>>({});
	let sourceSearch = $state('');
	let addingToTrackId: number | null = $state(null);
	let editingNoteId: number | null = $state(null);
	let noteText = $state('');
	let addingGoalToTrackId: number | null = $state(null);
	let newGoalText = $state('');

	let filteredSources = $derived(
		sourceSearch.length >= 1
			? $sources.filter(s => s.title.toLowerCase().includes(sourceSearch.toLowerCase()))
			: []
	);

	async function handleDelete(id: number) {
		await deleteLearningTrack(id);
		await Promise.all([loadLearningTracks(), loadTags()]);
		confirmDelete = null;
	}

	async function toggleActive(id: number, isActive: boolean) {
		if (isActive) { await deactivateLearningTrack(id); } else { await activateLearningTrack(id); }
		await loadLearningTracks();
	}

	async function toggleExpand(id: number) {
		if (expandedId === id) { expandedId = null; addingToTrackId = null; return; }
		expandedId = id;
		addingToTrackId = null;
		if (!entityTags[id]) {
			entityTags[id] = await getEntityTags('learning_track', id);
		}
	}

	async function handleAttach(trackId: number, tag: Tag) {
		await attachTag(tag.id, 'learning_track', trackId);
		entityTags[trackId] = await getEntityTags('learning_track', trackId);
	}

	async function handleDetach(trackId: number, tag: Tag) {
		await detachTag(tag.id, 'learning_track', trackId);
		entityTags[trackId] = await getEntityTags('learning_track', trackId);
	}

	async function handleAddSource(trackId: number, sourceId: number) {
		const track = $learningTracks.find(lt => lt.id === trackId);
		const position = track ? track.items.length : 0;
		await addItem(trackId, { source_id: sourceId, position });
		sourceSearch = '';
		addingToTrackId = null;
		await loadLearningTracks();
	}

	async function cycleStatus(item: LearningTrackItem) {
		const idx = STATUS_CYCLE.indexOf(item.status);
		const next = STATUS_CYCLE[(idx + 1) % STATUS_CYCLE.length];
		await updateItem(item.id, { status: next });
		await loadLearningTracks();
	}

	async function handleRemoveItem(itemId: number) {
		await removeItem(itemId);
		await loadLearningTracks();
	}

	async function moveItemUp(trackId: number, item: LearningTrackItem) {
		const track = $learningTracks.find(lt => lt.id === trackId);
		if (!track) return;
		const sorted = [...track.items].sort((a, b) => a.position - b.position);
		const idx = sorted.findIndex(i => i.id === item.id);
		if (idx <= 0) return;
		await updateItem(sorted[idx].id, { position: sorted[idx - 1].position });
		await updateItem(sorted[idx - 1].id, { position: item.position });
		await loadLearningTracks();
	}

	async function moveItemDown(trackId: number, item: LearningTrackItem) {
		const track = $learningTracks.find(lt => lt.id === trackId);
		if (!track) return;
		const sorted = [...track.items].sort((a, b) => a.position - b.position);
		const idx = sorted.findIndex(i => i.id === item.id);
		if (idx >= sorted.length - 1) return;
		await updateItem(sorted[idx].id, { position: sorted[idx + 1].position });
		await updateItem(sorted[idx + 1].id, { position: item.position });
		await loadLearningTracks();
	}

	async function saveNote(itemId: number) {
		await updateItem(itemId, { notes: noteText || undefined });
		editingNoteId = null;
		noteText = '';
		await loadLearningTracks();
	}

	function getSourceTitle(sourceId: number): string {
		const source = $sources.find(s => s.id === sourceId);
		return source ? source.title : `Source #${sourceId}`;
	}

	async function handleAddGoal(trackId: number) {
		if (!newGoalText.trim()) return;
		await addGoal(trackId, newGoalText.trim());
		newGoalText = '';
		addingGoalToTrackId = null;
		await loadLearningTracks();
	}

	async function handleToggleGoal(goalId: number) {
		await toggleGoal(goalId);
		await loadLearningTracks();
	}

	async function handleRemoveGoal(goalId: number) {
		await removeGoal(goalId);
		await loadLearningTracks();
	}

	async function loadAllTags() {
		const entries = await Promise.all(
			$learningTracks.map(async (track) => [track.id, await getEntityTags('learning_track', track.id)] as const)
		);
		const updated: Record<number, Tag[]> = {};
		for (const [id, tags] of entries) updated[id] = tags;
		entityTags = updated;
	}

	$effect(() => {
		if ($learningTracks) loadAllTags();
	});
</script>

<PanelContainer title="Learning Tracks" panelId="learningtrack" color="#7b6b8d" onAdd={() => (showForm = !showForm)}>
	{#if showForm}
		<div class="inline-form">
			<LearningTrackForm onDone={() => (showForm = false)} />
		</div>
	{/if}

	{#each filteredTracks as track (track.id)}
		{#if editingIds.has(track.id)}
			<div class="inline-form">
				<LearningTrackForm editData={track} onDone={() => { editingIds.delete(track.id); editingIds = new Set(editingIds); }} />
			</div>
		{:else}
			<div class="item" use:selectable={{ entityType: 'learning_track', entityId: track.id }} ondblclick={() => selectEntity('learning_track', track.id, track.title)} role="button" tabindex="-1">
				<div class="item-header">
					<button class="item-title" ondblclick={() => { editingIds.add(track.id); editingIds = new Set(editingIds); }}>{track.title}</button>
					<span class="item-count">{track.items.length} items</span>
					<button class="btn-expand" onclick={() => toggleExpand(track.id)}>
						{expandedId === track.id ? 'Collapse' : 'Expand'}
					</button>
					<button class="btn-active" class:active={track.is_active} onclick={() => toggleActive(track.id, track.is_active)}>
						{track.is_active ? 'Active' : 'Inactive'}
					</button>
					<button class="btn-delete" onclick={() => (confirmDelete = track.id)}>Delete</button>
				</div>
				{#if entityTags[track.id]?.length}
					<div class="tag-badges">
						{#each entityTags[track.id] as tag (tag.id)}
							<TagBadge {tag} />
						{/each}
					</div>
				{/if}
				{#if track.description}
					<p class="item-desc">{track.description}</p>
				{/if}

				{#if expandedId === track.id}
					<div class="expanded-section">
						<!-- Goals section -->
						<div class="goals-section">
							<div class="section-header">
								<span class="section-title">Goals</span>
								<span class="goal-progress">
									{(track.goals ?? []).filter(g => g.is_completed).length}/{(track.goals ?? []).length}
								</span>
							</div>
							<div class="goals-list">
								{#each track.goals ?? [] as goal (goal.id)}
									<div class="goal-item" class:completed={goal.is_completed}>
										<button class="goal-checkbox" onclick={() => handleToggleGoal(goal.id)}>
											{goal.is_completed ? '☑' : '☐'}
										</button>
										<span class="goal-text">{goal.description}</span>
										<button class="btn-remove-goal" onclick={() => handleRemoveGoal(goal.id)}>×</button>
									</div>
								{/each}
							</div>
							{#if addingGoalToTrackId === track.id}
								<div class="add-goal-form">
									<input
										type="text"
										placeholder="Describe the goal..."
										bind:value={newGoalText}
										class="goal-input"
										onkeydown={(e) => e.key === 'Enter' && handleAddGoal(track.id)}
									/>
									<button class="btn-save-goal" onclick={() => handleAddGoal(track.id)}>Add</button>
									<button class="btn-cancel-goal" onclick={() => { addingGoalToTrackId = null; newGoalText = ''; }}>Cancel</button>
								</div>
							{:else}
								<button class="btn-add-goal" onclick={() => (addingGoalToTrackId = track.id)}>+ Add Goal</button>
							{/if}
						</div>

						<div class="items-list">
							{#each [...track.items].sort((a, b) => a.position - b.position) as item (item.id)}
								<div class="list-item">
									<div class="list-item-header">
										<div class="reorder-btns">
											<button class="btn-move" onclick={() => moveItemUp(track.id, item)}>&#9650;</button>
											<button class="btn-move" onclick={() => moveItemDown(track.id, item)}>&#9660;</button>
										</div>
										<span class="source-title">{getSourceTitle(item.source_id)}</span>
										<button
											class="status-badge"
											style:background={STATUS_COLORS[item.status] || '#9ca3af'}
											onclick={() => cycleStatus(item)}
										>
											{STATUS_LABELS[item.status] || item.status}
										</button>
										<button class="btn-note" onclick={() => { editingNoteId = editingNoteId === item.id ? null : item.id; noteText = item.notes ?? ''; }}>
											Notes
										</button>
										<button class="btn-remove" onclick={() => handleRemoveItem(item.id)}>x</button>
									</div>
									{#if item.notes && editingNoteId !== item.id}
										<p class="item-note">{item.notes}</p>
									{/if}
									{#if editingNoteId === item.id}
										<div class="note-edit">
											<textarea bind:value={noteText} rows="2" placeholder="Add notes..."></textarea>
											<div class="note-actions">
												<button class="btn-save-note" onclick={() => saveNote(item.id)}>Save</button>
												<button class="btn-cancel-note" onclick={() => { editingNoteId = null; }}>Cancel</button>
											</div>
										</div>
									{/if}
								</div>
							{/each}
						</div>

						<div class="add-source">
							{#if addingToTrackId === track.id}
								<div class="source-search">
									<input
										type="text"
										placeholder="Search sources by title..."
										bind:value={sourceSearch}
										class="source-search-input"
									/>
									{#if filteredSources.length > 0}
										<div class="source-dropdown">
											{#each filteredSources.slice(0, 10) as source (source.id)}
												<button class="source-option" onclick={() => handleAddSource(track.id, source.id)}>
													{source.title}
												</button>
											{/each}
										</div>
									{/if}
									<button class="btn-cancel-add" onclick={() => { addingToTrackId = null; sourceSearch = ''; }}>Cancel</button>
								</div>
							{:else}
								<button class="btn-add-source" onclick={() => (addingToTrackId = track.id)}>+ Add Source</button>
							{/if}
						</div>

						<div class="tag-section">
							<TagInput
								attachedTags={entityTags[track.id] || []}
								targetType="learning_track"
								targetId={track.id}
								onAttach={(tag) => handleAttach(track.id, tag)}
								onDetach={(tag) => handleDetach(track.id, tag)}
							/>
						</div>
					</div>
				{/if}
			</div>
		{/if}
	{/each}

	{#if $learningTracks.length === 0}
		<p class="empty">No learning tracks yet.</p>
	{:else if filteredTracks.length === 0}
		<p class="empty">No learning tracks for this date.</p>
	{/if}
</PanelContainer>

<ConfirmDialog
	open={confirmDelete !== null}
	message="Delete this learning track? All items will be removed."
	onConfirm={() => confirmDelete && handleDelete(confirmDelete)}
	onCancel={() => (confirmDelete = null)}
/>

<style>
	.inline-form { padding: 10px; background: #f0fdfa; border: 1px solid #99f6e4; border-radius: 8px; margin-bottom: 12px; }
	.item { padding: 10px 0; border-bottom: 1px solid #f3f4f6; }
	.item-header { display: flex; align-items: center; gap: 8px; }
	.item-title { flex: 1; background: none; border: none; cursor: pointer; font-weight: 500; font-size: 0.9rem; text-align: left; padding: 0; color: #111827; }
	.item-desc { font-size: 0.8rem; color: #6b7280; margin: 4px 0 0; }
	.item-count { font-size: 0.7rem; padding: 2px 6px; background: #f0fdfa; border-radius: 4px; color: #0d9488; }
	.btn-expand { font-size: 0.7rem; padding: 2px 8px; border-radius: 4px; border: 1px solid #d1d5db; cursor: pointer; background: #f9fafb; color: #6b7280; }
	.btn-active { font-size: 0.7rem; padding: 2px 8px; border-radius: 4px; border: 1px solid #d1d5db; cursor: pointer; background: #f3f4f6; color: #6b7280; }
	.btn-active.active { background: #dcfce7; color: #16a34a; border-color: #bbf7d0; }
	.tag-badges { display: flex; flex-wrap: wrap; gap: 4px; margin-top: 4px; }
	.btn-delete { font-size: 0.75rem; padding: 2px 8px; background: #fee2e2; color: #ef4444; border: 1px solid #fecaca; border-radius: 4px; cursor: pointer; }
	.tag-section { margin-top: 8px; padding: 8px; background: #f9fafb; border-radius: 6px; }
	.empty { text-align: center; color: #9ca3af; font-size: 0.875rem; }

	.expanded-section { margin-top: 8px; padding: 8px; background: #f9fafb; border-radius: 6px; }
	.items-list { display: flex; flex-direction: column; gap: 4px; }
	.list-item { background: white; border: 1px solid #e5e7eb; border-radius: 6px; padding: 6px 8px; }
	.list-item-header { display: flex; align-items: center; gap: 6px; }
	.reorder-btns { display: flex; flex-direction: column; gap: 0; }
	.btn-move { background: none; border: none; cursor: pointer; font-size: 0.6rem; padding: 0 2px; color: #9ca3af; line-height: 1; }
	.btn-move:hover { color: #374151; }
	.source-title { flex: 1; font-size: 0.8rem; font-weight: 500; color: #374151; }
	.status-badge { font-size: 0.65rem; padding: 2px 8px; border-radius: 10px; color: white; border: none; cursor: pointer; font-weight: 500; }
	.btn-note { font-size: 0.65rem; padding: 2px 6px; border-radius: 4px; border: 1px solid #d1d5db; cursor: pointer; background: #f9fafb; color: #6b7280; }
	.btn-remove { font-size: 0.7rem; background: none; border: none; cursor: pointer; color: #ef4444; padding: 0 4px; }
	.item-note { font-size: 0.75rem; color: #6b7280; margin: 4px 0 0 24px; font-style: italic; }
	.note-edit { margin-top: 4px; margin-left: 24px; }
	.note-edit textarea { width: 100%; padding: 4px 6px; border: 1px solid #d1d5db; border-radius: 4px; font-size: 0.8rem; resize: vertical; }
	.note-actions { display: flex; gap: 4px; margin-top: 4px; }
	.btn-save-note { font-size: 0.7rem; padding: 2px 8px; background: #0d9488; color: white; border: none; border-radius: 4px; cursor: pointer; }
	.btn-cancel-note { font-size: 0.7rem; padding: 2px 8px; background: white; border: 1px solid #d1d5db; border-radius: 4px; cursor: pointer; }

	.add-source { margin-top: 8px; }
	.btn-add-source { font-size: 0.8rem; padding: 4px 12px; background: #f0fdfa; color: #0d9488; border: 1px dashed #99f6e4; border-radius: 6px; cursor: pointer; width: 100%; }
	.source-search { display: flex; flex-direction: column; gap: 4px; position: relative; }
	.source-search-input { padding: 6px 8px; border: 1px solid #d1d5db; border-radius: 4px; font-size: 0.8rem; }
	.source-dropdown { background: white; border: 1px solid #e5e7eb; border-radius: 6px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); max-height: 150px; overflow-y: auto; }
	.source-option { display: block; width: 100%; text-align: left; padding: 6px 10px; border: none; background: none; cursor: pointer; font-size: 0.8rem; color: #374151; }
	.source-option:hover { background: #f3f4f6; }
	.btn-cancel-add { font-size: 0.75rem; padding: 4px 8px; background: white; border: 1px solid #d1d5db; border-radius: 4px; cursor: pointer; align-self: flex-start; }

	/* Goals styles */
	.goals-section { margin-bottom: 12px; padding: 8px; background: #faf5ff; border: 1px solid #e9d5ff; border-radius: 6px; }
	.section-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 6px; }
	.section-title { font-size: 0.75rem; font-weight: 600; color: #7c3aed; text-transform: uppercase; letter-spacing: 0.5px; }
	.goal-progress { font-size: 0.7rem; padding: 2px 6px; background: #ede9fe; border-radius: 4px; color: #7c3aed; font-weight: 500; }
	.goals-list { display: flex; flex-direction: column; gap: 4px; }
	.goal-item { display: flex; align-items: center; gap: 6px; padding: 4px 6px; background: white; border: 1px solid #e5e7eb; border-radius: 4px; }
	.goal-item.completed { background: #f0fdf4; border-color: #bbf7d0; }
	.goal-item.completed .goal-text { text-decoration: line-through; color: #9ca3af; }
	.goal-checkbox { background: none; border: none; cursor: pointer; font-size: 1rem; padding: 0; color: #7c3aed; }
	.goal-text { flex: 1; font-size: 0.8rem; color: #374151; }
	.btn-remove-goal { background: none; border: none; cursor: pointer; font-size: 0.9rem; color: #d1d5db; padding: 0 2px; }
	.btn-remove-goal:hover { color: #ef4444; }
	.btn-add-goal { font-size: 0.75rem; padding: 4px 10px; background: white; color: #7c3aed; border: 1px dashed #c4b5fd; border-radius: 4px; cursor: pointer; margin-top: 6px; }
	.btn-add-goal:hover { background: #faf5ff; }
	.add-goal-form { display: flex; gap: 4px; margin-top: 6px; }
	.goal-input { flex: 1; padding: 4px 8px; border: 1px solid #d1d5db; border-radius: 4px; font-size: 0.8rem; }
	.btn-save-goal { font-size: 0.75rem; padding: 4px 8px; background: #7c3aed; color: white; border: none; border-radius: 4px; cursor: pointer; }
	.btn-cancel-goal { font-size: 0.75rem; padding: 4px 8px; background: white; border: 1px solid #d1d5db; border-radius: 4px; cursor: pointer; }
</style>
