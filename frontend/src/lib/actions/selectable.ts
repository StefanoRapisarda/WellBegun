import { panelSelection, type EntityType } from '$lib/stores/panelSelection';

interface SelectableParams {
	entityType: EntityType;
	entityId: number;
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

	const unsubscribe = panelSelection.subscribe(($sel) => {
		if ($sel.has(key)) {
			node.style.boxShadow = 'inset 0 0 0 2px #d1d5db';
			node.style.borderRadius = '8px';
		} else {
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
			node.style.boxShadow = '';
			node.style.borderRadius = '';
		}
	};
}
