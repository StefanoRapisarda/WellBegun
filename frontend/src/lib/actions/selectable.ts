import { panelSelection, pulsingSelection, type EntityType } from '$lib/stores/panelSelection';

interface SelectableParams {
	entityType: EntityType;
	entityId: number;
}

// Inject keyframes once
const KEYFRAMES_ID = 'coffee-pulse-keyframes';
if (typeof document !== 'undefined' && !document.getElementById(KEYFRAMES_ID)) {
	const s = document.createElement('style');
	s.id = KEYFRAMES_ID;
	s.textContent = `@keyframes coffee-pulse {
		0%, 100% { box-shadow: inset 0 0 0 2px #3b82f6; }
		50% { box-shadow: inset 0 0 0 2px #3b82f6, 0 0 16px 4px rgba(59,130,246,0.35); }
	}`;
	document.head.appendChild(s);
}

export function selectable(node: HTMLElement, params: SelectableParams) {
	let { entityType, entityId } = params;

	node.setAttribute('data-selectable', '');

	function handleClick(e: MouseEvent) {
		if (e.detail !== 1) return;

		const target = e.target as HTMLElement;
		if (target.closest('button, input, textarea, a')) return;

		e.stopPropagation();

		if (e.metaKey || e.ctrlKey) {
			panelSelection.toggle(entityType, entityId);
		} else {
			panelSelection.selectOne(entityType, entityId);
		}
	}

	node.addEventListener('click', handleClick);

	const key = `${entityType}:${entityId}`;

	// Track current states for cross-subscription coordination
	let currentSel = false;
	let currentPulse = false;

	const unsubscribe = panelSelection.subscribe(($sel) => {
		currentSel = $sel.has(key);
		if (currentPulse) {
			// Pulsing takes priority; don't clear its styles
			return;
		}
		if (currentSel) {
			node.style.boxShadow = 'inset 0 0 0 2px #d1d5db';
			node.style.borderRadius = '8px';
		} else {
			node.style.boxShadow = '';
			node.style.borderRadius = '';
		}
	});

	const unsubPulse = pulsingSelection.subscribe(($ps) => {
		currentPulse = $ps.has(key);
		if (currentPulse) {
			node.style.animation = 'coffee-pulse 0.6s ease-in-out 4';
			node.style.boxShadow = 'inset 0 0 0 2px #3b82f6';
			node.style.borderRadius = '8px';
		} else if (currentSel) {
			node.style.animation = '';
			node.style.boxShadow = 'inset 0 0 0 2px #d1d5db';
			node.style.borderRadius = '8px';
		} else {
			node.style.animation = '';
			node.style.boxShadow = '';
			node.style.borderRadius = '';
		}
	});

	return {
		update(newParams: SelectableParams) {
			entityType = newParams.entityType;
			entityId = newParams.entityId;
		},
		destroy() {
			node.removeEventListener('click', handleClick);
			unsubscribe();
			unsubPulse();
			node.style.boxShadow = '';
			node.style.borderRadius = '';
			node.style.animation = '';
		}
	};
}
