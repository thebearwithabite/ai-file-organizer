import React from 'react';
import { Loader2 } from 'lucide-react';

const LoadingSpinner: React.FC = () => {
  return (
    <div className="flex flex-col items-center justify-center min-h-[50vh] w-full">
      <Loader2 className="w-10 h-10 text-indigo-500 animate-spin" />
      <p className="mt-4 text-gray-500 font-medium animate-pulse">Loading...</p>
    </div>
  );
};

export default LoadingSpinner;
