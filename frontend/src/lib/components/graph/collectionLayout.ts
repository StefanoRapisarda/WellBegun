// Layout constants for CollectionContainer
export const MINI_CARD_W = 220;
export const MINI_CARD_H = 36;
export const MINI_GAP = 8;
export const COLS = 1;
export const TITLE_BAR_H = 32;
export const CONTAINER_PADDING = 12;
export const NESTED_INDENT = 16;

export function containerWidth(): number {
	return Math.max(180, CONTAINER_PADDING * 2 + COLS * MINI_CARD_W + (COLS - 1) * MINI_GAP);
}

export function containerHeight(memberCount: number, collapsed: boolean): number {
	if (collapsed || memberCount === 0) return TITLE_BAR_H;
	const rows = Math.ceil(memberCount / COLS);
	return TITLE_BAR_H + CONTAINER_PADDING + rows * MINI_CARD_H + (rows - 1) * MINI_GAP + CONTAINER_PADDING;
}

export interface ContainerMember {
	entityType: string;
	entityId: number;
	title: string;
	status?: string;
	itemId?: number;
	nestedMembers?: ContainerMember[];
	nestedExpanded?: boolean;
	nestedStatusCycle?: string[];
}

/**
 * Build a flat list of visual rows from members, expanding nested collections inline.
 * Each row knows its indent level and whether it's a sub-member.
 */
export interface VisualRow {
	member: ContainerMember;
	indent: number;
	isSubMember: boolean;
	parentCollectionId?: number;
}

export function buildVisualRows(members: ContainerMember[]): VisualRow[] {
	const rows: VisualRow[] = [];
	for (const m of members) {
		rows.push({ member: m, indent: 0, isSubMember: false });
		if (m.entityType === 'collection' && m.nestedExpanded && m.nestedMembers) {
			for (const sub of m.nestedMembers) {
				rows.push({ member: sub, indent: 1, isSubMember: true, parentCollectionId: m.entityId });
			}
		}
	}
	return rows;
}

/**
 * Container height accounting for expanded nested collections.
 */
export function containerHeightNested(members: ContainerMember[], collapsed: boolean): number {
	if (collapsed || members.length === 0) return TITLE_BAR_H;
	const rows = buildVisualRows(members);
	return TITLE_BAR_H + CONTAINER_PADDING + rows.length * MINI_CARD_H + (rows.length - 1) * MINI_GAP + CONTAINER_PADDING;
}
