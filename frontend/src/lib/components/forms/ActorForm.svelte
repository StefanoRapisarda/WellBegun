<script lang="ts">
	import type { Actor } from '$lib/types';
	import { createActor, updateActor } from '$lib/api/actors';
	import { loadActors } from '$lib/stores/actors';
	import { loadTags } from '$lib/stores/tags';
	import { attachTag } from '$lib/api/tags';
	import DefaultTagSuggestions from '../shared/DefaultTagSuggestions.svelte';

	let { onDone, editData, onCreate }: { onDone: () => void; editData?: Actor; onCreate?: (id: number) => void } = $props();

	let fullName = $state(editData?.full_name ?? '');
	let role = $state(editData?.role ?? '');
	let affiliation = $state(editData?.affiliation ?? '');
	let expertise = $state(editData?.expertise ?? '');
	let notes = $state(editData?.notes ?? '');
	let email = $state(editData?.email ?? '');
	let url = $state(editData?.url ?? '');
	let selectedTagIds = $state<number[]>([]);

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

<form onsubmit={handleSubmit} class="form">
	<label>
		Full Name *
		<input type="text" bind:value={fullName} required />
	</label>
	<label>
		Role
		<input type="text" bind:value={role} />
	</label>
	<label>
		Affiliation
		<input type="text" bind:value={affiliation} />
	</label>
	<label>
		Expertise
		<input type="text" bind:value={expertise} />
	</label>
	<label>
		Notes
		<textarea bind:value={notes} rows="2"></textarea>
	</label>
	<label>
		Email
		<input type="email" bind:value={email} />
	</label>
	<label>
		URL
		<input type="url" bind:value={url} placeholder="https://..." />
	</label>
	{#if !editData}
		<DefaultTagSuggestions category="actor" bind:selectedTagIds />
	{/if}
	<div class="form-actions">
		<button type="button" class="btn btn-cancel" onclick={onDone}>Cancel</button>
		<button type="submit" class="btn btn-primary">{editData ? 'Save' : 'Create'}</button>
	</div>
</form>

<style>
	.form { display: flex; flex-direction: column; gap: 12px; }
	label { display: flex; flex-direction: column; gap: 4px; font-size: 0.875rem; font-weight: 500; color: #374151; }
	input, textarea { padding: 8px; border: 1px solid #d1d5db; border-radius: 6px; font-size: 0.875rem; }
	.form-actions { display: flex; gap: 8px; justify-content: flex-end; margin-top: 8px; }
	.btn { padding: 8px 16px; border-radius: 6px; border: 1px solid #d1d5db; cursor: pointer; font-size: 0.875rem; }
	.btn-cancel { background: white; }
	.btn-primary { background: #ef4444; color: white; border-color: #ef4444; }
</style>
