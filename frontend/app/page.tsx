"use client";

import Header from "@/components/Header";
import InputBar from "@/components/InputBar";
import MessageArea from "@/components/MessageArea";
import React, { useState } from "react";

interface Message {
  id: number;
  content: string;
  isUser: boolean;
  type: "user" | "assistant";
}

const Home = () => {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 1,
      content: "Hi there, how can I help you?",
      isUser: false,
      type: "assistant",
    },
  ]);

  const [currentMessage, setCurrentMessage] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!currentMessage.trim()) return;

    // Add user message
    const userMessageId = messages.length + 1;
    setMessages((prev) => [
      ...prev,
      { id: userMessageId, content: currentMessage, isUser: true, type: "user" },
    ]);

    const userInput = currentMessage;
    setCurrentMessage("");

    try {
      // Send request to FastAPI
      const response = await fetch("http://localhost:8000/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: userInput }),
      });

      const data = await response.json();
      const aiContent = data.response || "Sorry, I couldn't process your request.";

      // Add AI message
      setMessages((prev) => [
        ...prev,
        { id: userMessageId + 1, content: aiContent, isUser: false, type: "assistant" },
      ]);
    } catch (error) {
      console.error(error);
      setMessages((prev) => [
        ...prev,
        { id: messages.length + 1, content: "Error connecting to server.", isUser: false, type: "assistant" },
      ]);
    }
  };

  return (
    <div className="flex justify-center bg-gray-100 min-h-screen py-8 px-4">
      <div className="w-[90%] bg-white flex flex-col rounded-xl shadow-lg border border-gray-100 overflow-hidden h-[90vh]">
        <Header />
        <MessageArea messages={messages} />
        <InputBar
          currentMessage={currentMessage}
          setCurrentMessage={setCurrentMessage}
          onSubmit={handleSubmit}
        />
      </div>
    </div>
  );
};

export default Home;
