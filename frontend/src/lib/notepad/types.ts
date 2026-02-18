export type NotepadEntityType = 'note' | 'project' | 'log' | 'activity' | 'source' | 'actor' | 'reading_list' | 'plan';

export interface ParsedEntity {
	type: NotepadEntityType;
	fields: Record<string, string>;
	startLine: number;
	endLine: number;
	dbId?: number;
	items?: Array<{ title: string; is_done: boolean; header?: string | null }>;
	/** Virtual entities are generated from plan items — shown as cards but skipped during save */
	virtual?: boolean;
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
		explicitFields: ['location', 'mood', 'weather', 'day_theme', 'log_type', 'tags'],
		color: '#8b7355'
	},
	activity: {
		primaryField: 'title',
		defaultTextField: 'description',
		defaultTitle: 'Untitled activity',
		explicitFields: ['duration', 'tags'],
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
	reading_list: {
		primaryField: 'title',
		defaultTextField: 'description',
		defaultTitle: 'Untitled reading list',
		explicitFields: ['tags'],
		color: '#5f9ea0'
	},
	plan: {
		primaryField: 'title',
		defaultTextField: 'description',
		defaultTitle: 'Untitled plan',
		explicitFields: ['motivation', 'outcome', 'start_date', 'end_date', 'tags'],
		color: '#6b8ba3'
	}
};

export const VALID_ENTITY_TYPES = Object.keys(ENTITY_CONFIG) as NotepadEntityType[];

export interface StagedConnection {
	sourceIndex: number;
	targetIndex: number;
	predicate: string;
}
