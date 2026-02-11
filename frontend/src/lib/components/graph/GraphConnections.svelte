<script lang="ts">
	import type { KnowledgeTriple, BoardNode } from '$lib/types';
	import { structuralPredicates, semanticRelations, loadPredicates } from '$lib/stores/predicates';
	import { onMount } from 'svelte';

	let {
		triples,
		nodeMap,
		cardWidth = 150,
		cardHeight = 60,
		collapsedNodes,
		editingTripleId = null,
		editingPredicate = '',
		onPredicateDblClick,
		onPredicateChange,
		onPredicateBlur,
		onPredicateKeydown,
		onConnectionSwap,
		onConnectionDelete,
		onPredicateSelect
	}: {
		triples: KnowledgeTriple[];
		nodeMap: Map<string, BoardNode>;
		cardWidth?: number;
		cardHeight?: number;
		collapsedNodes: Set<string>;
		editingTripleId?: number | null;
		editingPredicate?: string;
		onPredicateDblClick: (tripleId: number, currentPredicate: string) => void;
		onPredicateChange: (value: string) => void;
		onPredicateBlur: () => void;
		onPredicateKeydown: (e: KeyboardEvent) => void;
		onConnectionSwap: (tripleId: number) => void;
		onConnectionDelete: (tripleId: number) => void;
		onPredicateSelect?: (tripleId: number, predicate: string) => void;
	} = $props();

	let predicateMenuTripleId = $state<number | null>(null);

	function getSuggestedPredicates(triple: KnowledgeTriple): { label: string; group: string }[] {
		const key1 = `${triple.subject_type}:${triple.object_type}`;
		const key2 = `${triple.object_type}:${triple.subject_type}`;
		const results: { label: string; group: string }[] = [];
		if ($structuralPredicates[key1]) results.push({ label: $structuralPredicates[key1], group: 'Structural' });
		if ($structuralPredicates[key2] && $structuralPredicates[key2] !== $structuralPredicates[key1]) {
			results.push({ label: $structuralPredicates[key2], group: 'Structural' });
		}
		results.push({ label: 'related to', group: 'Structural' });
		for (const [category, predicates] of Object.entries($semanticRelations)) {
			for (const pred of predicates) {
				results.push({ label: pred.forward, group: category });
			}
		}
		return results;
	}

	function handlePredicateMenuSelect(tripleId: number, predicate: string) {
		predicateMenuTripleId = null;
		onPredicateSelect?.(tripleId, predicate);
	}

	function togglePredicateMenu(tripleId: number, e: MouseEvent) {
		e.stopPropagation();
		predicateMenuTripleId = predicateMenuTripleId === tripleId ? null : tripleId;
	}

	onMount(() => { loadPredicates(); });

	function nodeKey(type: string, id: number): string {
		return `${type}:${id}`;
	}

	interface ConnectionData {
		triple: KnowledgeTriple;
		sx: number;
		sy: number;
		tx: number;
		ty: number;
		path: string;
		labelX: number;
		labelY: number;
		angle: number;
	}

	// Clip a point from center (cx,cy) toward a target, stopping at the card edge
	function clipToEdge(cx: number, cy: number, targetX: number, targetY: number, hw: number, hh: number): { x: number; y: number } {
		const dx = targetX - cx;
		const dy = targetY - cy;
		if (dx === 0 && dy === 0) return { x: cx, y: cy };
		// Which edge does the ray hit first?
		const absDx = Math.abs(dx);
		const absDy = Math.abs(dy);
		if (absDx * hh > absDy * hw) {
			// exits left/right
			const sign = dx > 0 ? 1 : -1;
			return { x: cx + sign * hw, y: cy + dy * hw / absDx };
		} else {
			// exits top/bottom
			const sign = dy > 0 ? 1 : -1;
			return { x: cx + dx * hh / absDy, y: cy + sign * hh };
		}
	}

	let connections = $derived.by(() => {
		const result: ConnectionData[] = [];
		if (!Array.isArray(triples)) return result;
		const hw = cardWidth / 2;
		const hh = cardHeight / 2;
		for (const triple of triples) {
			const subjectKey = nodeKey(triple.subject_type, triple.subject_id);
			const objectKey = nodeKey(triple.object_type, triple.object_id);

			// Skip if either node is collapsed
			if (collapsedNodes.has(subjectKey) || collapsedNodes.has(objectKey)) continue;

			const sNode = nodeMap.get(subjectKey);
			const tNode = nodeMap.get(objectKey);
			if (!sNode || !tNode) continue;

			const sCx = sNode.x + hw;
			const sCy = sNode.y + hh;
			const tCx = tNode.x + hw;
			const tCy = tNode.y + hh;

			// Clip to card edges
			const sEdge = clipToEdge(sCx, sCy, tCx, tCy, hw, hh);
			const tEdge = clipToEdge(tCx, tCy, sCx, sCy, hw, hh);

			const sx = sEdge.x;
			const sy = sEdge.y;
			const tx = tEdge.x;
			const ty = tEdge.y;

			const dx = tx - sx;
			const dy = ty - sy;
			const dist = Math.sqrt(dx * dx + dy * dy);
			const offset = Math.min(Math.abs(dx), Math.abs(dy)) * 0.4;

			let cp1x: number, cp1y: number, cp2x: number, cp2y: number;
			if (Math.abs(dx) > Math.abs(dy)) {
				cp1x = sx + dx * 0.3;
				cp1y = sy - offset;
				cp2x = sx + dx * 0.7;
				cp2y = ty + offset;
			} else {
				cp1x = sx - offset;
				cp1y = sy + dy * 0.3;
				cp2x = tx + offset;
				cp2y = sy + dy * 0.7;
			}

			const path = `M ${sx},${sy} C ${cp1x},${cp1y} ${cp2x},${cp2y} ${tx},${ty}`;

			// Bezier midpoint at t=0.5
			const t = 0.5;
			const mt = 1 - t;
			const labelX =
				mt * mt * mt * sx +
				3 * mt * mt * t * cp1x +
				3 * mt * t * t * cp2x +
				t * t * t * tx;
			const labelY =
				mt * mt * mt * sy +
				3 * mt * mt * t * cp1y +
				3 * mt * t * t * cp2y +
				t * t * t * ty;

			const angle = dist > 0 ? (Math.atan2(dy, dx) * 180) / Math.PI : 0;

			result.push({ triple, sx, sy, tx, ty, path, labelX, labelY, angle });
		}
		return result;
	});
