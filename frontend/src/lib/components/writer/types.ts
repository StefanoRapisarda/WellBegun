export interface OpenDocument {
	id: string;
	title: string;
	content: string;
	filePath: string | null;
	hasChanges: boolean;
	originalContent: string;
}

export interface EditorPane {
	id: string;
	documents: OpenDocument[];
	activeDocId: string | null;
}
