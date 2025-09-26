import React from "react";

interface InputBarProps {
  currentMessage: string;
  setCurrentMessage: (msg: string) => void;
  onSubmit: (e: React.FormEvent) => void;
}

const InputBar: React.FC<InputBarProps> = ({ currentMessage, setCurrentMessage, onSubmit }) => {
  return (
    <form onSubmit={onSubmit} className="flex items-center border-t border-gray-200 p-3">
      <input
        type="text"
        value={currentMessage}
        onChange={(e) => setCurrentMessage(e.target.value)}
        placeholder="Type your question..."
        className="flex-1 border rounded-lg px-3 py-2 mr-2 focus:outline-none focus:ring-2 focus:ring-violet-400 text-gray-900"
      />
      <button
        type="submit"
        className="px-4 py-2 bg-violet-600 text-white rounded-lg hover:bg-violet-700 transition"
      >
        Send
      </button>
    </form>
  );
};

export default InputBar;