</script>

<svg
	class="graph-connections"
	style="position:absolute;top:0;left:0;width:20000px;height:20000px;pointer-events:none;overflow:visible;"
>
	<defs>
		<marker
			id="arrowhead"
			markerWidth="10"
			markerHeight="8"
			refX="9"
			refY="4"
			orient="auto"
			markerUnits="userSpaceOnUse"
		>
			<path d="M 0 0 L 10 4 L 0 8 Z" fill="#94a3b8" />
		</marker>
	</defs>
	{#each connections as conn (conn.triple.id)}
		<!-- Connection line with arrow -->
		<path
			d={conn.path}
			fill="none"
			stroke="#94a3b8"
			stroke-width="1.5"
			stroke-dasharray="8 4"
			marker-end="url(#arrowhead)"
		/>
		<!-- Invisible wider hit area for click-to-swap -->
		<!-- svelte-ignore a11y_click_events_have_key_events -->
		<!-- svelte-ignore a11y_no_static_element_interactions -->
		<path
			d={conn.path}
			fill="none"
			stroke="transparent"
			stroke-width="12"
			class="line-hit-area"
			onclick={() => onConnectionSwap(conn.triple.id)}
		/>

		{#if editingTripleId === conn.triple.id}
			<!-- Inline predicate editor -->
			<foreignObject
				x={conn.labelX - 60}
				y={conn.labelY - 12}
				width="120"
				height="24"
			>
				<input
					type="text"
					class="predicate-input"
					value={editingPredicate}
					oninput={(e) => onPredicateChange((e.target as HTMLInputElement).value)}
					onblur={onPredicateBlur}
					onkeydown={onPredicateKeydown}
					autofocus
				/>
			</foreignObject>
		{:else}
			<!-- Predicate label: double-click to edit text -->
			<!-- svelte-ignore a11y_click_events_have_key_events -->
			<!-- svelte-ignore a11y_no_static_element_interactions -->
			<g
				class="predicate-group"
				transform="translate({conn.labelX},{conn.labelY})"
				ondblclick={() => onPredicateDblClick(conn.triple.id, conn.triple.predicate)}
			>
				<rect
					x={-(conn.triple.predicate.length * 3.5 + 12)}
					y="-10"
					width={conn.triple.predicate.length * 7 + 24}
					height="20"
					rx="4"
					fill="white"
					fill-opacity="0.9"
					stroke="#e5e7eb"
					stroke-width="0.5"
				/>
				<text
					text-anchor="middle"
					dominant-baseline="central"
					class="predicate-text"
				>
					{conn.triple.predicate}
				</text>
				<!-- Dropdown button -->
				<!-- svelte-ignore a11y_click_events_have_key_events -->
				<!-- svelte-ignore a11y_no_static_element_interactions -->
				<text
					x={conn.triple.predicate.length * 3.5 + 6}
					class="dropdown-btn"
					text-anchor="middle"
					dominant-baseline="central"
					onclick={(e: MouseEvent) => togglePredicateMenu(conn.triple.id, e)}
				>
					&#9662;
				</text>
				<!-- Delete button -->
				<!-- svelte-ignore a11y_click_events_have_key_events -->
				<!-- svelte-ignore a11y_no_static_element_interactions -->
				<text
					x={conn.triple.predicate.length * 3.5 + 18}
					class="delete-btn"
					text-anchor="middle"
					dominant-baseline="central"
					onclick={(e: MouseEvent) => { e.stopPropagation(); onConnectionDelete(conn.triple.id); }}
				>
					×
				</text>
			</g>
			{#if predicateMenuTripleId === conn.triple.id}
				{@const preds = getSuggestedPredicates(conn.triple)}
				{@const groups = [...new Set(preds.map(p => p.group))]}
				<foreignObject
					x={conn.labelX - 80}
					y={conn.labelY + 14}
					width="160"
					height="200"
				>
					<div class="pred-dropdown" xmlns="http://www.w3.org/1999/xhtml">
						{#each groups as group}
							<div class="pred-group-label">{group}</div>
							{#each preds.filter(p => p.group === group) as pred}
								<button
									class="pred-option"
									class:active={conn.triple.predicate === pred.label}
									onclick={() => handlePredicateMenuSelect(conn.triple.id, pred.label)}
								>
									{pred.label}
								</button>
							{/each}
						{/each}
					</div>
				</foreignObject>
			{/if}
		{/if}
	{/each}
</svg>

<style>
	.line-hit-area {
		pointer-events: stroke;
		cursor: pointer;
	}
	.predicate-group {
		cursor: pointer;
		pointer-events: all;
	}
	.predicate-text {
		font-size: 11px;
		fill: #64748b;
		font-family: inherit;
	}
	.predicate-group:hover .predicate-text {
		fill: #334155;
	}
	.delete-btn {
		font-size: 14px;
		fill: #cbd5e1;
		cursor: pointer;
		pointer-events: all;
	}
	.delete-btn:hover {
		fill: #ef4444;
	}
	.predicate-input {
		width: 100%;
		height: 100%;
		border: 1px solid #94a3b8;
		border-radius: 4px;
		padding: 2px 6px;
		font-size: 11px;
		text-align: center;
		outline: none;
		background: white;
		box-sizing: border-box;
	}
	.dropdown-btn {
		font-size: 10px;
		fill: #cbd5e1;
		cursor: pointer;
		pointer-events: all;
	}
	.dropdown-btn:hover {
		fill: #3b82f6;
	}
	.pred-dropdown {
		background: white;
		border: 1px solid #e5e7eb;
		border-radius: 6px;
		box-shadow: 0 4px 12px rgba(0,0,0,0.12);
		padding: 4px;
		max-height: 196px;
		overflow-y: auto;
		display: flex;
		flex-wrap: wrap;
		gap: 2px;
		pointer-events: all;
	}
	.pred-group-label {
		width: 100%;
		font-size: 9px;
		font-weight: 600;
		color: #9ca3af;
		text-transform: uppercase;
		letter-spacing: 0.04em;
		padding: 3px 4px 1px;
	}
	.pred-option {
		font-size: 10px;
		padding: 2px 6px;
		border: 1px solid #e5e7eb;
		border-radius: 3px;
		background: #f9fafb;
		cursor: pointer;
		color: #6b7280;
	}
	.pred-option:hover {
		background: #e5e7eb;
		color: #374151;
	}
	.pred-option.active {
		background: #6b7280;
		color: white;
		border-color: #6b7280;
	}
</style>
