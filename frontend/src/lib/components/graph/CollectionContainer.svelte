<script lang="ts">
	import {
		MINI_CARD_W, MINI_CARD_H, MINI_GAP,
		TITLE_BAR_H, CONTAINER_PADDING, NESTED_INDENT,
		containerWidth, containerHeightNested, buildVisualRows,
		type ContainerMember,
	} from './collectionLayout';
	import EntityIcon from '$lib/components/shared/EntityIcon.svelte';

	const ENTITY_COLORS: Record<string, string> = {
		project: '#5c7a99',
		log: '#8b7355',
		note: '#6b8e6b',
		activity: '#b5838d',
		source: '#c9a227',
		actor: '#8b4557',
		plan: '#6b8ba3',
		collection: '#7c6f9e'
	};

	let {
		collectionId,
		title,
		x,
		y,
		color = '#7c6f9e',
		collapsed = false,
		selected = false,
		highlighted = false,
		pulsing = false,
		archived = false,
		members = [],
		statusCycle = [],
		highlightedMemberKey = null,
		onPointerDown,
		onDblClick,
		onMemberDblClick,
		onMemberPointerDown,
		onStatusChange,
		onToggleCollapse,
		onNestedToggleCollapse,
		onContextMenu,
	}: {
		collectionId: number;
		title: string;
		x: number;
		y: number;
		color?: string;
		collapsed?: boolean;
		selected?: boolean;
		highlighted?: boolean;
		pulsing?: boolean;
		archived?: boolean;
		members?: ContainerMember[];
		statusCycle?: string[];
		highlightedMemberKey?: string | null;
		onPointerDown: (e: PointerEvent) => void;
		onDblClick?: () => void;
		onMemberDblClick: (type: string, id: number) => void;
		onMemberPointerDown?: (type: string, id: number, e: PointerEvent) => void;
		onStatusChange?: (itemId: number, newStatus: string) => void;
		onToggleCollapse: () => void;
		onNestedToggleCollapse?: (collectionId: number) => void;
		onContextMenu?: (e: MouseEvent) => void;
	} = $props();

	function cycleStatus(member: ContainerMember, cycle: string[]) {
		if (!member.itemId || !onStatusChange || cycle.length === 0) return;
		const idx = cycle.indexOf(member.status ?? '');
		const next = cycle[(idx + 1) % cycle.length];
		onStatusChange(member.itemId, next);
	}

	let displayTitle = $derived(
		title.length > 26 ? title.slice(0, 24) + '\u2026' : title
	);

	let w = $derived(containerWidth());
	let h = $derived(containerHeightNested(members, collapsed));

	let visualRows = $derived(buildVisualRows(members));

	function rowX(row: { indent: number }): number {
		return CONTAINER_PADDING + row.indent * NESTED_INDENT;
	}

	function rowY(index: number): number {
		return CONTAINER_PADDING + index * (MINI_CARD_H + MINI_GAP);
	}

	function rowW(row: { indent: number }): number {
		return MINI_CARD_W - row.indent * NESTED_INDENT;
	}

	function miniDisplayTitle(t: string): string {
		return t.length > 28 ? t.slice(0, 26) + '\u2026' : t;
	}

	function statusClass(status?: string): string {
		if (!status) return '';
		if (status === 'done' || status === 'reviewed') return 'mini-status-done';
		if (status === 'in_progress' || status === 'reading') return 'mini-status-in-progress';
		if (status === 'on_hold') return 'mini-status-on-hold';
		if (status === 'cancelled') return 'mini-status-cancelled';
		return 'mini-status-default';
	}

	function isNestedCollection(member: ContainerMember): boolean {
		return member.entityType === 'collection' && !!member.nestedMembers;
	}
</script>

<!-- svelte-ignore a11y_no_static_element_interactions -->
<div
	class="collection-container"
	class:selected
	class:highlighted
	class:pulsing
	class:archived
	style:left="{x}px"
	style:top="{y}px"
	style:width="{w}px"
	style:height="{h}px"
	onpointerdown={onPointerDown}
	oncontextmenu={onContextMenu}
