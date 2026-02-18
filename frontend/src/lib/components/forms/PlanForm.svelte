<script lang="ts">
	import type { Plan } from '$lib/types';
	import { createPlan, updatePlan, addPlanItem } from '$lib/api/plans';
	import { createActivity } from '$lib/api/activities';
	import { loadPlans } from '$lib/stores/plans';
	import { loadActivities } from '$lib/stores/activities';
	import { loadTags } from '$lib/stores/tags';
	import { attachTag, searchTags, createWildTag } from '$lib/api/tags';
	import DefaultTagSuggestions from '../shared/DefaultTagSuggestions.svelte';
	import { onMount } from 'svelte';

	let { onDone, editData }: { onDone: (createdId?: number) => void; editData?: Plan } = $props();

	let title = $state(editData?.title ?? '');
	let description = $state(editData?.description ?? '');
	let motivation = $state(editData?.motivation ?? '');
	let outcome = $state(editData?.outcome ?? '');
	let startDate = $state(editData?.start_date ?? '');
	let endDate = $state(editData?.end_date ?? '');
	let selectedTagIds = $state<number[]>([]);

	// Plan items with section headers
	interface PlannedItem { title: string; header: string | null; }
	let plannedItems = $state<PlannedItem[]>([]);
	let sectionHeaders = $state<string[]>([]);
	let newItemTexts = $state<Record<string, string>>({});
	let addingSection = $state(false);
	let newSectionName = $state('');

	let descEl: HTMLTextAreaElement | undefined = $state();

	onMount(() => {
		if (editData && descEl) {
			const maxH = window.innerHeight * 0.45;
			descEl.style.height = 'auto';
			descEl.style.height = Math.min(descEl.scrollHeight, maxH) + 'px';
		}
	});

	function sKey(header: string | null): string {
		return header ?? '__ungrouped__';
	}

	function getNewItemText(header: string | null): string {
		return newItemTexts[sKey(header)] ?? '';
	}

	function setNewItemText(header: string | null, value: string) {
		newItemTexts = { ...newItemTexts, [sKey(header)]: value };
	}

	function addItem(header: string | null) {
		const text = getNewItemText(header);
		if (!text.trim()) return;
		plannedItems = [...plannedItems, { title: text.trim(), header }];
		setNewItemText(header, '');
	}

	function removeItem(index: number) {
		plannedItems = plannedItems.filter((_, i) => i !== index);
	}

	function addSection() {
		if (!newSectionName.trim()) return;
		const name = newSectionName.trim();
		if (!sectionHeaders.includes(name)) {
			sectionHeaders = [...sectionHeaders, name];
		}
		newSectionName = '';
		addingSection = false;
	}

	function removeSection(header: string) {
		plannedItems = plannedItems.map(item =>
			item.header === header ? { ...item, header: null } : item
		);
		sectionHeaders = sectionHeaders.filter(h => h !== header);
	}

	// Drag-and-drop between sections
	let draggedIndex = $state<number | null>(null);
	let dropTargetSection = $state<string | null>(null);

	function handleItemDragStart(originalIndex: number, e: DragEvent) {
		draggedIndex = originalIndex;
		if (e.dataTransfer) {
			e.dataTransfer.effectAllowed = 'move';
			e.dataTransfer.setData('text/plain', '');
		}
	}

	function handleSectionDragOver(header: string | null, e: DragEvent) {
		if (draggedIndex === null) return;
		const fromHeader = plannedItems[draggedIndex]?.header ?? null;
		if (fromHeader === (header ?? null)) return;
		e.preventDefault();
		if (e.dataTransfer) e.dataTransfer.dropEffect = 'move';
		dropTargetSection = sKey(header);
	}

	function handleSectionDragLeave(e: DragEvent) {
		const currentTarget = e.currentTarget as HTMLElement;
		const relatedTarget = e.relatedTarget as HTMLElement | null;
		if (!relatedTarget || !currentTarget.contains(relatedTarget)) {
			dropTargetSection = null;
		}
	}

	function handleSectionDrop(header: string | null, e: DragEvent) {
		e.preventDefault();
		dropTargetSection = null;
		if (draggedIndex === null) return;
		plannedItems[draggedIndex] = { ...plannedItems[draggedIndex], header };
		plannedItems = [...plannedItems];
		draggedIndex = null;
	}

	function handleDragEnd() {
		draggedIndex = null;
		dropTargetSection = null;
	}

	interface FormSectionItem { title: string; header: string | null; originalIndex: number; }
	interface FormSection { header: string | null; items: FormSectionItem[]; }

	let formSections = $derived.by(() => {
		const indexed = plannedItems.map((item, idx) => ({ ...item, originalIndex: idx }));
		const sections: FormSection[] = [];
		sections.push({ header: null, items: indexed.filter(i => i.header === null) });
		for (const h of sectionHeaders) {
			sections.push({ header: h, items: indexed.filter(i => i.header === h) });
		}
		return sections;
	});

	async function handleSubmit(e: SubmitEvent) {
		e.preventDefault();
		e.stopPropagation();
		if (!title.trim()) return;
		try {
			const data = {
				title: title.trim(),
				description: description.trim() || undefined,
				motivation: motivation.trim() || undefined,
				outcome: outcome.trim() || undefined,
				start_date: startDate || undefined,
				end_date: endDate || undefined
			};
			let createdId: number | undefined;
			if (editData) {
				await updatePlan(editData.id, data);
			} else {
				const created = await createPlan(data);
				createdId = created.id;
				for (const tagId of selectedTagIds) {
					await attachTag(tagId, 'plan', created.id);
				}
				// Create activities from planned items
				if (plannedItems.length > 0) {
					const todoResults = await searchTags('ToDo');
					const todoTag = todoResults.find(t => t.name.toLowerCase() === 'todo') ?? await createWildTag('ToDo', undefined, 'activity');
					const planTagResults = await searchTags(title.trim());
					const planTag = planTagResults.find(t => t.entity_type === 'plan' && t.entity_id === created.id);
					for (let i = 0; i < plannedItems.length; i++) {
						const activity = await createActivity({ title: plannedItems[i].title });
						await attachTag(todoTag.id, 'activity', activity.id);
						if (planTag) await attachTag(planTag.id, 'activity', activity.id);
						await addPlanItem(created.id, {
							activity_id: activity.id,
							position: i,
							header: plannedItems[i].header ?? undefined
						});
					}
				}
				await loadActivities();
			}
			await Promise.all([loadPlans(), loadTags()]);
			onDone(createdId);
		} catch (err) {
			console.error('[PlanForm] Submit error:', err);
		}
	}
