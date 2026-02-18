<script lang="ts">
	import type { Log } from '$lib/types';
	import { updateLog } from '$lib/api/logs';
	import { loadLogs } from '$lib/stores/logs';
	import { loadTags } from '$lib/stores/tags';
	import { onMount } from 'svelte';

	let { onDone, editData }: { onDone: () => void; editData: Log } = $props();

	let title = $state(editData.title);
	let content = $state(editData.content ?? '');
	let location = $state(editData.location ?? '');
	let mood = $state(editData.mood ?? '');
	let weather = $state(editData.weather ?? '');
	let dayTheme = $state(editData.day_theme ?? '');

	const MOODS = ['😊', '😃', '😌', '😐', '😔', '😢', '😤', '😴', '🤔', '😎'];
	const WEATHERS = ['☀️', '🌤️', '⛅', '☁️', '🌧️', '⛈️', '🌨️', '🌬️', '🌫️', '🌈'];
	const THEMES = ['💼', '📚', '🏃', '🎨', '🧘', '🎉', '❤️', '🌱', '🍳', '✈️'];

	let contentEl: HTMLTextAreaElement | undefined = $state();

	onMount(() => {
		if (contentEl) {
			const maxH = window.innerHeight * 0.45;
			contentEl.style.height = 'auto';
			contentEl.style.height = Math.min(contentEl.scrollHeight, maxH) + 'px';
		}
	});

	function toggleEmoji(current: string, emoji: string): string {
		return current === emoji ? '' : emoji;
	}

	async function handleSubmit(e: SubmitEvent) {
		e.preventDefault();
		if (!title.trim()) return;
		await updateLog(editData.id, {
			title: title.trim(),
			content: content.trim() || undefined,
			location: location.trim() || undefined,
			mood: mood || undefined,
			weather: weather || undefined,
			day_theme: dayTheme || undefined
		});
		await Promise.all([loadLogs(), loadTags()]);
		onDone();
	}
</script>

<form onsubmit={handleSubmit} class="widget editing">
	<div class="title-row">
		<input type="text" bind:value={title} required placeholder="Log title..." class="title-input" />
		<button type="submit" class="btn-save">Save</button>
		<button type="button" class="btn-cancel" onclick={onDone}>Cancel</button>
	</div>
	<input type="text" bind:value={location} placeholder="Location" class="field-input" />
	<textarea bind:this={contentEl} bind:value={content} rows="3" placeholder="Content (optional)" class="field-textarea"></textarea>
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
</form>

<style>
	.widget { display: flex; flex-direction: column; gap: 6px; padding: 10px; background: #faf8f5; border: 1px solid #e8e0d4; border-radius: 8px; margin-bottom: 12px; }
	.widget.editing { background: #fefce8; border-color: #fde68a; }
	.title-row { display: flex; gap: 6px; align-items: center; }
	.title-input { flex: 1; padding: 6px 8px; border: 1px solid #d1d5db; border-radius: 6px; font-size: 0.85rem; }
	.field-input { padding: 6px 8px; border: 1px solid #d1d5db; border-radius: 6px; font-size: 0.85rem; }
	.field-textarea { padding: 6px 8px; border: 1px solid #d1d5db; border-radius: 6px; font-size: 0.85rem; resize: vertical; font-family: inherit; }
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
