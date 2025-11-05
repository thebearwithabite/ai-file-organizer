#!/bin/bash
# AI File Organizer - Frontend Initialization Script
# Initializes Vite + React + TypeScript project with all required dependencies

set -e  # Exit on error

echo "🚀 Initializing AI File Organizer Frontend..."
echo ""

# Check if we're in the right directory
if [ ! -f "package.json" ] || [ ! -f "CLAUDE.md" ]; then
    echo "⚠️  Warning: Run this script from the ai-file-organizer root directory"
    echo "   Current directory: $(pwd)"
    read -p "   Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Create frontend_v2 directory
echo "📁 Creating frontend_v2 directory..."
mkdir -p frontend_v2
cd frontend_v2

# Initialize Vite project
echo "⚡ Initializing Vite + React + TypeScript..."
npm create vite@latest . -- --template react-ts

# Install core dependencies
echo "📦 Installing core dependencies..."
npm install

# Install UI dependencies
echo "🎨 Installing UI dependencies (Tailwind, ShadCN, Framer Motion)..."
npm install -D tailwindcss postcss autoprefixer
npm install @radix-ui/react-slot @radix-ui/react-dialog @radix-ui/react-dropdown-menu @radix-ui/react-toast
npm install class-variance-authority clsx tailwind-merge
npm install framer-motion lucide-react

# Install state management
echo "🧠 Installing state management (TanStack Query, Zustand)..."
npm install @tanstack/react-query @tanstack/react-query-devtools
npm install zustand

# Install routing
echo "🛣️  Installing React Router..."
npm install react-router-dom

# Install form handling
echo "📝 Installing form libraries (React Hook Form, Zod)..."
npm install react-hook-form @hookform/resolvers zod

# Install utilities
echo "🔧 Installing utilities..."
npm install react-dropzone  # File upload
npm install sonner  # Toast notifications
npm install date-fns  # Date utilities
npm install react-window  # Virtualized lists
npm install monaco-editor @monaco-editor/react  # Code editor for VEO JSON
npm install d3  # Data visualization for continuity graph
npm install @types/d3 --save-dev

# Initialize Tailwind
echo "🌈 Initializing Tailwind CSS..."
npx tailwindcss init -p

# Copy config files from skill assets
echo "📋 Copying configuration files..."
SKILL_PATH="../.claude/skills/ai-organizer-ui-consolidation/assets"

if [ -d "$SKILL_PATH" ]; then
    cp "$SKILL_PATH/tailwind.config.ts" ./tailwind.config.ts 2>/dev/null || echo "   ⚠️  tailwind.config.ts not found in skill assets"
    cp "$SKILL_PATH/vite.config.ts" ./vite.config.ts 2>/dev/null || echo "   ⚠️  vite.config.ts not found in skill assets"
    cp "$SKILL_PATH/tsconfig.json" ./tsconfig.json 2>/dev/null || echo "   ⚠️  tsconfig.json not found in skill assets"
else
    echo "   ⚠️  Skill assets directory not found. Using default configurations."
fi

# Create directory structure
echo "📂 Creating project structure..."
mkdir -p src/components/{ui,layout,organize,search,veo,analysis,rollback,settings}
mkdir -p src/hooks
mkdir -p src/lib
mkdir -p src/services
mkdir -p src/types

# Create placeholder files
echo "📄 Creating placeholder files..."

# Create lib/utils.ts for cn() helper
cat > src/lib/utils.ts << 'EOF'
import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}
EOF

# Create basic API client
cat > src/services/api.ts << 'EOF'
/**
 * API Client for AI File Organizer Backend
 * Base URL: http://localhost:8000
 */

const API_BASE = 'http://localhost:8000'

export async function apiRequest<T>(
  endpoint: string,
  options?: RequestInit
): Promise<T> {
  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  })

  if (!response.ok) {
    throw new Error(`API Error: ${response.statusText}`)
  }

  return response.json()
}

export const api = {
  // System
  getSystemStatus: () => apiRequest('/api/system/status'),

  // Organize
  uploadFile: (file: File) => {
    const formData = new FormData()
    formData.append('file', file)
    return apiRequest('/api/organize/upload', {
      method: 'POST',
      body: formData,
      headers: {}, // Let browser set Content-Type for FormData
    })
  },

  // Search
  search: (query: string, mode: string = 'auto') =>
    apiRequest(`/api/search?q=${encodeURIComponent(query)}&mode=${mode}`),

  // Add more endpoints as needed...
}
EOF

# Update package.json scripts
echo "📝 Updating package.json scripts..."
npm pkg set scripts.dev="vite"
npm pkg set scripts.build="tsc && vite build"
npm pkg set scripts.preview="vite preview"
npm pkg set scripts.lint="eslint . --ext ts,tsx --report-unused-disable-directives --max-warnings 0"

echo ""
echo "✅ Frontend initialization complete!"
echo ""
echo "📌 Next steps:"
echo "   1. cd frontend_v2"
echo "   2. Review tailwind.config.ts for liquid glass design tokens"
echo "   3. npm run dev"
echo "   4. Open http://localhost:5173"
echo ""
echo "🎨 Start building with the liquid glass aesthetic!"
echo "   - Use backdrop-blur-xl for frosted glass effect"
echo "   - Use bg-white/[0.07] for translucent backgrounds"
echo "   - See .claude/skills/ai-organizer-ui-consolidation/references/ for design guidelines"
echo ""