</script>

<form onsubmit={handleSubmit} class="widget">
	<input type="text" bind:value={title} required placeholder="Plan title..." class="title-input" />
	<textarea bind:this={descEl} bind:value={description} rows="2" placeholder="Description (optional)" class="field-textarea"></textarea>
	<input type="text" bind:value={motivation} placeholder="Motivation (optional)" class="field-input" />
	<input type="text" bind:value={outcome} placeholder="Expected outcome (optional)" class="field-input" />
	<div class="date-row">
		<label class="date-label">Start <input type="date" bind:value={startDate} class="date-input" /></label>
		<label class="date-label">End <input type="date" bind:value={endDate} class="date-input" /></label>
	</div>
	{#if !editData}
		<div class="items-section">
			{#each formSections as section}
				<!-- svelte-ignore a11y_no_static_element_interactions -->
				<div
					class="section-drop-zone"
					class:drop-target={dropTargetSection === sKey(section.header) && draggedIndex !== null && (plannedItems[draggedIndex]?.header ?? null) !== (section.header ?? null)}
					ondragover={(e) => handleSectionDragOver(section.header, e)}
					ondragleave={handleSectionDragLeave}
					ondrop={(e) => handleSectionDrop(section.header, e)}
				>
					{#if section.header !== null}
						<div class="section-header-bar">
							<span class="section-header-name">{section.header}</span>
							<button type="button" class="btn-remove-section" onclick={() => removeSection(section.header!)}>x</button>
						</div>
					{:else}
						<div class="items-label">Activities</div>
					{/if}
					{#each section.items as item}
						<div
							class="planned-item"
							class:dragging={draggedIndex === item.originalIndex}
							draggable="true"
							ondragstart={(e) => handleItemDragStart(item.originalIndex, e)}
							ondragend={handleDragEnd}
						>
							<span class="drag-grip">⠿</span>
							<input type="checkbox" disabled />
							<input
								type="text"
								class="planned-item-text"
								value={item.title}
								onchange={(e) => { plannedItems[item.originalIndex] = { ...plannedItems[item.originalIndex], title: (e.target as HTMLInputElement).value }; }}
							/>
							<button type="button" class="btn-remove-item" onclick={() => removeItem(item.originalIndex)}>&minus;</button>
						</div>
					{/each}
					<div class="add-item-row">
						<input
							type="text"
							class="add-item-input"
							placeholder="New activity..."
							value={getNewItemText(section.header)}
							oninput={(e) => setNewItemText(section.header, e.currentTarget.value)}
							onkeydown={(e) => { if (e.key === 'Enter') { e.preventDefault(); addItem(section.header); } }}
						/>
						<button type="button" class="btn-add-item" onclick={() => addItem(section.header)}>+</button>
					</div>
				</div>
			{/each}
			{#if addingSection}
				<div class="add-section-row">
					<input
						type="text"
						class="add-section-input-field"
						placeholder="Section name..."
						bind:value={newSectionName}
						onkeydown={(e) => { if (e.key === 'Enter') { e.preventDefault(); addSection(); } else if (e.key === 'Escape') { addingSection = false; newSectionName = ''; } }}
					/>
					<button type="button" class="btn-add-item" onclick={addSection}>+</button>
					<button type="button" class="btn-cancel-section" onclick={() => { addingSection = false; newSectionName = ''; }}>Cancel</button>
				</div>
			{:else}
				<button type="button" class="btn-add-section" onclick={() => { addingSection = true; newSectionName = ''; }}>+ Section</button>
			{/if}
		</div>
		<DefaultTagSuggestions category="plan" bind:selectedTagIds />
	{/if}
	<div class="button-row">
		<button type="button" class="btn-cancel" onclick={onDone}>Cancel</button>
		<button type="submit" class="btn-save">{editData ? 'Save' : 'Create'}</button>
	</div>
</form>

<style>
	.widget { display: flex; flex-direction: column; gap: 6px; padding: 10px; background: #f0f7fa; border: 1px solid #b3d9e6; border-radius: 8px; margin-bottom: 12px; }
	.title-input { padding: 6px 8px; border: 1px solid #d1d5db; border-radius: 6px; font-size: 0.85rem; }
	.button-row { display: flex; justify-content: flex-end; gap: 6px; padding-top: 4px; }
	.field-textarea { padding: 6px 8px; border: 1px solid #d1d5db; border-radius: 6px; font-size: 0.85rem; resize: vertical; font-family: inherit; }
	.field-input { padding: 6px 8px; border: 1px solid #d1d5db; border-radius: 6px; font-size: 0.85rem; }
	.date-row { display: flex; gap: 8px; }
	.date-label { display: flex; align-items: center; gap: 4px; font-size: 0.8rem; color: #6b7280; }
	.date-input { padding: 4px 6px; border: 1px solid #d1d5db; border-radius: 6px; font-size: 0.8rem; }
	.btn-save { padding: 6px 14px; background: #4a90a4; color: white; border: none; border-radius: 6px; cursor: pointer; font-size: 0.8rem; font-weight: 500; }
	.btn-save:hover { background: #3d7a8c; }
	.btn-cancel { padding: 6px 14px; background: white; color: #6b7280; border: 1px solid #d1d5db; border-radius: 6px; cursor: pointer; font-size: 0.8rem; font-weight: 500; }
	.btn-cancel:hover { background: #f3f4f6; }

	.items-section { display: flex; flex-direction: column; gap: 4px; padding: 6px 0; }
	.items-label { font-size: 0.75rem; font-weight: 600; color: #4a90a4; text-transform: uppercase; letter-spacing: 0.03em; }
	.planned-item { display: flex; align-items: center; gap: 6px; }
	.planned-item input[type="checkbox"] { pointer-events: none; opacity: 0.5; }
	.planned-item-text { flex: 1; padding: 4px 6px; border: 1px solid #e5e7eb; border-radius: 4px; font-size: 0.8rem; background: white; }
	.btn-remove-item { background: none; border: none; cursor: pointer; color: #ef4444; font-size: 0.85rem; font-weight: 600; padding: 0 4px; }
	.add-item-row { display: flex; gap: 4px; }
	.add-item-input { flex: 1; padding: 5px 8px; border: 1px solid #d1d5db; border-radius: 4px; font-size: 0.8rem; }
	.btn-add-item { padding: 4px 10px; background: #4a90a4; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 0.85rem; font-weight: 600; }

	/* Section headers */
	.section-header-bar { display: flex; align-items: center; gap: 6px; margin-top: 6px; padding: 4px 8px; background: #eef3f7; border-radius: 4px; border-left: 3px solid #4a90a4; }
	.section-header-name { flex: 1; font-size: 0.78rem; font-weight: 600; color: #374151; }
	.btn-remove-section { background: none; border: none; cursor: pointer; font-size: 0.75rem; font-weight: 700; color: #9ca3af; padding: 0 4px; }
	.btn-remove-section:hover { color: #ef4444; }
	.btn-add-section { display: block; margin-top: 6px; padding: 3px 10px; font-size: 0.72rem; background: #f0f7fa; color: #4a90a4; border: 1px dashed #b3d9e6; border-radius: 4px; cursor: pointer; font-weight: 500; }
	.btn-add-section:hover { background: #e0eef5; }
	.add-section-row { display: flex; gap: 4px; margin-top: 6px; }
	.add-section-input-field { flex: 1; padding: 4px 8px; border: 1px solid #d1d5db; border-radius: 4px; font-size: 0.78rem; }
	.btn-cancel-section { font-size: 0.7rem; padding: 2px 8px; background: white; border: 1px solid #d1d5db; border-radius: 4px; cursor: pointer; }

	/* Drag-and-drop */
	.section-drop-zone { border-radius: 6px; border: 2px solid transparent; padding: 2px; transition: border-color 0.15s, background 0.15s; }
	.section-drop-zone.drop-target { border-color: #4a90a4; background: rgba(74, 144, 164, 0.06); }
	.drag-grip { cursor: grab; color: #d1d5db; font-size: 0.7rem; user-select: none; line-height: 1; }
	.drag-grip:hover { color: #9ca3af; }
	.planned-item.dragging { opacity: 0.4; }
</style>
