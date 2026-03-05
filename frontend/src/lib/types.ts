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
	plan_id: number | null;

	source_id: number | null;
	title: string;
	description: string | null;
	duration: number | null;
	position: number;
	header: string | null;
	status: string;
	activity_date: string | null;
	is_active: boolean;
	is_archived: boolean;
	created_at: string;
	updated_at: string;
}

export interface Note {
	id: number;
	title: string;
	content: string | null;
	is_active: boolean;
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
	status: string;
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
	goal: string | null;
	start_date: string | null;
	end_date: string | null;
	status: string;
	is_active: boolean;
	is_archived: boolean;
	created_at: string;
	updated_at: string;
	items: PlanItem[];
	activities: Activity[];
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
	w?: number;
	h?: number;
	collapsed: boolean;
	created_at: string;
	updated_at: string;
}

export interface CategoryStatus {
	id: number;
	category_id: number;
	value: string;
	position: number;
	is_default: boolean;
}

export interface Category {
	id: number;
	slug: string;
	display_name: string;
	member_entity_type: string;
	created_at: string;
	updated_at: string;
	statuses: CategoryStatus[];
}

export interface CollectionItem {
	id: number;
	collection_id: number;
	member_entity_type: string;
	member_entity_id: number;
	position: number;
	status: string | null;
	notes: string | null;
	header: string | null;
	created_at: string;
	updated_at: string;
}

export interface Collection {
	id: number;
	entity_type: string;
	title: string;
	description: string | null;
	category_id: number;
	is_active: boolean;
	is_archived: boolean;
	created_at: string;
	updated_at: string;
	items: CollectionItem[];
}

export interface WorkspaceItem {
	id: number;
	workspace_id: number;
	entity_type: string;
	entity_id: number;
	x: number;
	y: number;
	collapsed: boolean;
	added_at: string;
}

export interface WorkspaceEvent {
	id: number;
	workspace_id: number;
	event_type: string;
	entity_type: string | null;
	entity_id: number | null;
	metadata_json: string | null;
	timestamp: string;
}

export interface Workspace {
	id: number;
	name: string;
	description: string | null;
	is_archived: boolean;
	created_at: string;
	last_opened_at: string;
	items: WorkspaceItem[];
}

export interface WorkspaceDetail extends Workspace {
	events: WorkspaceEvent[];
}

export interface ActiveContext {
	projects: Project[];
	logs: Log[];
	activities: Activity[];
	sources: Source[];
	actors: Actor[];
	plans: Plan[];
	collections: Collection[];
}
