import clsx from 'clsx';
import type { Issue } from '../api/types';

interface IssueCardProps {
  dimension: string;
  score: number;
  issues: Issue[];
  suggestions: string[];
}

function getScoreColor(score: number): string {
  if (score >= 80) return 'bg-green-100 text-green-800';
  if (score >= 60) return 'bg-blue-100 text-blue-800';
  if (score >= 40) return 'bg-yellow-100 text-yellow-800';
  return 'bg-red-100 text-red-800';
}

export default function IssueCard({
  dimension,
  score,
  issues,
  suggestions,
}: IssueCardProps) {
  const hasContent = issues.length > 0 || suggestions.length > 0;

  if (!hasContent && score >= 80) {
    return null; // Don't show cards with no issues and high scores
  }

  return (
    <div className="border border-gray-200 rounded-lg p-4">
      <div className="flex items-center justify-between mb-3">
        <h4 className="font-medium text-gray-900">{dimension}</h4>
        <span className={clsx('px-2 py-1 text-sm font-medium rounded', getScoreColor(score))}>
          {score}/100
        </span>
      </div>

      {issues.length > 0 && (
        <div className="mb-3">
          <p className="text-xs font-medium text-gray-500 uppercase mb-2">Issues</p>
          <ul className="space-y-2">
            {issues.map((issue, idx) => (
              <li key={idx} className="text-sm">
                <div className="flex items-start gap-2">
                  <span className="text-red-500 mt-0.5">&#8226;</span>
                  <div className="flex-1">
                    <span className="text-red-700">{issue.message}</span>
                    {issue.line && (
                      <span className="ml-2 text-xs text-gray-500 font-mono">
                        Line {issue.line}{issue.line_end && issue.line_end !== issue.line ? `-${issue.line_end}` : ''}
                      </span>
                    )}
                    {issue.snippet && (
                      <div className="mt-1 px-2 py-1 bg-gray-100 rounded text-xs font-mono text-gray-600 truncate max-w-full">
                        {issue.snippet}
                      </div>
                    )}
                  </div>
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}

      {suggestions.length > 0 && (
        <div>
          <p className="text-xs font-medium text-gray-500 uppercase mb-2">Suggestions</p>
          <ul className="space-y-1">
            {suggestions.map((suggestion, idx) => (
              <li key={idx} className="text-sm text-blue-700 flex items-start gap-2">
                <span className="text-blue-500 mt-0.5">&#10003;</span>
                {suggestion}
              </li>
            ))}
          </ul>
        </div>
      )}

      {!hasContent && (
        <p className="text-sm text-gray-500 italic">No issues found</p>
      )}
    </div>
  );
}
