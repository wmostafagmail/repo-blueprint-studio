import React from 'react';
import { marked } from 'marked';

interface MarkdownPreviewProps {
  markdown: string;
}

export const MarkdownPreview: React.FC<MarkdownPreviewProps> = ({ markdown }) => {
  // Parse markdown content synchronously
  const getHtmlContent = () => {
    try {
      return marked.parse(markdown || '');
    } catch (e) {
      return `<p class="text-rose-500">Failed to render Markdown preview: ${String(e)}</p>`;
    }
  };

  return (
    <div className="border border-slate-200 rounded-lg p-6 bg-white shadow-sm mt-6">
      <h3 className="text-base font-bold text-slate-800 mb-4 pb-2 border-b border-slate-100 flex items-center">
        <span>Blueprint Live Preview</span>
      </h3>
      <div 
        className="markdown-body overflow-x-auto"
        dangerouslySetInnerHTML={{ __html: getHtmlContent() as string }}
      />
    </div>
  );
};
