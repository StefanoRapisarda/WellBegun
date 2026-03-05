<script lang="ts">
	import type { Log } from '$lib/types';
	import { createLog, updateLog } from '$lib/api/logs';
	import { loadLogs } from '$lib/stores/logs';
	import { loadTags } from '$lib/stores/tags';
	import { syncHashtags, attachTag } from '$lib/api/tags';
	import { getDraft, setDraft, clearDraft } from '$lib/stores/formDrafts';
	import HashtagTextarea from '../shared/HashtagTextarea.svelte';
	import DefaultTagSuggestions from '../shared/DefaultTagSuggestions.svelte';
	import { onMount } from 'svelte';

	let { editData = undefined, onDone = undefined, onCreate = undefined }: { editData?: Log; onDone?: () => void; onCreate?: (id: number) => void } =
		$props();

	let title = $state('');
	let content = $state('');
	let location = $state('');
	let mood = $state('');
	let weather = $state('');
	let dayTheme = $state('');
	let selectedTagIds = $state<number[]>([]);

	const MOODS = ['😊', '😃', '😌', '😐', '😔', '😢', '😤', '😴', '🤔', '😎'];
	const WEATHERS = ['☀️', '🌤️', '⛅', '☁️', '🌧️', '⛈️', '🌨️', '🌬️', '🌫️', '🌈'];
	const THEMES = ['💼', '📚', '🏃', '🎨', '🧘', '🎉', '❤️', '🌱', '🍳', '✈️'];

	function toggleEmoji(current: string, emoji: string): string {
		return current === emoji ? '' : emoji;
	}

	// Load draft on mount (only for new entries, not editing)
	onMount(() => {
		if (!editData) {
			const draft = getDraft('log');
			title = draft.title || '';
			content = draft.content || '';
		}
	});

	// Save draft as user types (only for new entries)
	$effect(() => {
		if (!editData) {
			setDraft('log', 'title', title);
			setDraft('log', 'content', content);
		}
	});

	$effect(() => {
		if (editData) {
			title = editData.title;
			content = editData.content ?? '';
			location = editData.location ?? '';
			mood = editData.mood ?? '';
			weather = editData.weather ?? '';
			dayTheme = editData.day_theme ?? '';
		}
	});

	async function handleSubmit(e: SubmitEvent) {
		e.preventDefault();
		if (!title.trim()) return;
		let logId: number;
		if (editData) {
			await updateLog(editData.id, {
				title: title.trim(),
				content: content.trim() || undefined,
				location: location.trim() || undefined,
				mood: mood || undefined,
				weather: weather || undefined,
				day_theme: dayTheme || undefined
			});
			logId = editData.id;
		} else {
			const created = await createLog({
				title: title.trim(),
				content: content.trim() || undefined,
				location: location.trim() || undefined,
				mood: mood || undefined,
				weather: weather || undefined,
				day_theme: dayTheme || undefined
			});
			logId = created.id;
			for (const tagId of selectedTagIds) {
				await attachTag(tagId, 'log', logId);
			}
		}
		if (content.includes('#')) {
			await syncHashtags(content, 'log', logId);
		}
		await Promise.all([loadLogs(), loadTags()]);
		if (!editData) {
			onCreate?.(logId);
			clearDraft('log');
		}
		title = '';
		content = '';
		location = '';
		mood = '';
		weather = '';
		dayTheme = '';
		selectedTagIds = [];
		onDone?.();
	}

	function handleCancel() {
		title = '';
		content = '';
		location = '';
		mood = '';
		weather = '';
		dayTheme = '';
		onDone?.();
	}
</script>

<form onsubmit={handleSubmit} class="widget" class:editing={!!editData}>
	<input type="text" bind:value={title} placeholder="Log title..." class="title-input" required />
	<input type="text" bind:value={location} placeholder="Location" class="field-input" />
	<HashtagTextarea bind:value={content} rows={editData ? 4 : 2} autoSize={!!editData} placeholder="Content (optional) — type # to insert tags" />
	{#if !editData}
		<DefaultTagSuggestions category="log" bind:selectedTagIds {title} />
	{/if}
	<div class="emoji-row">
		<span class="emoji-label">Mood</span>
		{#each MOODS as e}
			<button type="button" class="emoji-chip" class:selected={mood === e} onclick={() => mood = toggleEmoji(mood, e)}>{e}</button>
		{/each}
	</div>
	<div class="emoji-row">
		<span class="emoji-label">Weather</span>
		{#each WEATHERS as e}
			<button type="button" class="emoji-chip" class:selected={weather === e} onclick={() => weather = toggleEmoji(weather, e)}>{e}</button>
		{/each}
	</div>
	<div class="emoji-row">
		<span class="emoji-label">Theme</span>
		{#each THEMES as e}
			<button type="button" class="emoji-chip" class:selected={dayTheme === e} onclick={() => dayTheme = toggleEmoji(dayTheme, e)}>{e}</button>
		{/each}
	</div>
	<div class="button-row">
		<button type="button" class="btn-cancel" onclick={handleCancel}>Cancel</button>
		<button type="submit" class="btn-save">{editData ? 'Save' : 'Create'}</button>
	</div>
</form>

<style>
	.widget { display: flex; flex-direction: column; gap: 6px; padding: 10px; background: #faf8f5; border: 1px solid #e8e0d4; border-radius: 8px; margin-bottom: 12px; }
	.widget.editing { background: #fefce8; border-color: #fde68a; }
	.title-input { padding: 6px 8px; border: 1px solid #d1d5db; border-radius: 6px; font-size: 0.85rem; }
	.button-row { display: flex; justify-content: flex-end; gap: 6px; padding-top: 4px; }
	.field-input { padding: 6px 8px; border: 1px solid #d1d5db; border-radius: 6px; font-size: 0.85rem; }
	.emoji-row { display: flex; align-items: center; gap: 4px; flex-wrap: wrap; }
	.emoji-label { font-size: 0.7rem; color: #6b7280; font-weight: 500; min-width: 50px; }
	.emoji-chip { font-size: 1rem; padding: 2px 4px; border: 1px solid transparent; border-radius: 6px; background: none; cursor: pointer; line-height: 1; transition: all 0.1s; }
	.emoji-chip:hover { background: #f3f4f6; }
	.emoji-chip.selected { border-color: #3b82f6; background: #eff6ff; }
	.btn-save { padding: 6px 14px; background: #8b7355; color: white; border: none; border-radius: 6px; cursor: pointer; font-size: 0.8rem; font-weight: 500; }
	.btn-save:hover { background: #74603f; }
	.btn-cancel { padding: 6px 14px; background: white; color: #6b7280; border: 1px solid #d1d5db; border-radius: 6px; cursor: pointer; font-size: 0.8rem; font-weight: 500; }
	.btn-cancel:hover { background: #f3f4f6; }
</style>
