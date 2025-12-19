import { useState, useCallback, useEffect, useRef } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { parseFile, listPrompts, runHeuristicAnalysis, startLLMAnalysis, getLLMStatus, generateSuggestions, createInlinePrompt } from './api/client';
import type { HeuristicAnalysis, LLMAnalysis, SuggestionResponse } from './api/types';
import FileUpload from './components/FileUpload';
import PromptList from './components/PromptList';
import PromptDetail from './components/PromptDetail';
import PromptInput from './components/PromptInput';
import type { PromptType } from './api/types';

type InputMode = 'file' | 'text';

function App() {
  const [inputMode, setInputMode] = useState<InputMode>('file');
  const [selectedPromptId, setSelectedPromptId] = useState<string | null>(null);
  const [analyses, setAnalyses] = useState<Record<string, HeuristicAnalysis>>({});
  const [llmAnalyses, setLLMAnalyses] = useState<Record<string, LLMAnalysis>>({});
  const [suggestions, setSuggestions] = useState<Record<string, SuggestionResponse>>({});
  const [llmJobId, setLLMJobId] = useState<string | null>(null);
  const pollIntervalRef = useRef<number | null>(null);
  const queryClient = useQueryClient();

  const { data: prompts = [] } = useQuery({
    queryKey: ['prompts'],
    queryFn: listPrompts,
    enabled: true,
  });

  const uploadMutation = useMutation({
    mutationFn: parseFile,
    onSuccess: (data) => {
      queryClient.setQueryData(['prompts'], data.prompts);
      setSelectedPromptId(null);
      setAnalyses({});
      setLLMAnalyses({});
      setSuggestions({});
    },
  });

  const inlinePromptMutation = useMutation({
    mutationFn: async ({ content, type, name }: { content: string; type: PromptType; name: string }) => {
      return createInlinePrompt(content, type, name);
    },
    onSuccess: (prompt) => {
      queryClient.setQueryData(['prompts'], [prompt]);
      setSelectedPromptId(prompt.id);
      setAnalyses({});
      setLLMAnalyses({});
      setSuggestions({});
    },
  });

  const analyzeMutation = useMutation({
    mutationFn: async (promptId: string) => {
      const result = await runHeuristicAnalysis(promptId);
      return { promptId, analysis: result.analysis };
    },
    onSuccess: ({ promptId, analysis }) => {
      setAnalyses((prev) => ({ ...prev, [promptId]: analysis }));
    },
  });

  const handleFileSelect = useCallback(
    (file: File) => {
      uploadMutation.mutate(file);
    },
    [uploadMutation]
  );

  const handleInlinePrompt = useCallback(
    (content: string, type: PromptType, name: string) => {
      inlinePromptMutation.mutate({ content, type, name });
    },
    [inlinePromptMutation]
  );

  const handleAnalyze = useCallback(
    (promptId: string) => {
      analyzeMutation.mutate(promptId);
    },
    [analyzeMutation]
  );

  const handleAnalyzeAll = useCallback(() => {
    prompts.forEach((prompt) => {
      if (!analyses[prompt.id]) {
        analyzeMutation.mutate(prompt.id);
      }
    });
  }, [prompts, analyses, analyzeMutation]);

  // LLM Analysis mutation
  const llmAnalyzeMutation = useMutation({
    mutationFn: async (promptId: string) => {
      const result = await startLLMAnalysis(promptId);
      return { promptId, jobId: result.job_id };
    },
    onSuccess: ({ promptId, jobId }) => {
      setLLMJobId(jobId);
      // Start polling for results
      pollIntervalRef.current = window.setInterval(async () => {
        try {
          const status = await getLLMStatus(jobId);
          if (status.status === 'completed' && status.result) {
            setLLMAnalyses((prev) => ({ ...prev, [promptId]: status.result! }));
            if (pollIntervalRef.current) {
              clearInterval(pollIntervalRef.current);
              pollIntervalRef.current = null;
            }
            setLLMJobId(null);
          } else if (status.status === 'failed') {
            setLLMAnalyses((prev) => ({
              ...prev,
              [promptId]: {
                prompt_id: promptId,
                status: 'failed',
                ambiguities: [],
                missing_context: [],
                injection_risks: [],
                best_practice_issues: [],
                suggested_revision: null,
                revision_explanation: null,
                error: 'Analysis failed',
              },
            }));
            if (pollIntervalRef.current) {
              clearInterval(pollIntervalRef.current);
              pollIntervalRef.current = null;
            }
            setLLMJobId(null);
          }
        } catch {
          // Continue polling
        }
      }, 1000);
    },
  });

  // Generate suggestions mutation
  const suggestionsMutation = useMutation({
    mutationFn: async (promptId: string) => {
      const result = await generateSuggestions(promptId);
      return { promptId, suggestions: result };
    },
    onSuccess: ({ promptId, suggestions: result }) => {
      setSuggestions((prev) => ({ ...prev, [promptId]: result }));
    },
  });

  // Cleanup polling on unmount
  useEffect(() => {
    return () => {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
      }
    };
  }, []);

  const handleLLMAnalyze = useCallback(
    (promptId: string) => {
      llmAnalyzeMutation.mutate(promptId);
    },
    [llmAnalyzeMutation]
  );

  const handleGenerateSuggestions = useCallback(
    (promptId: string) => {
      suggestionsMutation.mutate(promptId);
    },
    [suggestionsMutation]
  );

  const selectedPrompt = prompts.find((p) => p.id === selectedPromptId);
  const selectedAnalysis = selectedPromptId ? analyses[selectedPromptId] : undefined;
  const selectedLLMAnalysis = selectedPromptId ? llmAnalyses[selectedPromptId] : undefined;
  const selectedSuggestions = selectedPromptId ? suggestions[selectedPromptId] : undefined;

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">PromptDesign</h1>
              <p className="text-sm text-gray-500">Evaluate and improve your prompts</p>
            </div>
            {prompts.length > 0 && (
              <button
                onClick={handleAnalyzeAll}
                disabled={analyzeMutation.isPending}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
              >
                {analyzeMutation.isPending ? 'Analyzing...' : 'Analyze All'}
              </button>
            )}
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-6">
        {/* Input Mode Selection */}
        {prompts.length === 0 && (
          <div className="space-y-4">
            {/* Mode Toggle */}
            <div className="flex justify-center gap-2">
              <button
                onClick={() => setInputMode('file')}
                className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                  inputMode === 'file'
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                }`}
              >
                Upload File
              </button>
              <button
                onClick={() => setInputMode('text')}
                className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                  inputMode === 'text'
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                }`}
              >
                Type Prompt
              </button>
            </div>

            {/* File Upload or Text Input */}
            {inputMode === 'file' ? (
              <FileUpload
                onFileSelect={handleFileSelect}
                isLoading={uploadMutation.isPending}
                error={uploadMutation.error?.message}
              />
            ) : (
              <PromptInput
                onSubmit={handleInlinePrompt}
                isLoading={inlinePromptMutation.isPending}
              />
            )}

            {inlinePromptMutation.error && inputMode === 'text' && (
              <div className="p-4 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
                {inlinePromptMutation.error.message}
              </div>
            )}
          </div>
        )}

        {/* Main Content */}
        {prompts.length > 0 && (
          <div className="grid grid-cols-12 gap-6">
            {/* Sidebar - Prompt List */}
            <div className="col-span-4">
              <div className="bg-white rounded-lg shadow">
                <div className="p-4 border-b border-gray-200 flex items-center justify-between">
                  <h2 className="font-semibold text-gray-900">Prompts</h2>
                  <label className="text-sm text-blue-600 hover:text-blue-700 cursor-pointer">
                    Upload New
                    <input
                      type="file"
                      accept=".md"
                      className="hidden"
                      onChange={(e) => {
                        const file = e.target.files?.[0];
                        if (file) handleFileSelect(file);
                      }}
                    />
                  </label>
                </div>
                <PromptList
                  prompts={prompts}
                  analyses={analyses}
                  selectedId={selectedPromptId}
                  onSelect={setSelectedPromptId}
                  onAnalyze={handleAnalyze}
                  isAnalyzing={analyzeMutation.isPending}
                />
              </div>
            </div>

            {/* Main - Prompt Detail */}
            <div className="col-span-8">
              {selectedPrompt ? (
                <PromptDetail
                  prompt={selectedPrompt}
                  analysis={selectedAnalysis}
                  llmAnalysis={selectedLLMAnalysis}
                  suggestions={selectedSuggestions}
                  onAnalyze={() => handleAnalyze(selectedPrompt.id)}
                  onLLMAnalyze={() => handleLLMAnalyze(selectedPrompt.id)}
                  onGenerateSuggestions={() => handleGenerateSuggestions(selectedPrompt.id)}
                  isAnalyzing={analyzeMutation.isPending}
                  isLLMAnalyzing={llmAnalyzeMutation.isPending || llmJobId !== null}
                  isGeneratingSuggestions={suggestionsMutation.isPending}
                />
              ) : (
                <div className="bg-white rounded-lg shadow p-8 text-center text-gray-500">
                  <p>Select a prompt to view details and analysis</p>
                </div>
              )}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

export default App;
