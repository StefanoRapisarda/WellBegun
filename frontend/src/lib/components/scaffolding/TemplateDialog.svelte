<script lang="ts">
	let {
		onSave,
		onSkip,
		onClose,
	}: {
		onSave: (data: { name: string; description: string; creator: string; version: string }) => Promise<{ success: boolean; message: string }>;
		onSkip: () => void;
		onClose: () => void;
	} = $props();

	let name = $state('');
	let description = $state('');
	let creator = $state('');
	let version = $state('1.0.0');
	let isSaving = $state(false);
	let error = $state('');

	async function handleSave() {
		if (!name.trim()) {
			error = 'Template name is required';
			return;
		}
		if (!creator.trim()) {
			error = 'Creator name is required';
			return;
		}

		error = '';
		isSaving = true;

		const result = await onSave({ name, description, creator, version });

		isSaving = false;

		if (result.success) {
			onClose();
		} else {
			error = result.message;
		}
	}

	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'Escape') {
			onClose();
		}
	}
</script>

<svelte:window onkeydown={handleKeydown} />

<div class="modal-overlay" onclick={onClose} role="dialog" aria-modal="true">
	<div class="modal-content" onclick={(e) => e.stopPropagation()} role="document">
		<header class="modal-header">
			<div class="header-icon">🎉</div>
			<h2>Project Created Successfully!</h2>
			<p>Would you like to save this structure as a template for future use?</p>
		</header>

		<div class="modal-body">
			<div class="form-group">
				<label>
					<span>Template Name *</span>
					<input
						type="text"
						bind:value={name}
						placeholder="e.g., Python FastAPI Project"
					/>
				</label>
			</div>
			<div class="form-group">
				<label>
					<span>Description</span>
					<textarea
						bind:value={description}
						rows="2"
						placeholder="Brief description of what this template is for..."
					></textarea>
				</label>
			</div>
			<div class="form-row">
				<div class="form-group">
					<label>
						<span>Creator *</span>
						<input
							type="text"
							bind:value={creator}
							placeholder="Your Name"
						/>
					</label>
				</div>
				<div class="form-group">
					<label>
						<span>Version</span>
						<input
							type="text"
							bind:value={version}
							placeholder="1.0.0"
						/>
					</label>
				</div>
			</div>

			{#if error}
				<div class="error-message">{error}</div>
			{/if}
		</div>

		<footer class="modal-footer">
			<button class="btn-skip" onclick={onSkip}>
				Skip
			</button>
			<button class="btn-save" onclick={handleSave} disabled={isSaving}>
				{isSaving ? 'Saving...' : 'Save as Template'}
			</button>
		</footer>
	</div>
</div>

<style>
	.modal-overlay {
		position: fixed;
		inset: 0;
		background: rgba(0, 0, 0, 0.5);
		display: flex;
		align-items: center;
		justify-content: center;
		z-index: 1000;
	}

	.modal-content {
		background: white;
		border-radius: 12px;
		width: 90%;
		max-width: 480px;
		box-shadow: 0 20px 60px rgba(0, 0, 0, 0.2);
	}

	.modal-header {
		text-align: center;
		padding: 24px 24px 16px;
	}
	.header-icon {
		font-size: 3rem;
		margin-bottom: 12px;
	}
	.modal-header h2 {
		margin: 0 0 8px;
		font-size: 1.2rem;
		font-weight: 600;
		color: #065f46;
	}
	.modal-header p {
		margin: 0;
		font-size: 0.9rem;
		color: #6b7280;
	}

	.modal-body {
		padding: 0 24px 16px;
		display: flex;
		flex-direction: column;
		gap: 12px;
	}

	.form-group label {
		display: flex;
		flex-direction: column;
		gap: 4px;
	}
	.form-group label span {
		font-size: 0.8rem;
		font-weight: 500;
		color: #374151;
	}
	.form-group input,
	.form-group textarea {
		padding: 10px 12px;
		border: 1px solid #d1d5db;
		border-radius: 6px;
		font-size: 0.9rem;
	}
	.form-group input:focus,
	.form-group textarea:focus {
		outline: none;
		border-color: #5c7a99;
		box-shadow: 0 0 0 2px rgba(92, 122, 153, 0.1);
	}

	.form-row {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 12px;
	}

	.error-message {
		padding: 10px 12px;
		background: #fef2f2;
		border: 1px solid #fecaca;
		border-radius: 6px;
		color: #dc2626;
		font-size: 0.85rem;
	}

	.modal-footer {
		display: flex;
		justify-content: space-between;
		padding: 16px 24px;
		border-top: 1px solid #e5e7eb;
	}

	.btn-skip {
		padding: 10px 20px;
		border: none;
		border-radius: 6px;
		background: none;
		color: #6b7280;
		font-size: 0.9rem;
		cursor: pointer;
	}
	.btn-skip:hover {
		color: #374151;
		background: #f3f4f6;
	}

	.btn-save {
		padding: 10px 24px;
		border: none;
		border-radius: 6px;
		background: #5c7a99;
		color: white;
		font-size: 0.9rem;
		font-weight: 500;
		cursor: pointer;
		transition: transform 0.15s, box-shadow 0.15s;
	}
	.btn-save:hover:not(:disabled) {
		transform: translateY(-1px);
		box-shadow: 0 4px 12px rgba(92, 122, 153, 0.3);
	}
	.btn-save:disabled {
		opacity: 0.6;
		cursor: not-allowed;
	}
</style>
