import { useState } from 'react';
import clsx from 'clsx';
import type { Prompt, HeuristicAnalysis, LLMAnalysis, SuggestionResponse } from '../api/types';
import RadarChart from './RadarChart';
import IssueCard from './IssueCard';

interface PromptDetailProps {
  prompt: Prompt;
  analysis?: HeuristicAnalysis;
  llmAnalysis?: LLMAnalysis;
  suggestions?: SuggestionResponse;
  onAnalyze: () => void;
  onLLMAnalyze: () => void;
  onGenerateSuggestions: () => void;
  isAnalyzing: boolean;
  isLLMAnalyzing: boolean;
  isGeneratingSuggestions: boolean;
}

function getScoreLabel(score: number): { label: string; color: string } {
  if (score >= 80) return { label: 'Excellent', color: 'text-green-600' };
  if (score >= 60) return { label: 'Good', color: 'text-blue-600' };
  if (score >= 40) return { label: 'Fair', color: 'text-yellow-600' };
  return { label: 'Needs Work', color: 'text-red-600' };
}

export default function PromptDetail({
  prompt,
  analysis,
  llmAnalysis,
  suggestions,
  onAnalyze,
  onLLMAnalyze,
  onGenerateSuggestions,
  isAnalyzing,
  isLLMAnalyzing,
  isGeneratingSuggestions,
}: PromptDetailProps) {
  const [showFullContent, setShowFullContent] = useState(false);
  const [showSuggestions, setShowSuggestions] = useState(false);

  const contentPreview = prompt.content.length > 500 && !showFullContent
    ? prompt.content.slice(0, 500) + '...'
    : prompt.content;

  const typeLabel = prompt.type === 'system' ? 'System Prompt'
    : prompt.type === 'skill' ? 'Skill'
    : 'User Prompt';

  return (
    <div className="space-y-6">
      {/* Prompt Content Card */}
      <div className="bg-white rounded-lg shadow">
        <div className="p-4 border-b border-gray-200 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span
              className={clsx(
                'px-2 py-1 text-sm font-medium rounded',
                prompt.type === 'system' && 'bg-purple-100 text-purple-700',
                prompt.type === 'user' && 'bg-blue-100 text-blue-700',
                prompt.type === 'skill' && 'bg-green-100 text-green-700'
              )}
            >
              {typeLabel}
            </span>
            <h2 className="text-lg font-semibold text-gray-900">{prompt.name}</h2>
          </div>
          <span className="text-sm text-gray-500">
            Lines {prompt.line_start}-{prompt.line_end}
          </span>
        </div>

        {/* Metadata for skill prompts */}
        {prompt.metadata && (
          <div className="p-4 bg-gray-50 border-b border-gray-200">
            <div className="grid grid-cols-2 gap-4 text-sm">
              {prompt.metadata.description && (
                <div className="col-span-2">
                  <span className="text-gray-500">Description:</span>
                  <p className="text-gray-700 mt-1">{prompt.metadata.description}</p>
                </div>
              )}
              {prompt.metadata.version && (
                <div>
                  <span className="text-gray-500">Version:</span>
                  <span className="ml-2 text-gray-700">{prompt.metadata.version}</span>
                </div>
              )}
              {prompt.metadata.author && (
                <div>
                  <span className="text-gray-500">Author:</span>
                  <span className="ml-2 text-gray-700">{prompt.metadata.author}</span>
                </div>
              )}
              {prompt.metadata.license && (
                <div>
                  <span className="text-gray-500">License:</span>
                  <span className="ml-2 text-gray-700">{prompt.metadata.license}</span>
                </div>
              )}
              {prompt.metadata.tags.length > 0 && (
                <div className="col-span-2">
                  <span className="text-gray-500">Tags:</span>
                  <div className="flex flex-wrap gap-1 mt-1">
                    {prompt.metadata.tags.map((tag, idx) => (
                      <span key={idx} className="px-2 py-0.5 bg-gray-200 text-gray-700 text-xs rounded">
                        {tag}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        <div className="p-4">
          <div className="bg-gray-50 rounded max-h-96 overflow-y-auto font-mono text-sm">
            <table className="w-full">
              <tbody>
                {contentPreview.replace(/\r\n|\r/g, '\n').split('\n').map((line, idx) => {
                  const lineNum = prompt.line_start + idx;
                  return (
                    <tr key={idx} className="hover:bg-gray-100">
                      <td className="px-2 py-0.5 text-right text-gray-400 select-none border-r border-gray-200 w-12">
                        {lineNum}
                      </td>
                      <td className="px-3 py-0.5 text-gray-700 whitespace-pre break-all">
                        {line || ' '}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          {prompt.content.length > 500 && (
            <button
              onClick={() => setShowFullContent(!showFullContent)}
              className="mt-2 text-sm text-blue-600 hover:text-blue-700"
            >
              {showFullContent ? 'Show less' : 'Show more'}
            </button>
          )}
        </div>
      </div>

      {/* Analysis Section */}
      {!analysis ? (
        <div className="bg-white rounded-lg shadow p-8 text-center">
          <p className="text-gray-500 mb-4">No analysis yet</p>
          <div className="flex gap-3 justify-center">
            <button
              onClick={onAnalyze}
              disabled={isAnalyzing}
              className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
            >
              {isAnalyzing ? 'Analyzing...' : 'Run Heuristic Analysis'}
            </button>
          </div>
        </div>
      ) : (
        <>
          {/* Overall Score */}
          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-lg font-semibold text-gray-900">Overall Score</h3>
                <p className={clsx('text-sm', getScoreLabel(analysis.overall_score).color)}>
                  {getScoreLabel(analysis.overall_score).label}
                </p>
              </div>
              <div
                className={clsx(
                  'text-4xl font-bold',
                  getScoreLabel(analysis.overall_score).color
                )}
              >
                {analysis.overall_score}
                <span className="text-lg text-gray-400">/100</span>
              </div>
            </div>
          </div>

          {/* Radar Chart */}
          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Dimension Scores</h3>
            <RadarChart analysis={analysis} />
          </div>

          {/* Issues */}
          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Issues & Suggestions</h3>
            <div className="space-y-4">
              <IssueCard
                dimension="Clarity"
                score={analysis.clarity.score}
                issues={analysis.clarity.issues}
                suggestions={analysis.clarity.suggestions}
              />
              <IssueCard
                dimension="Specificity"
                score={analysis.specificity.score}
                issues={analysis.specificity.issues}
                suggestions={analysis.specificity.suggestions}
              />
              <IssueCard
                dimension="Structure"
                score={analysis.structure.score}
                issues={analysis.structure.issues}
                suggestions={analysis.structure.suggestions}
              />
              <IssueCard
                dimension="Completeness"
                score={analysis.completeness.score}
                issues={analysis.completeness.issues}
                suggestions={analysis.completeness.suggestions}
              />
              <IssueCard
                dimension="Output Format"
                score={analysis.output_format.score}
                issues={analysis.output_format.issues}
                suggestions={analysis.output_format.suggestions}
              />
              <IssueCard
                dimension="Guardrails"
                score={analysis.guardrails.score}
                issues={analysis.guardrails.issues}
                suggestions={analysis.guardrails.suggestions}
              />
            </div>
          </div>

          {/* LLM Analysis Section */}
          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-gray-900">LLM Deep Analysis</h3>
              <div className="flex gap-2">
                <button
                  onClick={onLLMAnalyze}
                  disabled={isLLMAnalyzing}
                  className="px-4 py-2 bg-purple-600 text-white text-sm rounded-lg hover:bg-purple-700 disabled:opacity-50"
                >
                  {isLLMAnalyzing ? 'Analyzing...' : llmAnalysis ? 'Re-analyze' : 'Run LLM Analysis'}
                </button>
                <button
                  onClick={onGenerateSuggestions}
                  disabled={isGeneratingSuggestions}
                  className="px-4 py-2 bg-green-600 text-white text-sm rounded-lg hover:bg-green-700 disabled:opacity-50"
                >
                  {isGeneratingSuggestions ? 'Generating...' : 'Get Suggestions'}
                </button>
              </div>
            </div>

            {llmAnalysis?.error && (
              <div className="p-4 bg-red-50 border border-red-200 rounded-lg mb-4">
                <p className="text-red-700 text-sm">{llmAnalysis.error}</p>
              </div>
            )}

            {llmAnalysis && !llmAnalysis.error && (
              <div className="space-y-4">
                {llmAnalysis.ambiguities.length > 0 && (
                  <div>
                    <h4 className="font-medium text-gray-800 mb-2">Ambiguities</h4>
                    <ul className="space-y-1">
                      {llmAnalysis.ambiguities.map((item, idx) => (
                        <li key={idx} className="text-sm text-gray-600 flex items-start gap-2">
                          <span className="text-yellow-500">&#9888;</span>
                          {item}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {llmAnalysis.missing_context.length > 0 && (
                  <div>
                    <h4 className="font-medium text-gray-800 mb-2">Missing Context</h4>
                    <ul className="space-y-1">
                      {llmAnalysis.missing_context.map((item, idx) => (
                        <li key={idx} className="text-sm text-gray-600 flex items-start gap-2">
                          <span className="text-blue-500">&#8226;</span>
                          {item}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {llmAnalysis.injection_risks.length > 0 && (
                  <div>
                    <h4 className="font-medium text-gray-800 mb-2">Injection Risks</h4>
                    <ul className="space-y-1">
                      {llmAnalysis.injection_risks.map((item, idx) => (
                        <li key={idx} className="text-sm text-red-600 flex items-start gap-2">
                          <span className="text-red-500">&#9888;</span>
                          {item}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {llmAnalysis.best_practice_issues.length > 0 && (
                  <div>
                    <h4 className="font-medium text-gray-800 mb-2">Best Practice Issues</h4>
                    <ul className="space-y-1">
                      {llmAnalysis.best_practice_issues.map((item, idx) => (
                        <li key={idx} className="text-sm text-gray-600 flex items-start gap-2">
                          <span className="text-orange-500">&#8226;</span>
                          {item}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {!llmAnalysis.ambiguities.length && !llmAnalysis.missing_context.length &&
                 !llmAnalysis.injection_risks.length && !llmAnalysis.best_practice_issues.length && (
                  <p className="text-sm text-green-600">No issues found by LLM analysis.</p>
                )}
              </div>
            )}

            {!llmAnalysis && !isLLMAnalyzing && (
              <p className="text-sm text-gray-500">
                Run LLM analysis for deep inspection of ambiguities, missing context, and security risks.
              </p>
            )}
          </div>

          {/* Suggestions Panel */}
          {suggestions && (
            <div className="bg-white rounded-lg shadow p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-gray-900">Improvement Suggestions</h3>
                <button
                  onClick={() => setShowSuggestions(!showSuggestions)}
                  className="text-sm text-blue-600 hover:text-blue-700"
                >
                  {showSuggestions ? 'Hide suggested prompt' : 'Show suggested prompt'}
                </button>
              </div>

              <p className="text-gray-700 mb-4">{suggestions.explanation}</p>

              {suggestions.changes.length > 0 && (
                <div className="mb-4">
                  <h4 className="font-medium text-gray-800 mb-2">Changes Made</h4>
                  <div className="space-y-3">
                    {suggestions.changes.map((change, idx) => (
                      <div key={idx} className="p-3 bg-gray-50 rounded-lg text-sm">
                        <div className="flex items-start gap-2 mb-1">
                          <span className="text-red-500 font-mono">-</span>
                          <span className="text-red-700 line-through">{change.original}</span>
                        </div>
                        <div className="flex items-start gap-2 mb-1">
                          <span className="text-green-500 font-mono">+</span>
                          <span className="text-green-700">{change.replacement}</span>
                        </div>
                        <p className="text-gray-500 text-xs mt-1 ml-4">{change.reason}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {showSuggestions && (
                <div className="mt-4">
                  <h4 className="font-medium text-gray-800 mb-2">Suggested Prompt</h4>
                  <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                    <pre className="whitespace-pre-wrap text-sm text-gray-800 font-mono">
                      {suggestions.suggested}
                    </pre>
                  </div>
                  <button
                    onClick={() => navigator.clipboard.writeText(suggestions.suggested)}
                    className="mt-2 text-sm text-blue-600 hover:text-blue-700"
                  >
                    Copy to clipboard
                  </button>
                </div>
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
}
