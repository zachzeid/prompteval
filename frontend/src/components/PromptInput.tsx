import { useState } from 'react';
import clsx from 'clsx';
import type { PromptType } from '../api/types';

interface PromptInputProps {
  onSubmit: (content: string, type: PromptType, name: string) => void;
  isLoading: boolean;
}

export default function PromptInput({ onSubmit, isLoading }: PromptInputProps) {
  const [content, setContent] = useState('');
  const [promptType, setPromptType] = useState<PromptType>('user');
  const [name, setName] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (content.trim()) {
      onSubmit(content.trim(), promptType, name.trim() || 'Inline Prompt');
    }
  };

  const charCount = content.length;
  const wordCount = content.trim() ? content.trim().split(/\s+/).length : 0;
  const lineCount = content.split('\n').length;

  return (
    <form onSubmit={handleSubmit} className="bg-white rounded-lg shadow p-6">
      <h2 className="text-lg font-semibold text-gray-900 mb-4">Evaluate a Prompt</h2>

      <div className="grid grid-cols-2 gap-4 mb-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Prompt Name (optional)
          </label>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="My Prompt"
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Prompt Type
          </label>
          <select
            value={promptType}
            onChange={(e) => setPromptType(e.target.value as PromptType)}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          >
            <option value="user">User Prompt</option>
            <option value="system">System Prompt</option>
            <option value="skill">Skill</option>
          </select>
        </div>
      </div>

      <div className="mb-4">
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Prompt Content
        </label>
        <textarea
          value={content}
          onChange={(e) => setContent(e.target.value)}
          placeholder="Enter your prompt here...

Example:
You are a helpful assistant that helps users write better code.
When reviewing code, focus on:
1. Correctness
2. Performance
3. Readability"
          rows={12}
          className="w-full px-3 py-2 border border-gray-300 rounded-lg font-mono text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 resize-y"
        />
        <div className="flex justify-between mt-1 text-xs text-gray-500">
          <span>{charCount} characters</span>
          <span>{wordCount} words</span>
          <span>{lineCount} lines</span>
        </div>
      </div>

      <div className="flex items-center justify-between">
        <p className="text-sm text-gray-500">
          Paste or type a prompt to analyze its effectiveness
        </p>
        <button
          type="submit"
          disabled={isLoading || !content.trim()}
          className={clsx(
            'px-6 py-2 rounded-lg font-medium transition-colors',
            content.trim()
              ? 'bg-blue-600 text-white hover:bg-blue-700'
              : 'bg-gray-200 text-gray-500 cursor-not-allowed',
            isLoading && 'opacity-50'
          )}
        >
          {isLoading ? 'Analyzing...' : 'Analyze Prompt'}
        </button>
      </div>
    </form>
  );
}
