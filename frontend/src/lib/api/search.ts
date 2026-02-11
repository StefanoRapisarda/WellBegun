import type { Tag } from '$lib/types';

export interface SearchResult {
	type: string;
	id: number;
	title: string;
	description: string | null;
	created_at: string;
	updated_at: string;
	tags: Tag[];
}

export interface SearchParams {
	q?: string;
	types?: string[];
	start_date?: string;
	end_date?: string;
	tag_ids?: number[];
	tag_mode?: 'or' | 'and';
	limit?: number;
	offset?: number;
}

export async function searchEntities(params: SearchParams): Promise<SearchResult[]> {
	const searchParams = new URLSearchParams();
	if (params.q) searchParams.set('q', params.q);
	if (params.types?.length) searchParams.set('types', params.types.join(','));
	if (params.start_date) searchParams.set('start_date', params.start_date);
	if (params.end_date) searchParams.set('end_date', params.end_date);
	if (params.tag_ids?.length) searchParams.set('tag_ids', params.tag_ids.join(','));
	if (params.tag_mode) searchParams.set('tag_mode', params.tag_mode);
	if (params.limit) searchParams.set('limit', String(params.limit));
	if (params.offset) searchParams.set('offset', String(params.offset));

	const res = await fetch(`/api/search/?${searchParams.toString()}`);
	return res.json();
}
