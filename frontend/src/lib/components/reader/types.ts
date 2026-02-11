import type { Tag } from '$lib/types';

export type DocumentType = 'pdf' | 'website';

export interface DocumentTab {
	id: string;
	type: DocumentType;
	title: string;
	// PDF-specific
	pdfFile?: File | null;
	pdfUrl?: string | null;
	currentPage?: number;
	totalPages?: number;
	scale?: number;
	// Website-specific
	websiteUrl?: string | null;
	// Session entities
	activityId?: number | null;
	activityTag?: Tag | null;
	sourceId?: number | null;
}

export interface SessionCard {
	id: string;
	entityType: string;
	entityId: number;
	title: string;
	x: number;
	y: number;
	fromTabId?: string;
}

export interface ReadingSessionState {
	tabs: DocumentTab[];
	activeTabId: string | null;
	cards: SessionCard[];
}
