<script lang="ts">
	let { onFileSelected }: { onFileSelected: (file: File) => void } = $props();

	let isDragging = $state(false);
	let fileInput: HTMLInputElement | undefined = $state();

	function handleDrop(e: DragEvent) {
		e.preventDefault();
		isDragging = false;
		const file = e.dataTransfer?.files[0];
		if (file && file.type === 'application/pdf') {
			onFileSelected(file);
		}
	}

	function handleDragOver(e: DragEvent) {
		e.preventDefault();
		isDragging = true;
	}

	function handleDragLeave() {
		isDragging = false;
	}

	function handleFileInput(e: Event) {
		const input = e.currentTarget as HTMLInputElement;
		const file = input.files?.[0];
		if (file) {
			onFileSelected(file);
		}
	}
</script>

<!-- svelte-ignore a11y_no_static_element_interactions -->
<div
	class="file-loader"
	class:dragging={isDragging}
	ondrop={handleDrop}
	ondragover={handleDragOver}
	ondragleave={handleDragLeave}
>
	<div class="loader-content">
		<div class="icon">PDF</div>
		<p class="title">Drop a PDF here</p>
		<p class="subtitle">or</p>
		<button class="browse-btn" onclick={() => fileInput?.click()}>
			Browse Files
		</button>
		<input
			bind:this={fileInput}
			type="file"
			accept=".pdf,application/pdf"
			onchange={handleFileInput}
			hidden
		/>
	</div>
</div>

<style>
	.file-loader {
		display: flex;
		align-items: center;
		justify-content: center;
		height: calc(100vh - 80px);
		border: 2px dashed #d1d5db;
		border-radius: 12px;
		margin: 20px;
		transition: all 0.2s;
		background: #fafafa;
	}
	.file-loader.dragging {
		border-color: #6366f1;
		background: #eef2ff;
	}
	.loader-content {
		text-align: center;
	}
	.icon {
		font-size: 2.5rem;
		font-weight: 700;
		color: #9ca3af;
		margin-bottom: 12px;
		letter-spacing: 2px;
	}
	.title {
		font-size: 1.1rem;
		color: #374151;
		font-weight: 500;
		margin: 0 0 4px;
	}
	.subtitle {
		font-size: 0.85rem;
		color: #9ca3af;
		margin: 0 0 12px;
	}
	.browse-btn {
		padding: 8px 20px;
		border: 1px solid #6366f1;
		border-radius: 8px;
		background: white;
		color: #6366f1;
		font-size: 0.875rem;
		font-weight: 500;
		cursor: pointer;
		transition: all 0.15s;
	}
	.browse-btn:hover {
		background: #6366f1;
		color: white;
	}
</style>
