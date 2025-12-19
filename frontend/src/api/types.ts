export type PromptType = 'system' | 'user' | 'skill';

export interface PromptMetadata {
  name: string | null;
  description: string | null;
  license: string | null;
  version: string | null;
  author: string | null;
  tags: string[];
  extra: Record<string, string>;
}

export interface Prompt {
  id: string;
  name: string;
  type: PromptType;
  content: string;
  line_start: number;
  line_end: number;
  metadata: PromptMetadata | null;
}

export interface ParsedFile {
  filename: string;
  prompts: Prompt[];
}

export interface Issue {
  message: string;
  line: number | null;
  line_end: number | null;
  snippet: string | null;
}

export interface DimensionScore {
  score: number;
  issues: Issue[];
  suggestions: string[];
}

export interface HeuristicAnalysis {
  prompt_id: string;
  overall_score: number;
  clarity: DimensionScore;
  specificity: DimensionScore;
  structure: DimensionScore;
  completeness: DimensionScore;
  output_format: DimensionScore;
  guardrails: DimensionScore;
}

export type LLMAnalysisStatus = 'pending' | 'running' | 'completed' | 'failed';

export interface LLMAnalysis {
  prompt_id: string;
  status: LLMAnalysisStatus;
  ambiguities: string[];
  missing_context: string[];
  injection_risks: string[];
  best_practice_issues: string[];
  suggested_revision: string | null;
  revision_explanation: string | null;
  error: string | null;
}

export interface SuggestionResponse {
  original: string;
  suggested: string;
  explanation: string;
  changes: Array<{
    original: string;
    replacement: string;
    reason: string;
  }>;
}
