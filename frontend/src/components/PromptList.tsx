import clsx from 'clsx';
import type { Prompt, HeuristicAnalysis } from '../api/types';

interface PromptListProps {
  prompts: Prompt[];
  analyses: Record<string, HeuristicAnalysis>;
  selectedId: string | null;
  onSelect: (id: string) => void;
  onAnalyze: (id: string) => void;
  isAnalyzing: boolean;
}

function getScoreColor(score: number): string {
  if (score >= 80) return 'text-green-600 bg-green-100';
  if (score >= 60) return 'text-blue-600 bg-blue-100';
  if (score >= 40) return 'text-yellow-600 bg-yellow-100';
  return 'text-red-600 bg-red-100';
}

export default function PromptList({
  prompts,
  analyses,
  selectedId,
  onSelect,
  onAnalyze,
  isAnalyzing,
}: PromptListProps) {
  return (
    <div className="divide-y divide-gray-100">
      {prompts.map((prompt) => {
        const analysis = analyses[prompt.id];
        const isSelected = prompt.id === selectedId;

        return (
          <div
            key={prompt.id}
            onClick={() => onSelect(prompt.id)}
            className={clsx(
              'p-4 cursor-pointer transition-colors',
              isSelected ? 'bg-blue-50' : 'hover:bg-gray-50'
            )}
          >
            <div className="flex items-start justify-between">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span
                    className={clsx(
                      'px-2 py-0.5 text-xs font-medium rounded',
                      prompt.type === 'system' && 'bg-purple-100 text-purple-700',
                      prompt.type === 'user' && 'bg-blue-100 text-blue-700',
                      prompt.type === 'skill' && 'bg-green-100 text-green-700'
                    )}
                  >
                    {prompt.type === 'system' ? 'SYS' : prompt.type === 'skill' ? 'SKILL' : 'USR'}
                  </span>
                  <h3 className="font-medium text-gray-900 truncate">{prompt.name}</h3>
                </div>
                <p className="mt-1 text-sm text-gray-500 line-clamp-2">
                  {prompt.metadata?.description || prompt.content}
                </p>
              </div>

              <div className="ml-4 flex flex-col items-end gap-2">
                {analysis ? (
                  <span
                    className={clsx(
                      'px-2 py-1 text-sm font-semibold rounded',
                      getScoreColor(analysis.overall_score)
                    )}
                  >
                    {analysis.overall_score}
                  </span>
                ) : (
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onAnalyze(prompt.id);
                    }}
                    disabled={isAnalyzing}
                    className="px-2 py-1 text-xs bg-gray-100 text-gray-600 rounded hover:bg-gray-200 disabled:opacity-50"
                  >
                    Analyze
                  </button>
                )}
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
