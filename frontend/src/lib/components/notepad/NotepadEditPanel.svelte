<script lang="ts">
	import { ENTITY_CONFIG, type ParsedEntity, type NotepadEntityType } from '$lib/notepad/types';
	import { get } from 'svelte/store';
	import { tags as tagsStore } from '$lib/stores/tags';
	import { onMount } from 'svelte';
	import HashtagTextarea from '../shared/HashtagTextarea.svelte';
	import DefaultTagSuggestions from '../shared/DefaultTagSuggestions.svelte';

	let {
		entity,
		onSave,
		onClose
	}: {
		entity: ParsedEntity;
		onSave: (updated: Record<string, string>, items?: Array<{ title: string; is_done: boolean }>) => void;
		onClose: () => void;
	} = $props();

	let config = $derived(ENTITY_CONFIG[entity.type]);

	// Editable field state — initialized from entity props
	// Component is recreated via {#key} in NotepadTab when entity changes
	const f = entity.fields;
	let title = $state(f.title ?? '');
	let content = $state(f.content ?? '');
	let description = $state(f.description ?? '');
	let status = $state(f.status ?? 'in_progress');
	let startDate = $state(f.start_date ?? '');
	let location = $state(f.location ?? '');
	let mood = $state(f.mood ?? '');
	let weather = $state(f.weather ?? '');
	let dayTheme = $state(f.day_theme ?? '');
	let logType = $state(f.log_type ?? '');
	let duration = $state(f.duration ?? '');
	let author = $state(f.author ?? '');
	let contentUrl = $state(f.content_url ?? '');
	let sourceType = $state(f.source_type ?? '');
	let fullName = $state(f.full_name ?? '');
	let role = $state(f.role ?? '');
	let affiliation = $state(f.affiliation ?? '');
	let expertise = $state(f.expertise ?? '');
	let notes = $state(f.notes ?? '');
	let email = $state(f.email ?? '');
	let url = $state(f.url ?? '');
	let motivation = $state(f.motivation ?? '');
	let outcome = $state(f.outcome ?? '');
	let endDate = $state(f.end_date ?? '');

	// Plan items state
	let plannedItems = $state<string[]>(entity.items?.map(i => i.title) ?? []);
	let newItemText = $state('');

	function addPlanItem() {
		if (!newItemText.trim()) return;
		plannedItems = [...plannedItems, newItemText.trim()];
		newItemText = '';
	}

	function removePlanItem(index: number) {
		plannedItems = plannedItems.filter((_, i) => i !== index);
	}

	function updatePlanItemText(index: number, text: string) {
		plannedItems[index] = text;
	}

	// ── Tag handling via DefaultTagSuggestions ──
	let selectedTagIds = $state<number[]>([]);

	function getTagCategory(type: NotepadEntityType): string {
		switch (type) {
			case 'reading_list': return 'readinglist';
			default: return type;
		}
	}

	let tagCategory = $derived(getTagCategory(entity.type));

	// ── Emoji pickers (for log) ──
	const MOODS = ['😊', '😃', '😌', '😐', '😔', '😢', '😤', '😴', '🤔', '😎'];
	const WEATHERS = ['☀️', '🌤️', '⛅', '☁️', '🌧️', '⛈️', '🌨️', '🌬️', '🌫️', '🌈'];
	const THEMES = ['💼', '📚', '🏃', '🎨', '🧘', '🎉', '❤️', '🌱', '🍳', '✈️'];

	function toggleEmoji(current: string, emoji: string): string {
		return current === emoji ? '' : emoji;
	}

	// ── Activity keyword matching (matches ActivityForm exactly) ──
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

	let keywordMatches = $derived.by(() => {
		if (entity.type !== 'activity') return [];
		const lowerTitle = title.toLowerCase();
		const matches: string[] = [];
		for (const [tagName, keywords] of Object.entries(KEYWORD_PATTERNS)) {
			if (keywords.some(kw => lowerTitle.includes(kw))) {
				matches.push(tagName);
			}
		}
		return matches;
	});

	// ── Auto-resize for plain textareas ──
	let descEl: HTMLTextAreaElement | undefined = $state();
	let notesEl: HTMLTextAreaElement | undefined = $state();

	onMount(() => {
		// Pre-select tags from entity's comma-separated tag names
		if (f.tags?.trim()) {
			const names = f.tags.split(',').map(t => t.trim().toLowerCase()).filter(Boolean);
			const allTags = get(tagsStore);
			const matched = allTags.filter(t => names.includes(t.name.toLowerCase()));
			selectedTagIds = matched.map(t => t.id);
		}
		// Auto-resize textareas that have content
		for (const el of [descEl, notesEl]) {
			if (el && el.value) {
				const maxH = window.innerHeight * 0.45;
				el.style.height = 'auto';
				el.style.height = Math.min(el.scrollHeight, maxH) + 'px';
			}
		}
	});

	function handleSubmit(e: SubmitEvent) {
		e.preventDefault();
		const updated: Record<string, string> = {};

		switch (entity.type) {
			case 'note':
				if (title.trim()) updated.title = title.trim();
				if (content.trim()) updated.content = content.trim();
				break;
			case 'project':
				if (title.trim()) updated.title = title.trim();
				if (description.trim()) updated.description = description.trim();
				if (status) updated.status = status;
				if (startDate) updated.start_date = startDate;
				break;
			case 'log':
				if (title.trim()) updated.title = title.trim();
				if (content.trim()) updated.content = content.trim();
				if (location.trim()) updated.location = location.trim();
				if (mood) updated.mood = mood;
				if (weather) updated.weather = weather;
				if (dayTheme) updated.day_theme = dayTheme;
				if (logType.trim()) updated.log_type = logType.trim();
				break;
			case 'activity':
				if (title.trim()) updated.title = title.trim();
				if (description.trim()) updated.description = description.trim();
				if (duration) updated.duration = duration;
				break;
			case 'source':
				if (title.trim()) updated.title = title.trim();
				if (description.trim()) updated.description = description.trim();
				if (author.trim()) updated.author = author.trim();
				if (contentUrl.trim()) updated.content_url = contentUrl.trim();
				if (sourceType.trim()) updated.source_type = sourceType.trim();
				break;
			case 'actor':
				if (fullName.trim()) updated.full_name = fullName.trim();
				if (role.trim()) updated.role = role.trim();
				if (affiliation.trim()) updated.affiliation = affiliation.trim();
				if (expertise.trim()) updated.expertise = expertise.trim();
				if (notes.trim()) updated.notes = notes.trim();
				if (email.trim()) updated.email = email.trim();
				if (url.trim()) updated.url = url.trim();
				break;
			case 'reading_list':
				if (title.trim()) updated.title = title.trim();
				if (description.trim()) updated.description = description.trim();
				break;
			case 'plan':
				if (title.trim()) updated.title = title.trim();
				if (description.trim()) updated.description = description.trim();
				if (motivation.trim()) updated.motivation = motivation.trim();
				if (outcome.trim()) updated.outcome = outcome.trim();
				if (startDate) updated.start_date = startDate;
				if (endDate) updated.end_date = endDate;
				break;
		}

		// Convert selectedTagIds to comma-separated tag names
		if (selectedTagIds.length > 0) {
			const allTags = get(tagsStore);
			const tagNames = selectedTagIds
				.map(id => allTags.find(t => t.id === id)?.name)
				.filter((n): n is string => !!n);
			if (tagNames.length > 0) {
				updated.tags = tagNames.join(', ');
			}
		}

		if (entity.type === 'plan' && plannedItems.length > 0) {
			const items = plannedItems.filter(t => t.trim()).map(t => ({ title: t.trim(), is_done: false }));
			onSave(updated, items);
		} else {
			onSave(updated);
		}
	}
