# Quick Start Guide

## Frontend Only (Mock Data)

```bash
cd frontend_v2
npm run dev
```

Open **http://localhost:5173** in your browser.

You'll see:
- Dashboard with system status
- Quick action buttons
- File upload interface
- All components working with mock data

## Frontend + Backend (Full Stack)

### Terminal 1: Backend (Python)
```bash
cd /Users/user/Github/ai-file-organizer
source venv/bin/activate  # Activate Python virtual environment
python main.py
```

Backend runs on **http://localhost:8000**

### Terminal 2: Frontend (Node.js)
```bash
cd /Users/user/Github/ai-file-organizer/frontend_v2
npm run dev
```

Frontend runs on **http://localhost:5173**

## What to Test

1. **Dashboard**
   - View system status
   - Click quick action buttons
   - See metrics and recent activity

2. **Organize Page**
   - Drag and drop a file
   - Watch AI analyze it
   - See classification result
   - Try different confidence modes

3. **Navigation**
   - Click sidebar items
   - Navigate between pages
   - Check active states

## Troubleshooting

**Frontend won't start?**
```bash
cd frontend_v2
rm -rf node_modules
npm install
npm run dev
```

**Backend not responding?**
```bash
# Check if backend is running
curl http://localhost:8000/api/system/status
```

**Port already in use?**
```bash
# Kill process on port 5173
lsof -ti:5173 | xargs kill -9
```

## Key Features

- **Liquid Glass Design** - Beautiful frosted glass aesthetic
- **ADHD-Friendly** - Large buttons, clear feedback, forgiving UX
- **Real-time Updates** - Dashboard refreshes automatically
- **Toast Notifications** - Immediate feedback for all actions
- **Drag & Drop** - Intuitive file upload
- **Confidence Modes** - Control how often AI asks for input

Enjoy! 🚀
