<script lang="ts">
	import type { Actor } from '$lib/types';
	import { createActor, updateActor } from '$lib/api/actors';
	import { loadActors } from '$lib/stores/actors';
	import { loadTags } from '$lib/stores/tags';
	import { attachTag } from '$lib/api/tags';
	import DefaultTagSuggestions from '../shared/DefaultTagSuggestions.svelte';
	import { onMount } from 'svelte';

	let { onDone, editData, onCreate }: { onDone: () => void; editData?: Actor; onCreate?: (id: number) => void } = $props();

	let fullName = $state(editData?.full_name ?? '');
	let role = $state(editData?.role ?? '');
	let affiliation = $state(editData?.affiliation ?? '');
	let expertise = $state(editData?.expertise ?? '');
	let notes = $state(editData?.notes ?? '');
	let email = $state(editData?.email ?? '');
	let url = $state(editData?.url ?? '');
	let selectedTagIds = $state<number[]>([]);

	let notesEl: HTMLTextAreaElement | undefined = $state();

	onMount(() => {
		if (editData && notesEl) {
			const maxH = window.innerHeight * 0.45;
			notesEl.style.height = 'auto';
			notesEl.style.height = Math.min(notesEl.scrollHeight, maxH) + 'px';
		}
	});

	async function handleSubmit(e: SubmitEvent) {
		e.preventDefault();
		if (!fullName.trim()) return;
		const data = {
			full_name: fullName.trim(),
			role: role.trim() || undefined,
			affiliation: affiliation.trim() || undefined,
			expertise: expertise.trim() || undefined,
			notes: notes.trim() || undefined,
			email: email.trim() || undefined,
			url: url.trim() || undefined
		};
		let actorId: number;
		if (editData) {
			await updateActor(editData.id, data);
			actorId = editData.id;
		} else {
			const created = await createActor(data);
			actorId = created.id;
			for (const tagId of selectedTagIds) {
				await attachTag(tagId, 'actor', actorId);
			}
		}
		await Promise.all([loadActors(), loadTags()]);
		if (!editData) {
			onCreate?.(actorId);
		}
		onDone();
	}
</script>

<form onsubmit={handleSubmit} class="widget" class:editing={!!editData}>
	<input type="text" bind:value={fullName} required placeholder="Full name..." class="title-input" />
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
	{#if !editData}
		<DefaultTagSuggestions category="actor" bind:selectedTagIds title={fullName} />
	{/if}
	<div class="button-row">
		<button type="button" class="btn-cancel" onclick={onDone}>Cancel</button>
		<button type="submit" class="btn-save">{editData ? 'Save' : 'Create'}</button>
	</div>
</form>

<style>
	.widget { display: flex; flex-direction: column; gap: 6px; padding: 10px; background: #fef2f2; border: 1px solid #fecaca; border-radius: 8px; margin-bottom: 12px; }
	.widget.editing { background: #fefce8; border-color: #fde68a; }
	.title-input { padding: 6px 8px; border: 1px solid #d1d5db; border-radius: 6px; font-size: 0.85rem; }
	.button-row { display: flex; justify-content: flex-end; gap: 6px; padding-top: 4px; }
	.fields-row { display: flex; gap: 6px; }
	.field-input { flex: 1; padding: 6px 8px; border: 1px solid #d1d5db; border-radius: 6px; font-size: 0.85rem; }
	.field-textarea { padding: 6px 8px; border: 1px solid #d1d5db; border-radius: 6px; font-size: 0.85rem; resize: vertical; font-family: inherit; }
	.btn-save { padding: 6px 14px; background: #ef4444; color: white; border: none; border-radius: 6px; cursor: pointer; font-size: 0.8rem; font-weight: 500; }
	.btn-save:hover { background: #dc2626; }
	.btn-cancel { padding: 6px 14px; background: white; color: #6b7280; border: 1px solid #d1d5db; border-radius: 6px; cursor: pointer; font-size: 0.8rem; font-weight: 500; }
	.btn-cancel:hover { background: #f3f4f6; }
</style>
