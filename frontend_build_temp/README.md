# AI File Organizer - Frontend v2

> Beautiful, ADHD-friendly web interface for the AI File Organizer

![Status](https://img.shields.io/badge/status-week%201%20complete-success)
![React](https://img.shields.io/badge/React-19.1-blue)
![TypeScript](https://img.shields.io/badge/TypeScript-5.9-blue)
![Vite](https://img.shields.io/badge/Vite-7.1-purple)

## 🎯 Mission

Transform 70+ CLI tools into one unified, beautiful web application that User (who has ADHD) can actually use without cognitive overload.

## 🚀 Quick Start

```bash
# Install dependencies (first time only)
npm install

# Start dev server
npm run dev

# Open http://localhost:5173
```

## ✨ Features (Week 1)

### Dashboard
- Real-time system status (Google Drive, disk space, services)
- Quick action buttons for common tasks
- Learning statistics and metrics
- Recent activity feed with undo buttons
- Auto-refresh every 10-30 seconds

### Organize Page
- Drag & drop file upload
- AI classification with confidence scores
- Visual confidence indicators
- Confirm/Reclassify/Skip actions
- 4-level confidence mode (NEVER/MINIMAL/SMART/ALWAYS)
- ADHD-friendly: large buttons, immediate feedback, forgiving UX

### Design System
- **Liquid Glass Aesthetic** - Frosted glass cards with backdrop blur
- **Dark Theme** - Calm, professional #0A0E1A background
- **Smooth Animations** - 200-500ms transitions (respects reduced motion)
- **Custom Scrollbars** - Subtle and minimal
- **Accessible** - Keyboard nav, focus indicators, WCAG AA contrast

## 📁 Project Structure

```
frontend_v2/
├── src/
│   ├── components/
│   │   ├── layout/           # Layout, Sidebar, Header
│   │   ├── dashboard/        # Dashboard components
│   │   └── organize/         # File upload & classification
│   ├── pages/                # Route pages
│   │   ├── Dashboard.tsx
│   │   ├── Organize.tsx
│   │   ├── Search.tsx
│   │   ├── VeoStudio.tsx
│   │   ├── Analysis.tsx
│   │   ├── RollbackCenter.tsx
│   │   └── Settings.tsx
│   ├── services/
│   │   ├── api.ts            # Real API client (ready for backend)
│   │   └── mockApi.ts        # Mock data for development
│   ├── types/                # TypeScript types
│   ├── lib/                  # Utilities
│   ├── App.tsx               # Router setup
│   ├── main.tsx              # Entry point
│   └── index.css             # Global styles
├── tailwind.config.js        # Design tokens
├── package.json
└── README.md
```

## 🛠️ Tech Stack

| Technology | Version | Purpose |
|-----------|---------|---------|
| React | 19.1 | UI framework |
| TypeScript | 5.9 | Type safety |
| Vite | 7.1 | Build tool |
| React Router | 6.x | Routing |
| TanStack Query | 5.x | Data fetching |
| Tailwind CSS | 3.4 | Styling |
| Framer Motion | Latest | Animations |
| Sonner | Latest | Toasts |
| React Dropzone | Latest | File upload |
| date-fns | Latest | Date formatting |
| Lucide React | Latest | Icons |

## 🎨 Design Philosophy

### ADHD-Friendly Principles

1. **Large, Clear Buttons** - All interactive elements are 48px+ tall
2. **Binary Choices** - Confirm/Skip, not complex multi-option forms
3. **Immediate Feedback** - Toast notifications for every action
4. **Visual Confidence Indicators** - Color-coded progress bars
5. **Forgiving Interactions** - Undo buttons everywhere
6. **Reduced Motion Support** - Respects user accessibility preferences
7. **Calm Color Palette** - Minimalist dark theme, no harsh colors
8. **Clear Visual Hierarchy** - Important information stands out
9. **Loading States** - Clear indication when AI is thinking
10. **No Context Switching** - Everything in one beautiful interface

### Liquid Glass Aesthetic

```css
/* Glass Card Example */
.glass-card {
  background: rgba(255, 255, 255, 0.07);
  backdrop-filter: blur(16px);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 16px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.37);
}
```

## 📝 Available Scripts

```bash
# Development
npm run dev          # Start dev server (http://localhost:5173)

# Production
npm run build        # Build for production
npm run preview      # Preview production build

# Linting
npm run lint         # Run ESLint
```

## 🔌 API Integration

The app currently uses **mock data** from `src/services/mockApi.ts` for development. To connect to the real backend:

1. Make sure FastAPI backend is running on `http://localhost:8000`
2. Update `src/services/api.ts` with real endpoint implementations
3. Replace `mockApi` imports with `api` imports in components

### Required Backend Endpoints

| Endpoint | Method | Purpose |
|---------|--------|---------|
| `/api/system/status` | GET | System health and Google Drive status |
| `/api/learning/stats` | GET | Learning statistics |
| `/api/organize/upload` | POST | Upload and classify file |
| `/api/rollback/operations` | GET | Recent file operations |
| `/api/rollback/undo/:id` | POST | Undo specific operation |
| `/api/settings/confidence` | GET/POST | Confidence mode settings |

## 🚨 Troubleshooting

### Dev server won't start
```bash
rm -rf node_modules
npm install
npm run dev
```

### Port already in use
```bash
lsof -ti:5173 | xargs kill -9
npm run dev
```

### TypeScript errors
```bash
npm run build
# Check output for specific errors
```

### Backend not responding
```bash
# Check if backend is running
curl http://localhost:8000/api/system/status

# Start backend (in separate terminal)
cd ..
source venv/bin/activate
python main.py
```

## 📚 Documentation

- [Week 1 README](./WEEK1_README.md) - Detailed implementation guide
- [Quick Start](./QUICKSTART.md) - Get up and running fast
- [Parent README](../README.md) - Project overview
- [CLAUDE.md](../CLAUDE.md) - System architecture and context

## 🎯 Week 1 Status: COMPLETE ✅

All deliverables met:
- ✅ Beautiful liquid glass UI
- ✅ Dashboard with real-time updates
- ✅ File upload and classification
- ✅ ADHD-friendly UX
- ✅ Toast notifications
- ✅ Confidence mode selector
- ✅ Navigation and routing
- ✅ TypeScript type-safe
- ✅ Production build works

## 🔜 Next Steps (Week 2+)

### Immediate
- [ ] Connect to real backend APIs
- [ ] Add error handling and retries
- [ ] Implement WebSocket for real-time updates

### Future Features
- [ ] Search page (semantic/fast/auto modes)
- [ ] VEO Studio (video prompt generation)
- [ ] Analysis page (pattern visualization)
- [ ] Rollback Center (complete history)
- [ ] Settings page (configuration)

## 🤝 Contributing

1. Read the [Week 1 README](./WEEK1_README.md) for architecture details
2. Make sure dev server runs without errors
3. Test all features before committing
4. Follow TypeScript best practices
5. Keep the ADHD-friendly UX principles

## 📄 License

Part of the AI File Organizer project.

---

**Built with love for User** 🚀
*Making file organization effortless for ADHD minds*
