<script lang="ts">
	import { onMount } from 'svelte';
	import { ENTITY_CONFIG, type NotepadEntityType } from '$lib/notepad/types';
	import { getEntityTags, type Tag } from '$lib/api/tags';
	import { getProject } from '$lib/api/projects';
	import { getNote } from '$lib/api/notes';
	import { getLog } from '$lib/api/logs';
	import { getActivity } from '$lib/api/activities';
	import { getSource } from '$lib/api/sources';
	import { getActor } from '$lib/api/actors';
	import { getPlan } from '$lib/api/plans';
	import DraggableWindow from '$lib/components/shared/DraggableWindow.svelte';
	import EntityIcon from '$lib/components/shared/EntityIcon.svelte';
	import ProjectForm from '$lib/components/forms/ProjectForm.svelte';
	import NoteForm from '$lib/components/forms/NoteForm.svelte';
	import LogEditForm from '$lib/components/forms/LogEditForm.svelte';
	import ActivityForm from '$lib/components/forms/ActivityForm.svelte';
	import SourceForm from '$lib/components/forms/SourceForm.svelte';
	import ActorForm from '$lib/components/forms/ActorForm.svelte';
	import PlanForm from '$lib/components/forms/PlanForm.svelte';

	let { entityType, entityId, onClose }: {
		entityType: string;
		entityId: number;
		onClose: () => void;
	} = $props();

	let entity = $state<any>(null);
	let tags = $state<Tag[]>([]);
	let editing = $state(false);
	let loading = $state(true);

	const FETCH_MAP: Record<string, (id: number) => Promise<any>> = {
		project: getProject,
		note: getNote,
		log: getLog,
		activity: getActivity,
		source: getSource,
		actor: getActor,
		plan: getPlan,
	};

	const VIEW_FIELDS: Record<string, { key: string; label: string }[]> = {
		project: [
			{ key: 'description', label: 'Description' },
			{ key: 'status', label: 'Status' },
			{ key: 'start_date', label: 'Start Date' },
		],
		note: [
			{ key: 'content', label: 'Content' },
		],
		log: [
			{ key: 'content', label: 'Content' },
			{ key: 'location', label: 'Location' },
			{ key: 'mood', label: 'Mood' },
			{ key: 'weather', label: 'Weather' },
			{ key: 'day_theme', label: 'Theme' },
		],
		activity: [
			{ key: 'description', label: 'Description' },
			{ key: 'duration', label: 'Duration (min)' },
			{ key: 'status', label: 'Status' },
			{ key: 'outcome', label: 'Outcome' },
		],
		source: [
			{ key: 'description', label: 'Description' },
			{ key: 'author', label: 'Author' },
			{ key: 'content_url', label: 'URL' },
			{ key: 'source_type', label: 'Type' },
		],
		actor: [
			{ key: 'role', label: 'Role' },
			{ key: 'affiliation', label: 'Affiliation' },
			{ key: 'expertise', label: 'Expertise' },
			{ key: 'email', label: 'Email' },
			{ key: 'url', label: 'URL' },
			{ key: 'notes', label: 'Notes' },
		],
		plan: [
			{ key: 'description', label: 'Description' },
			{ key: 'motivation', label: 'Motivation' },
			{ key: 'outcome', label: 'Outcome' },
			{ key: 'start_date', label: 'Start Date' },
			{ key: 'end_date', label: 'End Date' },
		],
	};

	async function fetchData() {
		loading = true;
		try {
			const fetcher = FETCH_MAP[entityType];
			if (fetcher) {
				const [entityData, tagData] = await Promise.all([
					fetcher(entityId),
					getEntityTags(entityType, entityId),
				]);
				entity = entityData;
				tags = tagData;
			}
		} catch (err) {
			console.error('Failed to fetch entity:', err);
		} finally {
			loading = false;
		}
	}

	onMount(() => { fetchData(); });

	function handleEditDone() {
		editing = false;
		fetchData();
	}

	function entityTitle(e: any): string {
		return e.title ?? e.full_name ?? 'Untitled';
	}

	function formatDate(val: string): string {
		try {
			return new Date(val).toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' });
		} catch {
			return val;
		}
	}

	function isDateField(key: string): boolean {
		return key.endsWith('_date') || key === 'created_at' || key === 'updated_at';
	}

	let accentColor = $derived(ENTITY_CONFIG[entityType as NotepadEntityType]?.color ?? '#6b7280');

	function typeLabel(type: string): string {
		return type.replace('_', ' ').replace(/\b\w/g, c => c.toUpperCase());
	}
</script>

