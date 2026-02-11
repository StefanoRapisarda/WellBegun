<script lang="ts">
	import { dateFilter, setFilterDate, setFilterDays, resetToToday, resetToAll } from '$lib/stores/dateFilter';

	function todayISO(): string {
		return new Date().toISOString().slice(0, 10);
	}

	let isAll = $derived($dateFilter.mode === 'all');
	let isToday = $derived($dateFilter.mode === 'single' && $dateFilter.date === todayISO());
	let isRange = $derived($dateFilter.mode === 'range');

	const presets = [1, 3, 7, 14, 30];
	let dayOptions = $derived(
		presets.includes($dateFilter.days) ? presets : [...presets, $dateFilter.days].sort((a, b) => a - b)
	);
</script>

<div class="date-filter">
	<div class="mode-toggle">
		<button
			class="mode-btn"
			class:active={isAll}
			onclick={resetToAll}
		>
			All
		</button>
		<button
			class="mode-btn"
			class:active={$dateFilter.mode === 'single'}
			onclick={() => setFilterDate($dateFilter.date)}
		>
			Date
		</button>
		<button
			class="mode-btn"
			class:active={isRange}
			onclick={() => setFilterDays($dateFilter.days)}
		>
			Last X days
		</button>
	</div>

	{#if isRange}
		<select
			class="days-select"
			value={$dateFilter.days}
			onchange={(e) => setFilterDays(parseInt((e.target as HTMLSelectElement).value))}
		>
			{#each dayOptions as d}
				<option value={d}>{d} day{d > 1 ? 's' : ''}</option>
			{/each}
		</select>
	{:else if $dateFilter.mode === 'single'}
		<input
			type="date"
			value={$dateFilter.date}
			oninput={(e) => setFilterDate((e.target as HTMLInputElement).value)}
			class="date-input"
		/>
		{#if !isToday}
			<button class="today-btn" onclick={resetToToday}>Today</button>
		{/if}
	{/if}
</div>

<style>
	.date-filter {
		display: flex;
		align-items: center;
		gap: 6px;
		flex-shrink: 0;
	}
	.mode-toggle {
		display: flex;
		border: 1px solid #d1d5db;
		border-radius: 6px;
		overflow: hidden;
	}
	.mode-btn {
		padding: 3px 8px;
		border: none;
		background: white;
		color: #6b7280;
		font-size: 0.7rem;
		cursor: pointer;
		transition: all 0.15s;
		white-space: nowrap;
	}
	.mode-btn:not(:last-child) {
		border-right: 1px solid #d1d5db;
	}
	.mode-btn.active {
		background: #3b82f6;
		color: white;
	}
	.mode-btn:hover:not(.active) {
		background: #f3f4f6;
	}
	.date-input {
		padding: 3px 6px;
		border: 1px solid #d1d5db;
		border-radius: 6px;
		font-size: 0.7rem;
		background: white;
		color: #111827;
	}
	.days-select {
		padding: 3px 6px;
		border: 1px solid #d1d5db;
		border-radius: 6px;
		font-size: 0.7rem;
		background: white;
		color: #111827;
		cursor: pointer;
	}
	.today-btn {
		padding: 3px 8px;
		border: 1px solid #d1d5db;
		border-radius: 6px;
		background: #f0fdf4;
		color: #16a34a;
		font-size: 0.7rem;
		cursor: pointer;
		font-weight: 500;
		transition: all 0.15s;
	}
	.today-btn:hover {
		background: #dcfce7;
	}
</style>
