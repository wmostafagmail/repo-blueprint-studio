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
    <div className="section-card mt-6">
      <h3 className="mb-4 flex items-center border-b border-white/50 pb-3 text-base font-bold text-slate-900">
        <span>Blueprint Live Preview</span>
      </h3>
      <div 
        className="markdown-body overflow-x-auto"
        dangerouslySetInnerHTML={{ __html: getHtmlContent() as string }}
      />
    </div>
  );
};
