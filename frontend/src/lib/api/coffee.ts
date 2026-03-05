export interface ChatMessage {
	role: 'user' | 'assistant';
	content: string;
}

export interface EntityRef {
	type: string;
	id: number;
	title: string;
}

export interface CurationSuggestion {
	type: string;
	entity_type: string;
	entity_id: number;
	title: string;
	message: string;
	action: string;
}

export type CoffeeEvent =
	| { type: 'entities'; items: EntityRef[] }
	| { type: 'token'; content: string }
	| { type: 'curation'; suggestions: CurationSuggestion[] }
	| { type: 'error'; message: string }
	| { type: 'done' };

export interface OllamaModel {
	name: string;
	size: number;
}

export interface ModelsResponse {
	models: OllamaModel[];
	current: string;
}

export async function fetchModels(): Promise<ModelsResponse> {
	const res = await fetch('/api/coffee/models');
	if (!res.ok) throw new Error(`Failed to fetch models: ${res.status}`);
	return res.json();
}

export async function switchModel(model: string): Promise<{ current: string }> {
	const res = await fetch('/api/coffee/model', {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ model })
	});
	if (!res.ok) throw new Error(`Failed to switch model: ${res.status}`);
	return res.json();
}

export function streamChat(
	message: string,
	history: ChatMessage[],
	onEvent: (event: CoffeeEvent) => void
): AbortController {
	const controller = new AbortController();

	fetch('/api/coffee/chat', {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ message, history }),
		signal: controller.signal
	})
		.then(async (res) => {
			if (!res.ok) {
				const detail = await res.json().catch(() => ({ detail: 'Chat failed' }));
				onEvent({ type: 'error', message: detail.detail || `HTTP ${res.status}` });
				onEvent({ type: 'done' });
				return;
			}

			const reader = res.body!.getReader();
			const decoder = new TextDecoder();
			let buffer = '';

			while (true) {
				const { done, value } = await reader.read();
				if (done) break;

				buffer += decoder.decode(value, { stream: true });
				const lines = buffer.split('\n');
				buffer = lines.pop() ?? '';

				for (const line of lines) {
					const trimmed = line.trim();
					if (trimmed.startsWith('data: ')) {
						try {
							const data = JSON.parse(trimmed.slice(6));
							onEvent(data as CoffeeEvent);
						} catch {
							// skip malformed SSE
						}
					}
				}
			}

			// Process remaining buffer
			if (buffer.trim().startsWith('data: ')) {
				try {
					const data = JSON.parse(buffer.trim().slice(6));
					onEvent(data as CoffeeEvent);
				} catch {
					// skip
				}
			}
		})
		.catch((err) => {
			if (err.name !== 'AbortError') {
				onEvent({ type: 'error', message: err.message });
				onEvent({ type: 'done' });
			}
		});

	return controller;
}