>
	<!-- Title bar -->
	<!-- svelte-ignore a11y_no_static_element_interactions -->
	<div class="container-title-bar" ondblclick={(e) => { e.stopPropagation(); onDblClick?.(); }}>
		<EntityIcon type="collection" size={12} />
		<span class="type-label">Collection</span>
		<span class="container-title">{displayTitle}</span>
		{#if archived}<span class="archived-badge">archived</span>{/if}
		<button
			class="collapse-toggle"
			class:is-collapsed={collapsed}
			onpointerdown={(e) => e.stopPropagation()}
			onclick={(e) => { e.stopPropagation(); onToggleCollapse(); }}
			title={collapsed ? 'Expand container' : 'Collapse container'}
		>
			&#9656;
		</button>
	</div>

	<!-- Member grid (flat list with visual rows) -->
	{#if !collapsed && visualRows.length > 0}
		<div class="member-grid">
			{#each visualRows as row, i (`${row.member.entityType}:${row.member.entityId}:${row.indent}`)}
				{@const member = row.member}
				<!-- svelte-ignore a11y_no_static_element_interactions -->
				<div
					class="mini-card"
					class:has-status={!!member.status}
					class:member-highlighted={highlightedMemberKey === `${member.entityType}:${member.entityId}`}
					class:sub-member={row.isSubMember}
					style:left="{rowX(row)}px"
					style:top="{rowY(i)}px"
					style:width="{rowW(row)}px"
					style:height="{MINI_CARD_H}px"
					ondblclick={(e) => { e.stopPropagation(); onMemberDblClick(member.entityType, member.entityId); }}
					onpointerdown={(e) => { e.stopPropagation(); onMemberPointerDown?.(member.entityType, member.entityId, e); }}
				>
					<div class="mini-color-strip" style:background={ENTITY_COLORS[member.entityType] ?? '#888'}></div>
					<EntityIcon type={member.entityType} size={10} />
					<span class="mini-title">{miniDisplayTitle(member.title)}</span>
					{#if member.status}
						{@const cycle = row.isSubMember && row.parentCollectionId
							? (members.find(m => m.entityId === row.parentCollectionId)?.nestedStatusCycle ?? statusCycle)
							: statusCycle}
						<button
							class="mini-status {statusClass(member.status)}"
							class:clickable={!!member.itemId && !!onStatusChange && cycle.length > 0}
							onclick={(e) => { e.stopPropagation(); cycleStatus(member, cycle); }}
							onpointerdown={(e) => e.stopPropagation()}
							ondblclick={(e) => e.stopPropagation()}
						>{member.status.replace('_', ' ')}</button>
					{/if}
					{#if isNestedCollection(member)}
						<button
							class="nested-expand-toggle"
							class:is-expanded={member.nestedExpanded}
							onpointerdown={(e) => e.stopPropagation()}
							onclick={(e) => { e.stopPropagation(); onNestedToggleCollapse?.(member.entityId); }}
							title={member.nestedExpanded ? 'Collapse' : 'Expand'}
						>&#9656;</button>
					{/if}
				</div>
			{/each}
		</div>
	{/if}
</div>

<style>
	.collection-container {
		position: absolute;
		border: 2px dashed #7c6f9e;
		border-radius: 10px;
		background: rgba(124, 111, 158, 0.06);
		cursor: grab;
		user-select: none;
		touch-action: none;
		transition: box-shadow 0.15s;
		overflow: visible;
	}
	.collection-container:active {
		cursor: grabbing;
	}
	.collection-container.archived {
		opacity: 0.55;
		background: rgba(124, 111, 158, 0.03);
	}
	.collection-container.selected {
		box-shadow: 0 0 0 2px #3b82f6, 0 0 12px rgba(59, 130, 246, 0.3);
		background: rgba(59, 130, 246, 0.05);
	}
	.collection-container.highlighted {
		box-shadow: 0 0 0 2px #7c6f9e, 0 4px 16px rgba(0, 0, 0, 0.15);
	}
	.collection-container.pulsing {
		animation: container-pulse 0.6s ease-in-out 4;
	}
	@keyframes container-pulse {
		0%, 100% { box-shadow: 0 0 0 2px #3b82f6, 0 0 0 rgba(59,130,246,0); }
		50% { box-shadow: 0 0 0 3px #3b82f6, 0 0 16px 4px rgba(59,130,246,0.4); }
	}

	.container-title-bar {
		display: flex;
		align-items: center;
		gap: 5px;
		padding: 6px 10px;
		border-bottom: 1px solid rgba(124, 111, 158, 0.15);
		position: relative;
	}
	.type-label {
		font-size: 0.55rem;
		color: #9ca3af;
		text-transform: uppercase;
		letter-spacing: 0.3px;
		font-weight: 600;
		flex-shrink: 0;
	}
	.container-title {
		font-size: 0.75rem;
		color: #1f2937;
		font-weight: 600;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
		flex: 1;
		min-width: 0;
	}
	.archived-badge {
		font-size: 0.5rem;
		padding: 1px 4px;
		background: #fef2f2;
		color: #b91c1c;
		border: 1px solid #fecaca;
		border-radius: 3px;
		text-transform: uppercase;
		letter-spacing: 0.3px;
		font-weight: 600;
		flex-shrink: 0;
	}
	.collapse-toggle {
		width: 16px;
		height: 16px;
		border-radius: 50%;
		border: 1px solid #d1d5db;
		background: white;
		font-size: 0.55rem;
		cursor: pointer;
		display: flex;
		align-items: center;
		justify-content: center;
		color: #9ca3af;
		transition: transform 0.15s, background 0.15s;
		padding: 0;
		line-height: 1;
		flex-shrink: 0;
	}
	.collapse-toggle:hover {
		background: #f3f4f6;
	}
	.collapse-toggle.is-collapsed {
		transform: rotate(180deg);
	}

	.member-grid {
		position: relative;
	}

	.mini-card {
		position: absolute;
		border-radius: 4px;
		background: white;
		box-shadow: 0 1px 4px rgba(0, 0, 0, 0.08);
		display: flex;
		align-items: center;
		gap: 4px;
		padding: 0 6px 0 0;
		cursor: pointer;
		transition: box-shadow 0.1s;
		overflow: hidden;
	}
	.mini-card:hover {
		box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
	}
	.mini-card.sub-member {
		background: #faf8ff;
		border-left: 2px solid rgba(124, 111, 158, 0.3);
	}
	.mini-card.member-highlighted {
		box-shadow: 0 0 0 2px #3b82f6, 0 2px 8px rgba(59, 130, 246, 0.3);
		background: #eff6ff;
	}
	.mini-color-strip {
		width: 3px;
		height: 100%;
		flex-shrink: 0;
		border-radius: 4px 0 0 4px;
	}
	.mini-title {
		font-size: 0.65rem;
		color: #374151;
		font-weight: 500;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
		flex: 1;
		min-width: 0;
	}

	.nested-expand-toggle {
		width: 14px;
		height: 14px;
		border-radius: 3px;
		border: 1px solid #d1d5db;
		background: white;
		font-size: 0.5rem;
		cursor: pointer;
		display: flex;
		align-items: center;
		justify-content: center;
		color: #9ca3af;
		transition: transform 0.15s, background 0.15s;
		padding: 0;
		line-height: 1;
		flex-shrink: 0;
	}
	.nested-expand-toggle:hover {
		background: #f3f4f6;
		color: #6b7280;
	}
	.nested-expand-toggle.is-expanded {
		transform: rotate(90deg);
	}

	.mini-status {
		font-size: 0.45rem;
		padding: 1px 3px;
		border-radius: 2px;
		font-weight: 600;
		flex-shrink: 0;
		background: #f3f4f6;
		color: #9ca3af;
		border: none;
		cursor: default;
		line-height: 1.2;
	}
	.mini-status.clickable {
		cursor: pointer;
	}
	.mini-status.clickable:hover {
		filter: brightness(0.9);
		outline: 1px solid currentColor;
		outline-offset: 1px;
	}
	.mini-status-done { background: #dcfce7; color: #16a34a; }
	.mini-status-in-progress { background: #fef3c7; color: #d97706; }
	.mini-status-on-hold { background: #fef9c3; color: #a16207; }
	.mini-status-cancelled { background: #fee2e2; color: #dc2626; }
	.mini-status-default { background: #f3f4f6; color: #9ca3af; }
</style>
