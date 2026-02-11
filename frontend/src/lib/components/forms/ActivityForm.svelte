<script lang="ts">
	import type { Activity } from '$lib/types';
	import { createActivity, updateActivity } from '$lib/api/activities';
	import { loadActivities } from '$lib/stores/activities';
	import { loadTags } from '$lib/stores/tags';
	import { syncHashtags, attachTag } from '$lib/api/tags';
	import HashtagTextarea from '../shared/HashtagTextarea.svelte';
	import DefaultTagSuggestions from '../shared/DefaultTagSuggestions.svelte';

	let { onDone, editData, onCreate }: { onDone: () => void; editData?: Activity; onCreate?: (id: number) => void } = $props();

	let title = $state(editData?.title ?? '');
	let description = $state(editData?.description ?? '');
	let duration = $state(editData?.duration?.toString() ?? '');
	let selectedTagIds = $state<number[]>([]);

	// Keyword patterns for auto-matching tags
	const KEYWORD_PATTERNS: Record<string, string[]> = {
		'Meeting': ['meeting', 'meet', 'sync', 'standup', 'stand-up', '1:1', 'one-on-one', 'call', 'huddle'],
		'ToDo': ['todo', 'to-do', 'to do'],
		'InProgress': ['wip', 'working on', 'in progress'],
		'Done': ['done', 'completed', 'finished'],
		'Blocked': ['blocked', 'stuck', 'waiting'],
		'Coding': ['coding', 'code', 'develop', 'programming', 'implement', 'debug', 'fix bug'],
		'Reading': ['reading', 'read', 'study', 'studying'],
		'Writing': ['writing', 'write', 'document', 'documentation', 'draft'],
		'Review': ['review', 'feedback', 'pr review', 'code review'],
		'Research': ['research', 'investigate', 'explore', 'analysis', 'analyze'],
	};

	// Derive matched keywords from title
	let keywordMatches = $derived.by(() => {
		const lowerTitle = title.toLowerCase();
		const matches: string[] = [];
		for (const [tagName, keywords] of Object.entries(KEYWORD_PATTERNS)) {
			if (keywords.some(kw => lowerTitle.includes(kw))) {
				matches.push(tagName);
			}
		}
		return matches;
	});

	async function handleSubmit(e: SubmitEvent) {
		e.preventDefault();
		if (!title.trim()) return;
		const data = {
			title: title.trim(),
			description: description.trim() || undefined,
			duration: duration ? parseInt(duration, 10) : undefined
		};
		let activityId: number;
		if (editData) {
			await updateActivity(editData.id, data);
			activityId = editData.id;
		} else {
			const created = await createActivity(data);
			activityId = created.id;
			// Attach selected default tags to new activity
			for (const tagId of selectedTagIds) {
				await attachTag(tagId, 'activity', activityId);
			}
		}
		if (description.includes('#')) {
			await syncHashtags(description, 'activity', activityId);
		}
		await Promise.all([loadActivities(), loadTags()]);
		if (!editData) {
			onCreate?.(activityId);
		}
		onDone();
	}
</script>

<form onsubmit={handleSubmit} class="form">
	<label>
		Title *
		<input type="text" bind:value={title} required placeholder="e.g. coding, reading" />
	</label>
	<label>
		Description
		<HashtagTextarea bind:value={description} rows={3} placeholder="What are you working on? Type # to insert tags..." />
	</label>
	<label>
		Duration (minutes)
		<input type="number" bind:value={duration} min="0" placeholder="e.g. 60" />
	</label>
	{#if !editData}
		<DefaultTagSuggestions category="activity" bind:selectedTagIds {keywordMatches} />
	{/if}
	<div class="form-actions">
		<button type="button" class="btn btn-cancel" onclick={onDone}>Cancel</button>
		<button type="submit" class="btn btn-primary">{editData ? 'Save' : 'Create Activity'}</button>
	</div>
</form>

<style>
	.form { display: flex; flex-direction: column; gap: 12px; }
	label { display: flex; flex-direction: column; gap: 4px; font-size: 0.875rem; font-weight: 500; color: #374151; }
	input { padding: 8px; border: 1px solid #d1d5db; border-radius: 6px; font-size: 0.875rem; }
	.form-actions { display: flex; gap: 8px; justify-content: flex-end; margin-top: 8px; }
	.btn { padding: 8px 16px; border-radius: 6px; border: 1px solid #d1d5db; cursor: pointer; font-size: 0.875rem; }
	.btn-cancel { background: white; }
	.btn-primary { background: #8b5cf6; color: white; border-color: #8b5cf6; }
</style>
