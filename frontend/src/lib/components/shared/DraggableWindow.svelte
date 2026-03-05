<script lang="ts">
	import type { Snippet } from 'svelte';
	import { onMount } from 'svelte';

	let { title, onClose, children, accentColor = '#6b7280' }: {
		title: string;
		onClose: () => void;
		children: Snippet;
		accentColor?: string;
	} = $props();

	let x = $state(0);
	let y = $state(0);
	let dragging = $state(false);
	let offsetX = 0;
	let offsetY = 0;

	onMount(() => {
		x = Math.round((window.innerWidth - 500) / 2);
		y = Math.round(window.innerHeight * 0.1);
	});

	function handlePointerDown(e: PointerEvent) {
		dragging = true;
		offsetX = e.clientX - x;
		offsetY = e.clientY - y;
		(e.target as HTMLElement).setPointerCapture(e.pointerId);
	}

	function handlePointerMove(e: PointerEvent) {
		if (!dragging) return;
		x = e.clientX - offsetX;
		y = e.clientY - offsetY;
	}

	function handlePointerUp() {
		dragging = false;
	}

	function handleBackdropClick(e: MouseEvent) {
		if (e.target === e.currentTarget) onClose();
	}
</script>

<!-- svelte-ignore a11y_no_static_element_interactions -->
<div class="backdrop" onclick={handleBackdropClick}>
	<div class="window" style:left="{x}px" style:top="{y}px">
		<!-- svelte-ignore a11y_no_static_element_interactions -->
		<div
			class="title-bar"
			style:border-color={accentColor}
			onpointerdown={handlePointerDown}
			onpointermove={handlePointerMove}
			onpointerup={handlePointerUp}
		>
			<span class="title-text">{title}</span>
			<button class="btn-close" onclick={onClose} title="Close">&times;</button>
		</div>
		<div class="window-body">
			{@render children()}
		</div>
	</div>
</div>

<style>
	.backdrop {
		position: fixed;
		inset: 0;
		background: rgba(0, 0, 0, 0.15);
		z-index: 1000;
	}
	.window {
		position: fixed;
		width: 500px;
		max-width: 95vw;
		max-height: 80vh;
		display: flex;
		flex-direction: column;
		background: white;
		border-radius: 10px;
		box-shadow: 0 8px 30px rgba(0, 0, 0, 0.18);
		overflow: hidden;
	}
	.title-bar {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 10px 14px;
		border-bottom: 2px solid #6b7280;
		cursor: grab;
		user-select: none;
		background: #fafafa;
	}
	.title-bar:active {
		cursor: grabbing;
	}
	.title-text {
		font-size: 0.8rem;
		font-weight: 600;
		color: #1f2937;
	}
	.btn-close {
		width: 24px;
		height: 24px;
		border-radius: 6px;
		border: none;
		background: transparent;
		color: #9ca3af;
		font-size: 1.1rem;
		cursor: pointer;
		display: flex;
		align-items: center;
		justify-content: center;
		transition: all 0.15s;
	}
	.btn-close:hover {
		background: #f3f4f6;
		color: #374151;
	}
	.window-body {
		flex: 1;
		overflow-y: auto;
		padding: 16px;
	}
</style>
