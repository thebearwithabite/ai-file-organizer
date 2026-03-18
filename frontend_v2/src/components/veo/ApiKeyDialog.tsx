import React from 'react';

interface ApiKeyDialogProps {
  onContinue: () => void;
}

const ApiKeyDialog: React.FC<ApiKeyDialogProps> = ({ onContinue }) => {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm">
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 max-w-md w-full shadow-2xl">
        <h2 className="text-xl font-bold text-white mb-4">API Key Required</h2>
        <p className="text-gray-400 mb-6">
          Please verify your API key to continue.
        </p>
        <div className="flex justify-end">
          <button
            onClick={onContinue}
            className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg transition-colors font-medium"
          >
            Continue
          </button>
        </div>
      </div>
    </div>
  );
};

export default ApiKeyDialog;
