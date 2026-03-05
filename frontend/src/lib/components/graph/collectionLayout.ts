// Layout constants for CollectionContainer
export const MINI_CARD_W = 220;
export const MINI_CARD_H = 36;
export const MINI_GAP = 8;
export const COLS = 1;
export const TITLE_BAR_H = 32;
export const CONTAINER_PADDING = 12;

export function containerWidth(): number {
	return Math.max(180, CONTAINER_PADDING * 2 + COLS * MINI_CARD_W + (COLS - 1) * MINI_GAP);
}

export function containerHeight(memberCount: number, collapsed: boolean): number {
	if (collapsed || memberCount === 0) return TITLE_BAR_H;
	const rows = Math.ceil(memberCount / COLS);
	return TITLE_BAR_H + CONTAINER_PADDING + rows * MINI_CARD_H + (rows - 1) * MINI_GAP + CONTAINER_PADDING;
}
