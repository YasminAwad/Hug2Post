import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface Message {
  id: number;
  content: string;
  isUser: boolean;
  type: "user" | "assistant";
}

interface Props {
  messages: Message[];
}

const MessageArea: React.FC<Props> = ({ messages }) => {
  return (
    <div className="flex-1 p-4 overflow-y-auto space-y-4">
      {messages.map((msg) => (
        <div
          key={msg.id}
          className={`flex ${msg.isUser ? 'justify-end' : 'justify-start'}`}
        >
          <div
            className={`max-w-[70%] p-3 rounded-lg ${
              msg.isUser ? 'bg-violet-500 text-white' : 'bg-gray-200 text-gray-900'
            }`}
          >
            {/* Render Markdown */}
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {msg.content}
            </ReactMarkdown>
          </div>
        </div>
      ))}
    </div>
  );
};

export default MessageArea;
