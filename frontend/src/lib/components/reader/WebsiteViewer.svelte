<script lang="ts">
	let {
		url
	}: {
		url: string;
	} = $props();

	let proxyUrl = $derived(`/api/proxy?url=${encodeURIComponent(url)}`);
</script>

<div class="website-viewer">
	<div class="url-bar">
		<span class="url-icon">&#127760;</span>
		<span class="url-text">{url}</span>
	</div>
	<iframe
		src={proxyUrl}
		class="website-frame"
		sandbox="allow-scripts allow-same-origin allow-popups allow-forms"
		title="Website viewer"
	></iframe>
</div>

<style>
	.website-viewer {
		display: flex;
		flex-direction: column;
		height: 100%;
	}
	.url-bar {
		display: flex;
		align-items: center;
		gap: 8px;
		padding: 6px 12px;
		background: #f3f4f6;
		border-bottom: 1px solid #e5e7eb;
		flex-shrink: 0;
	}
	.url-icon {
		font-size: 0.8rem;
	}
	.url-text {
		font-size: 0.75rem;
		color: #6b7280;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
	.website-frame {
		flex: 1;
		border: none;
		width: 100%;
		background: white;
	}
</style>
