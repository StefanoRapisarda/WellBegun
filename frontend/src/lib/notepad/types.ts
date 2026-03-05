export type NotepadEntityType = 'note' | 'project' | 'log' | 'activity' | 'source' | 'actor' | 'plan' | 'collection';

export interface ParsedEntity {
	type: NotepadEntityType;
	fields: Record<string, string>;
	startLine: number;
	endLine: number;
	dbId?: number;
	items?: Array<{ title: string; is_done: boolean; status?: string; header?: string | null; fields?: Record<string, string>; subSection?: string }>;
	/** Virtual entities are generated from plan items — shown as cards but skipped during save */
	virtual?: boolean;
	/** Index of the parent entity in the entities array (for virtual entities) */
	parentIndex?: number;
	/** Plan sub-section name this virtual entity belongs to (e.g. 'motivation', 'goal') */
	subSection?: string;
	/** True if parsed from a @@ list block */
	fromListBlock?: boolean;
	/** Line index of the @@ header that owns this entity */
	listBlockHeaderLine?: number;
}

export interface EntityConfig {
	primaryField: string;
	defaultTextField: string;
	defaultTitle: string;
	explicitFields: string[];
	color: string;
}

export const ENTITY_CONFIG: Record<NotepadEntityType, EntityConfig> = {
	note: {
		primaryField: 'title',
		defaultTextField: 'content',
		defaultTitle: 'Untitled note',
		explicitFields: ['tags'],
		color: '#6b8e6b'
	},
	project: {
		primaryField: 'title',
		defaultTextField: 'description',
		defaultTitle: 'Untitled project',
		explicitFields: ['status', 'start_date', 'tags'],
		color: '#5c7a99'
	},
	log: {
		primaryField: 'title',
		defaultTextField: 'content',
		defaultTitle: 'Untitled log',
		explicitFields: ['location', 'mood', 'weather', 'day_theme', 'tags'],
		color: '#8b7355'
	},
	activity: {
		primaryField: 'title',
		defaultTextField: 'description',
		defaultTitle: 'Untitled activity',
		explicitFields: ['duration', 'date', 'tags'],
		color: '#b5838d'
	},
	source: {
		primaryField: 'title',
		defaultTextField: 'description',
		defaultTitle: 'Untitled source',
		explicitFields: ['author', 'content_url', 'source_type', 'tags'],
		color: '#c9a227'
	},
	actor: {
		primaryField: 'full_name',
		defaultTextField: 'notes',
		defaultTitle: 'Untitled actor',
		explicitFields: ['role', 'affiliation', 'expertise', 'email', 'url', 'tags'],
		color: '#8b4557'
	},
	plan: {
		primaryField: 'title',
		defaultTextField: 'description',
		defaultTitle: 'Untitled plan',
		explicitFields: ['motivation', 'outcome', 'start_date', 'end_date', 'tags'],
		color: '#6b8ba3'
	},
	collection: {
		primaryField: 'title',
		defaultTextField: 'description',
		defaultTitle: 'default',
		explicitFields: ['category', 'tags'],
		color: '#7c6f9e'
	}
};

export const VALID_ENTITY_TYPES = Object.keys(ENTITY_CONFIG) as NotepadEntityType[];

/**
 * Valid @@sub-section names inside a @plan block.
 * Maps section name → the entity type items should be created as.
 * Role sections (motivation, goal, outcome) create notes linked with that predicate.
 */
export const PLAN_SUB_SECTIONS: Record<string, NotepadEntityType> = {
	activity: 'activity',
	source: 'source',
	note: 'note',
	actor: 'actor',
	motivation: 'note',
	goal: 'note',
	outcome: 'note',
};

export interface StagedConnection {
	sourceIndex: number;
	targetIndex: number;
	predicate: string;
}