</script>

{#snippet actionButtons(saveClass: string)}
	<div class="button-row">
		<button type="button" class="btn-cancel" onclick={onClose}>Cancel</button>
		<button type="submit" class="btn-save {saveClass}">Save</button>
	</div>
{/snippet}

<!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
<div class="overlay" onclick={onClose} onkeydown={(e) => e.key === 'Escape' && onClose()} role="dialog" tabindex="-1">
	<!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
	<!-- svelte-ignore a11y_click_events_have_key_events -->
	<div class="edit-panel" onclick={(e) => e.stopPropagation()} role="document">
		{#if entity.type === 'note'}
			<form onsubmit={handleSubmit} class="widget note-widget">
				<input type="text" bind:value={title} placeholder="Note title..." class="title-input" required />
				<HashtagTextarea bind:value={content} rows={2} autoSize placeholder="Content (optional) — type # to insert tags..." />
				<DefaultTagSuggestions category="note" bind:selectedTagIds />
				{@render actionButtons('note-save')}
			</form>

		{:else if entity.type === 'project'}
			<form onsubmit={handleSubmit} class="widget project-widget">
				<input type="text" bind:value={title} placeholder="Project title..." class="title-input" required />
				<div class="fields-row">
					<select bind:value={status} class="field-select">
						<option value="in_progress">In Progress</option>
						<option value="on_hold">On Hold</option>
						<option value="completed">Completed</option>
						<option value="archived">Archived</option>
					</select>
					<input type="datetime-local" bind:value={startDate} class="field-input" />
				</div>
				<textarea bind:this={descEl} bind:value={description} rows="2" placeholder="Description (optional)" class="field-textarea"></textarea>
				<DefaultTagSuggestions category="project" bind:selectedTagIds />
				{@render actionButtons('project-save')}
			</form>

		{:else if entity.type === 'log'}
			<form onsubmit={handleSubmit} class="widget log-widget">
				<input type="text" bind:value={title} placeholder="Log title..." class="title-input" required />
				<input type="text" bind:value={location} placeholder="Location" class="field-input" />
				<HashtagTextarea bind:value={content} rows={2} autoSize placeholder="Content (optional) — type # to insert tags" />
				<DefaultTagSuggestions category="log" bind:selectedTagIds />
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
				{@render actionButtons('log-save')}
			</form>

		{:else if entity.type === 'activity'}
			<form onsubmit={handleSubmit} class="widget activity-widget">
				<input type="text" bind:value={title} placeholder="Activity title..." class="title-input" required />
				<input type="number" bind:value={duration} min="0" placeholder="Duration (minutes)" class="field-input" />
				<HashtagTextarea bind:value={description} rows={3} autoSize placeholder="Description (optional) — type # to insert tags..." />
				<DefaultTagSuggestions category="activity" bind:selectedTagIds {keywordMatches} />
				{@render actionButtons('activity-save')}
			</form>

		{:else if entity.type === 'source'}
			<form onsubmit={handleSubmit} class="widget source-widget">
				<input type="text" bind:value={title} placeholder="Source title..." class="title-input" required />
				<input type="text" bind:value={author} placeholder="Author" class="field-input" />
				<input type="text" bind:value={sourceType} placeholder="Type (e.g. book, article, video)" class="field-input" />
				<input type="url" bind:value={contentUrl} placeholder="URL (https://...)" class="field-input" />
				<textarea bind:this={descEl} bind:value={description} rows="2" placeholder="Description (optional)" class="field-textarea"></textarea>
				<DefaultTagSuggestions category="source" bind:selectedTagIds />
				{@render actionButtons('source-save')}
			</form>

		{:else if entity.type === 'actor'}
			<form onsubmit={handleSubmit} class="widget actor-widget">
				<input type="text" bind:value={fullName} placeholder="Full name..." class="title-input" required />
				<div class="fields-row">
					<input type="text" bind:value={role} placeholder="Role" class="field-input" />
					<input type="text" bind:value={affiliation} placeholder="Affiliation" class="field-input" />
				</div>
				<input type="text" bind:value={expertise} placeholder="Expertise" class="field-input" />
				<div class="fields-row">
					<input type="email" bind:value={email} placeholder="Email" class="field-input" />
					<input type="url" bind:value={url} placeholder="URL (https://...)" class="field-input" />
				</div>
				<textarea bind:this={notesEl} bind:value={notes} rows="2" placeholder="Notes (optional)" class="field-textarea"></textarea>
				<DefaultTagSuggestions category="actor" bind:selectedTagIds />
				{@render actionButtons('actor-save')}
			</form>

		{:else if entity.type === 'reading_list'}
			<form onsubmit={handleSubmit} class="widget reading-list-widget">
				<input type="text" bind:value={title} placeholder="Reading list title..." class="title-input" required />
				<textarea bind:this={descEl} bind:value={description} rows="2" placeholder="Description (optional)" class="field-textarea"></textarea>
				<DefaultTagSuggestions category="readinglist" bind:selectedTagIds />
				{@render actionButtons('reading-list-save')}
			</form>

		{:else if entity.type === 'plan'}
			<form onsubmit={handleSubmit} class="widget plan-widget">
				<input type="text" bind:value={title} placeholder="Plan title..." class="title-input" required />
				<textarea bind:this={descEl} bind:value={description} rows="2" placeholder="Description (optional)" class="field-textarea"></textarea>
				<input type="text" bind:value={motivation} placeholder="Motivation (optional)" class="field-input" />
				<input type="text" bind:value={outcome} placeholder="Expected outcome (optional)" class="field-input" />
				<div class="date-row">
					<label class="date-label">Start <input type="date" bind:value={startDate} class="date-input" /></label>
					<label class="date-label">End <input type="date" bind:value={endDate} class="date-input" /></label>
				</div>
				<div class="items-section">
					<div class="items-label">Activities</div>
					{#each plannedItems as item, i (i)}
						<div class="planned-item">
							<input type="checkbox" disabled />
							<input
								type="text"
								class="planned-item-text"
								value={item}
								onchange={(e) => updatePlanItemText(i, (e.target as HTMLInputElement).value)}
							/>
							<button type="button" class="btn-remove-item" onclick={() => removePlanItem(i)}>&minus;</button>
						</div>
					{/each}
					<div class="add-item-row">
						<input
							type="text"
							class="add-item-input"
							placeholder="New activity..."
							bind:value={newItemText}
							onkeydown={(e) => { if (e.key === 'Enter') { e.preventDefault(); addPlanItem(); } }}
						/>
						<button type="button" class="btn-add-item" onclick={addPlanItem}>+</button>
					</div>
				</div>
				<DefaultTagSuggestions category="plan" bind:selectedTagIds />
				{@render actionButtons('plan-save')}
			</form>
		{/if}
	</div>
</div>

<style>
	.overlay {
		position: fixed;
		inset: 0;
		background: rgba(0, 0, 0, 0.4);
		display: flex;
		align-items: center;
		justify-content: center;
		z-index: 1000;
	}
	.edit-panel {
		min-width: 400px;
		max-width: 600px;
		max-height: 85vh;
		overflow-y: auto;
	}

	/* Shared form styles — matching Cards tab exactly */
	.widget { display: flex; flex-direction: column; gap: 6px; padding: 10px; border-radius: 8px; margin-bottom: 0; box-shadow: 0 8px 30px rgba(0, 0, 0, 0.2); }
	.title-input { padding: 6px 8px; border: 1px solid #d1d5db; border-radius: 6px; font-size: 0.85rem; }
	.fields-row { display: flex; gap: 6px; }
	.field-input { flex: 1; padding: 6px 8px; border: 1px solid #d1d5db; border-radius: 6px; font-size: 0.85rem; }
	.field-select { padding: 6px 8px; border: 1px solid #d1d5db; border-radius: 6px; font-size: 0.85rem; }
	.field-textarea { padding: 6px 8px; border: 1px solid #d1d5db; border-radius: 6px; font-size: 0.85rem; resize: vertical; font-family: inherit; }

	/* Action buttons at the bottom */
	.button-row { display: flex; justify-content: flex-end; gap: 6px; padding-top: 4px; }
	.btn-save { padding: 6px 14px; color: white; border: none; border-radius: 6px; cursor: pointer; font-size: 0.8rem; font-weight: 500; }
	.btn-cancel { padding: 6px 14px; background: white; color: #6b7280; border: 1px solid #d1d5db; border-radius: 6px; cursor: pointer; font-size: 0.8rem; font-weight: 500; }
	.btn-cancel:hover { background: #f3f4f6; }

	/* Per-entity colors — matching Cards tab creation forms exactly */
	.note-widget { background: #ecfdf5; border: 1px solid #d1fae5; }
	:global(.note-save) { background: #10b981; }
	:global(.note-save:hover) { background: #059669; }

	.project-widget { background: #eff6ff; border: 1px solid #bfdbfe; }
	:global(.project-save) { background: #3b82f6; }
	:global(.project-save:hover) { background: #2563eb; }

	.log-widget { background: #faf8f5; border: 1px solid #e8e0d4; }
	:global(.log-save) { background: #8b7355; }
	:global(.log-save:hover) { background: #74603f; }

	.activity-widget { background: #f5f3ff; border: 1px solid #ddd6fe; }
	:global(.activity-save) { background: #8b5cf6; }
	:global(.activity-save:hover) { background: #7c3aed; }

	.source-widget { background: #fffbeb; border: 1px solid #fde68a; }
	:global(.source-save) { background: #f59e0b; }
	:global(.source-save:hover) { background: #d97706; }

	.actor-widget { background: #fef2f2; border: 1px solid #fecaca; }
	:global(.actor-save) { background: #ef4444; }
	:global(.actor-save:hover) { background: #dc2626; }

	.reading-list-widget { background: #ecfeff; border: 1px solid #a5f3fc; }
	:global(.reading-list-save) { background: #06b6d4; }
	:global(.reading-list-save:hover) { background: #0891b2; }

	.plan-widget { background: #f0f7fa; border: 1px solid #b3d9e6; }
	:global(.plan-save) { background: #4a90a4; }
	:global(.plan-save:hover) { background: #3d7a8c; }

	/* Plan-specific styles */
	.date-row { display: flex; gap: 8px; }
	.date-label { display: flex; align-items: center; gap: 4px; font-size: 0.8rem; color: #6b7280; }
	.date-input { padding: 4px 6px; border: 1px solid #d1d5db; border-radius: 6px; font-size: 0.8rem; }

	.items-section { display: flex; flex-direction: column; gap: 4px; padding: 6px 0; }
	.items-label { font-size: 0.75rem; font-weight: 600; color: #4a90a4; text-transform: uppercase; letter-spacing: 0.03em; }
	.planned-item { display: flex; align-items: center; gap: 6px; }
	.planned-item input[type="checkbox"] { pointer-events: none; opacity: 0.5; }
	.planned-item-text { flex: 1; padding: 4px 6px; border: 1px solid #e5e7eb; border-radius: 4px; font-size: 0.8rem; background: white; }
	.btn-remove-item { background: none; border: none; cursor: pointer; color: #ef4444; font-size: 0.85rem; font-weight: 600; padding: 0 4px; }
	.add-item-row { display: flex; gap: 4px; }
	.add-item-input { flex: 1; padding: 5px 8px; border: 1px solid #d1d5db; border-radius: 4px; font-size: 0.8rem; }
	.btn-add-item { padding: 4px 10px; background: #4a90a4; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 0.85rem; font-weight: 600; }

	/* Emoji picker — matching DiaryForm */
	.emoji-row { display: flex; align-items: center; gap: 4px; flex-wrap: wrap; }
	.emoji-label { font-size: 0.7rem; color: #6b7280; font-weight: 500; min-width: 50px; }
	.emoji-chip { font-size: 1rem; padding: 2px 4px; border: 1px solid transparent; border-radius: 6px; background: none; cursor: pointer; line-height: 1; transition: all 0.1s; }
	.emoji-chip:hover { background: #f3f4f6; }
	.emoji-chip.selected { border-color: #3b82f6; background: #eff6ff; }
</style>
