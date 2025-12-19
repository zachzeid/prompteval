import type {
  ParsedFile,
  Prompt,
  HeuristicAnalysis,
  LLMAnalysis,
  SuggestionResponse,
} from './types';

const API_BASE = '/api';

async function fetchJSON<T>(url: string, options?: RequestInit): Promise<T> {
  const response = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(error.detail || `HTTP ${response.status}`);
  }

  return response.json();
}

export async function parseFile(file: File): Promise<ParsedFile> {
  const formData = new FormData();
  formData.append('file', file);

  const response = await fetch(`${API_BASE}/prompts/parse`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(error.detail || `HTTP ${response.status}`);
  }

  return response.json();
}

export async function parseText(content: string, filename?: string): Promise<ParsedFile> {
  return fetchJSON(`${API_BASE}/prompts/parse/text`, {
    method: 'POST',
    body: JSON.stringify({ content, filename }),
  });
}

export async function createInlinePrompt(
  content: string,
  type: string = 'user',
  name: string = 'Inline Prompt'
): Promise<Prompt> {
  return fetchJSON(`${API_BASE}/prompts/inline`, {
    method: 'POST',
    body: JSON.stringify({ content, type, name }),
  });
}

export async function listPrompts(): Promise<Prompt[]> {
  return fetchJSON(`${API_BASE}/prompts`);
}

export async function getPrompt(promptId: string): Promise<Prompt> {
  return fetchJSON(`${API_BASE}/prompts/${promptId}`);
}

export async function updatePrompt(promptId: string, content: string): Promise<Prompt> {
  return fetchJSON(`${API_BASE}/prompts/${promptId}`, {
    method: 'PUT',
    body: JSON.stringify({ content }),
  });
}

export async function runHeuristicAnalysis(promptId: string): Promise<{ analysis: HeuristicAnalysis }> {
  return fetchJSON(`${API_BASE}/analysis/heuristics`, {
    method: 'POST',
    body: JSON.stringify({ prompt_id: promptId }),
  });
}

export async function getHeuristicAnalysis(promptId: string): Promise<{ analysis: HeuristicAnalysis }> {
  return fetchJSON(`${API_BASE}/analysis/heuristics/${promptId}`);
}

export async function startLLMAnalysis(promptId: string): Promise<{ job_id: string; status: string }> {
  return fetchJSON(`${API_BASE}/analysis/llm`, {
    method: 'POST',
    body: JSON.stringify({ prompt_id: promptId }),
  });
}

export async function getLLMStatus(jobId: string): Promise<{
  job_id: string;
  status: string;
  result: LLMAnalysis | null;
}> {
  return fetchJSON(`${API_BASE}/analysis/llm/${jobId}/status`);
}

export async function generateSuggestions(
  promptId: string,
  focusAreas?: string[]
): Promise<SuggestionResponse> {
  return fetchJSON(`${API_BASE}/analysis/suggestions`, {
    method: 'POST',
    body: JSON.stringify({ prompt_id: promptId, focus_areas: focusAreas || [] }),
  });
}

export async function exportPrompts(
  promptIds?: string[],
  includeAnalysis?: boolean
): Promise<{ markdown: string }> {
  return fetchJSON(`${API_BASE}/prompts/export`, {
    method: 'POST',
    body: JSON.stringify({
      prompt_ids: promptIds || [],
      include_analysis: includeAnalysis || false,
    }),
  });
}
