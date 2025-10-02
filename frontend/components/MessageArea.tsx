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
            <ReactMarkdown 
              remarkPlugins={[remarkGfm]}
              components={{
                p: ({node, ...props}) => <p className="mb-2 last:mb-0" {...props} />,
                ul: ({node, ...props}) => <ul className="list-disc list-inside mb-2 last:mb-0 space-y-1" {...props} />,
                ol: ({node, ...props}) => <ol className="list-decimal list-inside mb-2 last:mb-0 space-y-1" {...props} />,
                li: ({node, ...props}) => <li className="ml-2" {...props} />,
                strong: ({node, ...props}) => <strong className="font-bold" {...props} />,
                em: ({node, ...props}) => <em className="italic" {...props} />,
                h1: ({node, ...props}) => <h1 className="text-2xl font-bold mb-2" {...props} />,
                h2: ({node, ...props}) => <h2 className="text-xl font-bold mb-2" {...props} />,
                h3: ({node, ...props}) => <h3 className="text-lg font-bold mb-2" {...props} />,
                code: ({node, inline, ...props}: any) => 
                  inline ? (
                    <code className={`px-1 py-0.5 rounded text-sm font-mono ${
                      msg.isUser ? 'bg-violet-600' : 'bg-gray-300'
                    }`} {...props} />
                  ) : (
                    <code className={`block p-2 rounded text-sm font-mono my-2 ${
                      msg.isUser ? 'bg-violet-600' : 'bg-gray-300'
                    }`} {...props} />
                  ),
                blockquote: ({node, ...props}) => <blockquote className="border-l-4 border-gray-400 pl-3 italic my-2" {...props} />,
              }}
            >
              {msg.content}
            </ReactMarkdown>
          </div>
        </div>
      ))}
    </div>
  );
};

export default MessageArea;