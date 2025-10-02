import React from "react";

interface InputBarProps {
  currentMessage: string;
  setCurrentMessage: (msg: string) => void;
  onSubmit: (e: React.FormEvent) => void;
  isLoading: boolean;
}

const InputBar: React.FC<InputBarProps> = ({ currentMessage, setCurrentMessage, onSubmit, isLoading }) => {
  return (
    <form onSubmit={onSubmit} className="flex items-center border-t border-gray-200 p-3">
      <input
        type="text"
        value={currentMessage}
        onChange={(e) => setCurrentMessage(e.target.value)}
        placeholder="Type your question..."
        disabled={isLoading}
        className="flex-1 border rounded-lg px-3 py-2 mr-2 focus:outline-none focus:ring-2 focus:ring-violet-400 text-gray-900 disabled:bg-gray-100 disabled:cursor-not-allowed"
      />
      <button
        type="submit"
        disabled={isLoading}
        className="px-4 py-2 bg-violet-600 text-white rounded-lg hover:bg-violet-700 transition disabled:bg-gray-400 disabled:cursor-not-allowed"
      >
        {isLoading ? 'Sending...' : 'Send'}
      </button>
    </form>
  );
};

export default InputBar;