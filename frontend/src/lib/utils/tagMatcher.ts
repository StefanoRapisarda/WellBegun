import type { Tag } from '$lib/types';

/**
 * Curated keyword patterns organized by tag category.
 * Keys are tag names, values are arrays of keywords/phrases that trigger a match.
 */
const KEYWORD_PATTERNS: Record<string, Record<string, string[]>> = {
	activity: {
		Meeting: ['meeting', 'meet', 'sync', 'standup', 'stand-up', '1:1', 'one-on-one', 'call', 'huddle'],
		Coding: ['coding', 'code', 'develop', 'programming', 'implement', 'debug', 'fix bug'],
		Reading: ['reading', 'read', 'study', 'studying'],
		Writing: ['writing', 'write', 'document', 'documentation', 'draft'],
		Review: ['review', 'feedback', 'pr review', 'code review'],
		Research: ['research', 'investigate', 'explore', 'analysis', 'analyze'],
		Planning: ['planning', 'plan', 'roadmap', 'strategy'],
		Designing: ['designing', 'design', 'wireframe', 'mockup', 'prototype', 'ui', 'ux'],
		ToDo: ['todo', 'to-do', 'to do'],
		InProgress: ['wip', 'working on', 'in progress'],
		Done: ['done', 'completed', 'finished'],
		Blocked: ['blocked', 'stuck', 'waiting'],
	},
	note: {
		Idea: ['idea', 'brainstorm', 'concept', 'inspiration'],
		Quote: ['quote', 'saying', 'citation'],
		Definition: ['definition', 'define', 'meaning', 'glossary'],
		Question: ['question', 'ask', 'inquiry', 'wonder'],
		Feature: ['feature', 'functionality', 'capability'],
		Milestone: ['milestone', 'checkpoint', 'landmark'],
		Goal: ['goal', 'objective', 'target', 'aim'],
		Motivation: ['motivation', 'motivate', 'inspire', 'why'],
		Outcome: ['outcome', 'result', 'conclusion'],
	},
	log: {
		'Daily Log': ['daily', 'day log', 'journal'],
		Progress: ['progress', 'update', 'status update'],
		Decision: ['decision', 'decided', 'chose', 'choice'],
		Issue: ['issue', 'problem', 'bug', 'error'],
		Reflection: ['reflection', 'reflect', 'looking back', 'retrospective'],
		Insight: ['insight', 'realization', 'discovery', 'learned'],
		Workspace: ['workspace', 'setup', 'environment', 'office'],
		Work: ['work', 'job', 'professional', 'career'],
		Travel: ['travel', 'trip', 'journey', 'flight', 'vacation'],
		Health: ['health', 'exercise', 'workout', 'fitness', 'medical'],
	},
	project: {
		Personal: ['personal', 'private', 'hobby', 'home'],
		Work: ['work', 'job', 'professional', 'company', 'business'],
		SideProject: ['side project', 'side-project', 'sideproject', 'hobby project'],
		Experiment: ['experiment', 'test', 'trial', 'poc', 'proof of concept', 'prototype'],
	},
};

/** Strip common English suffixes for rough stemming. */
function stem(word: string): string {
	return word
		.replace(/(?:ing|tion|sion|ment|ness|ity|ous|ive|able|ible|ful|less|ly|ed|er|es|s)$/, '');
}

/** Compute Levenshtein edit distance between two strings. */
function levenshtein(a: string, b: string): number {
	const m = a.length;
	const n = b.length;
	const dp: number[][] = Array.from({ length: m + 1 }, () => Array(n + 1).fill(0));
	for (let i = 0; i <= m; i++) dp[i][0] = i;
	for (let j = 0; j <= n; j++) dp[0][j] = j;
	for (let i = 1; i <= m; i++) {
		for (let j = 1; j <= n; j++) {
			dp[i][j] = a[i - 1] === b[j - 1]
				? dp[i - 1][j - 1]
				: 1 + Math.min(dp[i - 1][j], dp[i][j - 1], dp[i - 1][j - 1]);
		}
	}
	return dp[m][n];
}

/** Split a tag name from camelCase or hyphenated form into lowercase tokens. */
function tokenizeTagName(name: string): string[] {
	return name
		.replace(/([a-z])([A-Z])/g, '$1 $2')
		.replace(/[-_]/g, ' ')
		.toLowerCase()
		.split(/\s+/)
		.filter(Boolean);
}

/** Split a title string into lowercase word tokens. */
function tokenizeTitle(title: string): string[] {
	return title
		.toLowerCase()
		.split(/[\s\-_.,;:!?'"()\[\]{}\/\\]+/)
		.filter(Boolean);
}

/**
 * Match available tags against a title string.
 *
 * Strategy:
 * 1. For tags with curated keyword patterns: substring match against lowered title
 * 2. For tags without patterns (user-created): dynamic word-level matching with
 *    stemming, prefix matching, and Levenshtein distance
 *
 * @returns Array of matched tag names
 */
export function matchTagsToTitle(title: string, availableTags: Tag[], category?: string): string[] {
	if (!title.trim()) return [];

	const lowerTitle = title.toLowerCase();
	const titleTokens = tokenizeTitle(title);
	const titleStems = titleTokens.map(stem);

	const matched: string[] = [];

	// Get curated patterns for this category (if any)
	const categoryPatterns = category ? KEYWORD_PATTERNS[category] : undefined;

	for (const tag of availableTags) {
		const tagName = tag.name;

		// Strategy 1: Check curated keyword patterns
		if (categoryPatterns && tagName in categoryPatterns) {
			const keywords = categoryPatterns[tagName];
			if (keywords.some(kw => lowerTitle.includes(kw))) {
				matched.push(tagName);
			}
			continue;
		}

		// Strategy 2: Dynamic matching for tags without curated patterns
		const tagTokens = tokenizeTagName(tagName);
		let bestScore = 0;

		for (const tagToken of tagTokens) {
			if (tagToken.length < 2) continue;
			const tagStem = stem(tagToken);

			for (let i = 0; i < titleTokens.length; i++) {
				const titleToken = titleTokens[i];
				const titleStem = titleStems[i];

				// Exact stem match
				if (tagStem.length >= 3 && tagStem === titleStem) {
					bestScore = Math.max(bestScore, 0.9);
					continue;
				}

				// Prefix match (one starts with the other, min 4 chars overlap)
				const minLen = Math.min(tagToken.length, titleToken.length);
				if (minLen >= 4) {
					const shorter = tagToken.length <= titleToken.length ? tagToken : titleToken;
					const longer = tagToken.length <= titleToken.length ? titleToken : tagToken;
					if (longer.startsWith(shorter)) {
						bestScore = Math.max(bestScore, 0.7);
						continue;
					}
				}

				// Levenshtein distance for words >= 5 chars
				if (tagToken.length >= 5 && titleToken.length >= 5) {
					const dist = levenshtein(tagToken, titleToken);
					if (dist <= 2) {
						bestScore = Math.max(bestScore, 0.6);
					}
				}
			}
		}

		if (bestScore >= 0.6) {
			matched.push(tagName);
		}
	}

	return matched;
}
