'use client';

import React from 'react';
import { PersistentChat } from '@/components/chat';

/**
 * Chat Demo Page - Test page for the persistent chat system
 * 
 * This page demonstrates the chat functionality and can be used
 * for testing the chat integration with the backend API.
 */
export default function ChatDemoPage() {
  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-3xl font-bold text-gray-900 mb-8">
          Chat System Demo
        </h1>
        
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-8">
          <h2 className="text-xl font-semibold text-gray-800 mb-4">
            Persistent Chat Features
          </h2>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <h3 className="font-medium text-gray-700 mb-2">Chat Features:</h3>
              <ul className="text-sm text-gray-600 space-y-1">
                <li>• Fixed position at bottom-right</li>
                <li>• Expandable/collapsible interface</li>
                <li>• Unread message indicator</li>
                <li>• Smooth animations</li>
                <li>• Message history persistence</li>
                <li>• Real-time API integration</li>
              </ul>
            </div>
            
            <div>
              <h3 className="font-medium text-gray-700 mb-2">How to Test:</h3>
              <ul className="text-sm text-gray-600 space-y-1">
                <li>• Click the chat icon in bottom-right</li>
                <li>• Type a compliance question</li>
                <li>• Press Enter to send</li>
                <li>• Watch for API response</li>
                <li>• Test collapse/expand functionality</li>
                <li>• Check message persistence</li>
              </ul>
            </div>
          </div>
        </div>
        
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <h2 className="text-xl font-semibold text-gray-800 mb-4">
            Sample Questions to Try
          </h2>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="bg-blue-50 p-4 rounded-lg">
              <h4 className="font-medium text-blue-800 mb-2">Trade Compliance:</h4>
              <ul className="text-sm text-blue-700 space-y-1">
                <li>• &quot;What are the HTS requirements for electronics?&quot;</li>
                <li>• &quot;How do I classify textile products?&quot;</li>
                <li>• &quot;What sanctions apply to Russia?&quot;</li>
              </ul>
            </div>
            
            <div className="bg-green-50 p-4 rounded-lg">
              <h4 className="font-medium text-green-800 mb-2">Documentation:</h4>
              <ul className="text-sm text-green-700 space-y-1">
                <li>• &quot;What documents do I need for import?&quot;</li>
                <li>• &quot;How to prepare a commercial invoice?&quot;</li>
                <li>• &quot;What are FDA requirements for food?&quot;</li>
              </ul>
            </div>
          </div>
        </div>
        
        <div className="mt-8 text-center text-sm text-gray-500">
          The chat interface will appear in the bottom-right corner of the screen.
          <br />
          Make sure the backend API is running on localhost:8000 for full functionality.
        </div>
      </div>
      
      {/* The PersistentChat component will render in fixed position */}
      <PersistentChat />
    </div>
  );
}