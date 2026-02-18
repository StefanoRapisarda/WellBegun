export interface Tag {
	id: number;
	name: string;
	category: string;
	full_tag: string;
	description: string | null;
	color: string | null;
	entity_type: string | null;
	entity_id: number | null;
	is_system: boolean;
	created_at: string;
}

export interface EntityTag {
	id: number;
	tag_id: number;
	target_type: string;
	target_id: number;
	created_at: string;
}

export interface Project {
	id: number;
	title: string;
	description: string | null;
	status: string;
	is_active: boolean;
	is_archived: boolean;
	start_date: string | null;
	created_at: string;
	updated_at: string;
}

export interface Log {
	id: number;
	log_type: string;
	title: string;
	content: string | null;
	location: string | null;
	mood: string | null;
	weather: string | null;
	day_theme: string | null;
	is_active: boolean;
	is_archived: boolean;
	created_at: string;
	updated_at: string;
}

export interface Activity {
	id: number;
	log_id: number | null;
	title: string;
	description: string | null;
	duration: number | null;
	status: string;
	is_active: boolean;
	is_archived: boolean;
	created_at: string;
	updated_at: string;
}

export interface Note {
	id: number;
	title: string;
	content: string | null;
	is_archived: boolean;
	created_at: string;
	updated_at: string;
}

export interface Source {
	id: number;
	title: string;
	description: string | null;
	author: string | null;
	content_url: string | null;
	source_type: string | null;
	is_active: boolean;
	is_archived: boolean;
	created_at: string;
	updated_at: string;
}

export interface Actor {
	id: number;
	full_name: string;
	role: string | null;
	affiliation: string | null;
	expertise: string | null;
	notes: string | null;
	email: string | null;
	url: string | null;
	is_active: boolean;
	is_archived: boolean;
	created_at: string;
	updated_at: string;
}

export interface ReadingListItem {
	id: number;
	reading_list_id: number;
	source_id: number;
	position: number;
	status: string;
	notes: string | null;
	created_at: string;
	updated_at: string;
}

export interface ReadingList {
	id: number;
	title: string;
	description: string | null;
	is_active: boolean;
	created_at: string;
	updated_at: string;
	items: ReadingListItem[];
}


export interface PlanItem {
	id: number;
	plan_id: number;
	activity_id: number;
	position: number;
	is_done: boolean;
	notes: string | null;
	header: string | null;
	created_at: string;
	updated_at: string;
}

export interface Plan {
	id: number;
	title: string;
	description: string | null;
	motivation: string | null;
	outcome: string | null;
	start_date: string | null;
	end_date: string | null;
	is_active: boolean;
	is_archived: boolean;
	created_at: string;
	updated_at: string;
	items: PlanItem[];
}

/**
 * Returns a display prefix for a tag's category.
 * Entity-linked tags (with entity_id) show category as-is (e.g. "project").
 * Standalone/wild tags show "wd-{category}" or just "tag" for the wild category.
 */
export function tagCategoryPrefix(tag: Tag): string {
	if (tag.entity_id !== null && tag.entity_id !== undefined) {
		return tag.category;
	}
	if (tag.category === 'wild') {
		return 'tag';
	}
	return `wd-${tag.category}`;
}

export interface CustomPredicate {
	id: number;
	forward: string;
	reverse: string | null;
	category: string;
	created_at: string;
}

export interface KnowledgeTriple {
	id: number;
	subject_type: string;
	subject_id: number;
	predicate: string;
	object_type: string;
	object_id: number;
	created_at: string;
}

export interface BoardNode {
	id: number;
	entity_type: string;
	entity_id: number;
	x: number;
	y: number;
	collapsed: boolean;
	created_at: string;
	updated_at: string;
}

export interface ActiveContext {
	projects: Project[];
	logs: Log[];
	activities: Activity[];
	sources: Source[];
	actors: Actor[];
	reading_lists: ReadingList[];
	plans: Plan[];
}