<DraggableWindow title={typeLabel(entityType)} {onClose} {accentColor}>
	{#if loading}
		<div class="loading">Loading...</div>
	{:else if !entity}
		<div class="loading">Entity not found.</div>
	{:else if editing}
		<div class="edit-container">
			{#if entityType === 'project'}
				<ProjectForm onDone={handleEditDone} editData={entity} />
			{:else if entityType === 'note'}
				<NoteForm onDone={handleEditDone} editData={entity} />
			{:else if entityType === 'log'}
				<LogEditForm onDone={handleEditDone} editData={entity} />
			{:else if entityType === 'activity'}
				<ActivityForm onDone={handleEditDone} editData={entity} />
			{:else if entityType === 'source'}
				<SourceForm onDone={handleEditDone} editData={entity} />
			{:else if entityType === 'actor'}
				<ActorForm onDone={handleEditDone} editData={entity} />
			{:else if entityType === 'plan'}
				<PlanForm onDone={handleEditDone} editData={entity} />
			{/if}
		</div>
	{:else}
		<div class="view">
			<div class="entity-header">
				<EntityIcon type={entityType} size={20} />
				<span class="entity-title">{entityTitle(entity)}</span>
			</div>

			{#if entity.is_active !== undefined || entity.is_archived !== undefined}
				<div class="badges">
					{#if entity.is_active}
						<span class="badge active">Active</span>
					{/if}
					{#if entity.is_archived}
						<span class="badge archived">Archived</span>
					{/if}
				</div>
			{/if}

			{#each VIEW_FIELDS[entityType] ?? [] as field}
				{#if entity[field.key] != null && entity[field.key] !== ''}
					<div class="field">
						<div class="field-label">{field.label}</div>
						<div class="field-value">
							{#if isDateField(field.key)}
								{formatDate(entity[field.key])}
							{:else}
								{entity[field.key]}
							{/if}
						</div>
					</div>
				{/if}
			{/each}

			{#if tags.length > 0}
				<div class="field">
					<div class="field-label">Tags</div>
					<div class="tag-list">
						{#each tags as tag}
							<span class="tag-badge" style:background={tag.color ?? '#e5e7eb'}>
								{tag.name}
							</span>
						{/each}
					</div>
				</div>
			{/if}

			{#if entity.created_at}
				<div class="field">
					<div class="field-label">Created</div>
					<div class="field-value muted">{formatDate(entity.created_at)}</div>
				</div>
			{/if}
			{#if entity.updated_at}
				<div class="field">
					<div class="field-label">Updated</div>
					<div class="field-value muted">{formatDate(entity.updated_at)}</div>
				</div>
			{/if}

			<div class="footer">
				<button class="btn-edit" onclick={() => editing = true}>Edit</button>
			</div>
		</div>
	{/if}
</DraggableWindow>

<style>
	.loading {
		text-align: center;
		color: #9ca3af;
		font-size: 0.85rem;
		padding: 24px 0;
	}
	.view {
		display: flex;
		flex-direction: column;
		gap: 12px;
	}
	.entity-header {
		display: flex;
		align-items: center;
		gap: 8px;
		padding-bottom: 8px;
		border-bottom: 1px solid #e5e7eb;
	}
	.entity-title {
		font-size: 1rem;
		font-weight: 600;
		color: #1f2937;
	}
	.badges {
		display: flex;
		gap: 6px;
	}
	.badge {
		padding: 2px 8px;
		border-radius: 10px;
		font-size: 0.65rem;
		font-weight: 600;
		text-transform: uppercase;
		letter-spacing: 0.3px;
	}
	.badge.active {
		background: #dcfce7;
		color: #166534;
	}
	.badge.archived {
		background: #f3f4f6;
		color: #6b7280;
	}
	.field {
		display: flex;
		flex-direction: column;
		gap: 2px;
	}
	.field-label {
		font-size: 0.65rem;
		font-weight: 600;
		text-transform: uppercase;
		letter-spacing: 0.3px;
		color: #9ca3af;
	}
	.field-value {
		font-size: 0.85rem;
		color: #374151;
		line-height: 1.5;
		white-space: pre-wrap;
	}
	.field-value.muted {
		color: #9ca3af;
		font-size: 0.75rem;
	}
	.tag-list {
		display: flex;
		flex-wrap: wrap;
		gap: 4px;
	}
	.tag-badge {
		padding: 2px 8px;
		border-radius: 10px;
		font-size: 0.7rem;
		font-weight: 500;
		color: #374151;
	}
	.footer {
		padding-top: 8px;
		border-top: 1px solid #e5e7eb;
		display: flex;
		justify-content: flex-end;
	}
	.btn-edit {
		padding: 6px 16px;
		border-radius: 6px;
		border: 1px solid #d1d5db;
		background: white;
		color: #374151;
		font-size: 0.8rem;
		font-weight: 500;
		cursor: pointer;
		transition: all 0.15s;
	}
	.btn-edit:hover {
		background: #f3f4f6;
		border-color: #9ca3af;
	}
	.edit-container {
		max-height: 60vh;
		overflow-y: auto;
	}
</style>
