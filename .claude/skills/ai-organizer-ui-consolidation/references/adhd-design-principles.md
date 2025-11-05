# ADHD-Friendly Design Principles for AI File Organizer

## Core Philosophy

Make finding and organizing files as effortless as having a conversation. Reduce cognitive load through visual hierarchy, immediate feedback, and forgiving interactions.

## The 6 Pillars of ADHD-Friendly UX

### 1. Cognitive Load Reduction

**Problem:** Too many choices create paralysis ("analysis paralysis").

**Solutions:**

- **Binary Questions:** Present "A or B" choices, not A-Z options
  ```jsx
  // Good
  <div>
    <p>Is this about Finn or business?</p>
    <button>Finn</button>
    <button>Business</button>
  </div>

  // Bad
  <select>
    <option>Finn - Entertainment</option>
    <option>Finn - Contracts</option>
    <option>Business - General</option>
    <option>Business - Tax</option>
    <option>Creative - Podcast</option>
    {/* ... 20 more options */}
  </select>
  ```

- **Progressive Disclosure:** Hide advanced options behind "Advanced ▼" expanders
- **Sensible Defaults:** Start with SMART mode (70% confidence), not forcing choice immediately
- **Visual Simplicity:** One primary action per screen

### 2. Immediate Feedback

**Problem:** Uncertainty causes anxiety ("Did that work? Should I click again?").

**Solutions:**

- **Toast Notifications for EVERY Action:**
  ```jsx
  import { toast } from 'sonner'

  const handleUpload = async (file) => {
    toast.loading('Analyzing file...')
    const result = await classifyFile(file)
    toast.success('File organized to Entertainment/Contracts')
  }
  ```

- **Loading States with Progress:**
  ```jsx
  // Good
  <div>Processing 7 of 23 files...</div>
  <ProgressBar value={7} max={23} />

  // Bad
  <div>Loading...</div>  {/* No context */}
  ```

- **Visual Confirmation:**
  - Green checkmark animation on success
  - Bounce/scale animation on button click
  - Color change on hover (not just cursor)

- **No Silent Failures:**
  ```jsx
  // Always show errors with actionable suggestions
  try {
    await organizeFile(file)
  } catch (error) {
    toast.error('Could not organize file', {
      description: 'Check that Google Drive is connected',
      action: {
        label: 'Reconnect Drive',
        onClick: () => navigate('/settings/gdrive')
      }
    })
  }
  ```

### 3. Forgiving Interactions

**Problem:** Fear of making mistakes prevents action.

**Solutions:**

- **Rollback Center Always Visible:**
  - In navigation sidebar (not buried in settings)
  - Show last operation with one-click undo

  ```jsx
  <Sidebar>
    <NavItem to="/">Dashboard</NavItem>
    <NavItem to="/organize">Organize</NavItem>
    <NavItem to="/search">Search</NavItem>
    <NavItem to="/rollback" className="text-yellow-400">
      🔄 Rollback Center
    </NavItem>
  </Sidebar>
  ```

- **Confirmation Only for Destructive Actions:**
  ```jsx
  // No confirmation needed
  <button onClick={() => organizeFile(file)}>
    Organize
  </button>

  // Confirmation required
  <AlertDialog>
    <AlertDialogTrigger>Delete</AlertDialogTrigger>
    <AlertDialogContent>
      <AlertDialogTitle>Permanently delete this file?</AlertDialogTitle>
      <AlertDialogDescription>
        This cannot be undone. Consider moving to Trash instead.
      </AlertDialogDescription>
      <AlertDialogAction>Delete</AlertDialogAction>
      <AlertDialogCancel>Cancel</AlertDialogCancel>
    </AlertDialogContent>
  </AlertDialog>
  ```

- **"Undo" on Every Confirmation Toast:**
  ```jsx
  toast.success('File organized', {
    action: {
      label: 'Undo',
      onClick: () => rollbackOperation(operationId)
    }
  })
  ```

- **Draft/Preview Modes:**
  ```jsx
  // Batch processing shows preview first
  <BatchProcessor>
    <PreviewPanel>
      <div>Will organize 23 files:</div>
      <ul>{files.map(f => <FilePreview file={f} />)}</ul>
    </PreviewPanel>
    <button>Confirm & Organize</button>
  </BatchProcessor>
  ```

### 4. Visual Hierarchy

**Problem:** Can't distinguish important from unimportant.

**Solutions:**

- **Color-Coded Actions:**
  ```css
  /* Primary actions - Blue */
  .btn-primary { background: #0A84FF; }

  /* Success states - Green */
  .btn-success { background: #30D158; }

  /* Destructive actions - Red */
  .btn-destructive { background: #FF453A; }

  /* Warning states - Yellow */
  .btn-warning { background: #FFD60A; color: #000; }

  /* Secondary actions - Ghost/Outline */
  .btn-secondary { background: transparent; border: 1px solid rgba(255,255,255,0.2); }
  ```

- **Size Indicates Importance:**
  ```jsx
  // Most important action
  <button className="px-6 py-3 text-lg">
    Upload Files
  </button>

  // Secondary action
  <button className="px-4 py-2 text-sm">
    Settings
  </button>

  // Tertiary action
  <button className="px-2 py-1 text-xs text-muted">
    Learn More
  </button>
  ```

- **Confidence Scores as Progress Bars:**
  ```jsx
  // Good - Visual, not just numeric
  <div>
    <span>Confidence: 85%</span>
    <ProgressBar value={85} max={100} className="bg-green-500" />
  </div>

  // Bad - Just a number
  <div>Confidence: 0.85</div>
  ```

### 5. Persistent Context

**Problem:** Losing place causes frustration and re-orientation effort.

**Solutions:**

- **Breadcrumbs in Header:**
  ```jsx
  <Header>
    <Breadcrumbs>
      <BreadcrumbItem to="/">Home</BreadcrumbItem>
      <BreadcrumbItem to="/veo">VEO Studio</BreadcrumbItem>
      <BreadcrumbItem>Clip #12345</BreadcrumbItem>
    </Breadcrumbs>
  </Header>
  ```

- **URL Reflects State:**
  ```
  /search?q=finn+contracts&mode=semantic&date_from=2024-01-01

  # User can bookmark, share, or refresh without losing query
  ```

- **Recently Viewed Sidebar:**
  ```jsx
  <Sidebar>
    <div className="text-xs text-muted mt-8">Recently Viewed</div>
    <ul>
      <li>contract_draft.pdf</li>
      <li>Client Name contracts</li>
      <li>VEO: Golden Hour Shot</li>
    </ul>
  </Sidebar>
  ```

- **Auto-Save Form State:**
  ```jsx
  // Use React Hook Form + localStorage
  const { watch } = useForm({
    defaultValues: loadFromLocalStorage('organizeForm')
  })

  useEffect(() => {
    const subscription = watch((value) => {
      saveToLocalStorage('organizeForm', value)
    })
    return () => subscription.unsubscribe()
  }, [watch])
  ```

### 6. Reduced Motion Support

**Problem:** Animations can be distracting or nauseating for some.

**Solution:**

```css
/* Respect user preference */
@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
    scroll-behavior: auto !important;
  }
}
```

```jsx
// In Framer Motion components
<motion.div
  initial={{ opacity: 0 }}
  animate={{ opacity: 1 }}
  transition={{
    duration: 0.3,
    // Automatically respects prefers-reduced-motion
  }}
>
  {content}
</motion.div>
```

## Specific UI Patterns

### File Upload Zone

**ADHD-Friendly Pattern:**

```jsx
<Dropzone onDrop={handleDrop}>
  {({ isDragActive }) => (
    <div className={cn(
      "border-2 border-dashed rounded-2xl p-12 text-center",
      "transition-all duration-300",
      isDragActive ? "border-blue-500 bg-blue-500/10" : "border-white/20"
    )}>
      {isDragActive ? (
        <>
          <div className="text-4xl mb-2">📥</div>
          <p className="text-xl text-blue-400">Drop files here</p>
        </>
      ) : (
        <>
          <div className="text-4xl mb-2">📂</div>
          <p className="text-xl mb-2">Drag & drop files here</p>
          <p className="text-sm text-muted">or</p>
          <button className="mt-4 px-6 py-3 bg-blue-500 rounded-lg">
            Browse Files
          </button>
        </>
      )}
    </div>
  )}
</Dropzone>
```

**Why It Works:**
- Large target area (no precision required)
- Clear visual feedback when dragging
- Two ways to upload (drag or click) - forgiving
- Big, obvious button

### Confidence Mode Selector

**ADHD-Friendly Pattern:**

```jsx
<RadioGroup value={mode} onValueChange={setMode}>
  <div className="space-y-3">
    <RadioCard value="never">
      <div className="flex items-center justify-between">
        <div>
          <div className="font-semibold">🔴 NEVER</div>
          <div className="text-sm text-muted">Fully automatic, no questions</div>
        </div>
        <div className="text-2xl">0%</div>
      </div>
    </RadioCard>

    <RadioCard value="minimal">
      <div className="flex items-center justify-between">
        <div>
          <div className="font-semibold">🟡 MINIMAL</div>
          <div className="text-sm text-muted">Only very uncertain files</div>
        </div>
        <div className="text-2xl">40%</div>
      </div>
    </RadioCard>

    <RadioCard value="smart" defaultChecked>
      <div className="flex items-center justify-between">
        <div>
          <div className="font-semibold">🟢 SMART</div>
          <div className="text-sm text-muted">Balanced (recommended for ADHD)</div>
        </div>
        <div className="text-2xl">70%</div>
      </div>
    </RadioCard>

    <RadioCard value="always">
      <div className="flex items-center justify-between">
        <div>
          <div className="font-semibold">🔵 ALWAYS</div>
          <div className="text-sm text-muted">Review every single file</div>
        </div>
        <div className="text-2xl">100%</div>
      </div>
    </RadioCard>
  </div>
</RadioGroup>
```

**Why It Works:**
- 4 clear options, not a slider (sliders are hard to use precisely)
- Each has an emoji (visual marker), name, description, and percentage
- SMART is pre-selected (good default)
- "Recommended for ADHD" explicitly labels the best choice

### Interactive Question Modal

**ADHD-Friendly Pattern:**

```jsx
<Dialog open={isOpen} onOpenChange={setIsOpen}>
  <DialogContent className="max-w-2xl">
    <DialogHeader>
      <DialogTitle>Help classify this file</DialogTitle>
    </DialogHeader>

    <div className="space-y-4">
      {/* File preview */}
      <div className="bg-white/5 rounded-lg p-4">
        <div className="flex items-center gap-3">
          <div className="text-3xl">📄</div>
          <div>
            <div className="font-semibold">{file.name}</div>
            <div className="text-sm text-muted">{file.size}</div>
          </div>
        </div>
      </div>

      {/* AI reasoning */}
      <div className="bg-blue-500/10 border border-blue-500/30 rounded-lg p-4">
        <div className="text-sm mb-2 text-blue-400">💡 AI Analysis</div>
        <p className="text-sm">{reasoning}</p>
        <div className="mt-2">
          <ProgressBar value={confidence} max={100} />
          <div className="text-xs text-muted mt-1">{confidence}% confident</div>
        </div>
      </div>

      {/* Binary question */}
      <div>
        <p className="mb-3 font-semibold">Is this about Finn or business?</p>
        <div className="grid grid-cols-2 gap-3">
          <button
            onClick={() => handleAnswer('finn')}
            className="p-4 bg-white/10 hover:bg-white/20 rounded-lg text-left"
          >
            <div className="text-2xl mb-1">👤</div>
            <div className="font-semibold">Finn</div>
            <div className="text-sm text-muted">Entertainment/Client work</div>
          </button>

          <button
            onClick={() => handleAnswer('business')}
            className="p-4 bg-white/10 hover:bg-white/20 rounded-lg text-left"
          >
            <div className="text-2xl mb-1">💼</div>
            <div className="font-semibold">Business</div>
            <div className="text-sm text-muted">Company operations</div>
          </button>
        </div>
      </div>

      {/* Option to skip */}
      <button
        onClick={() => handleSkip()}
        className="w-full text-sm text-muted hover:text-white"
      >
        Skip (organize later)
      </button>
    </div>
  </DialogContent>
</Dialog>
```

**Why It Works:**
- Shows file preview (visual context)
- Shows AI reasoning (transparency)
- Binary choice with large click targets
- Each option has emoji, title, and description
- Option to skip if unsure (forgiving)
- Modal blocks other actions (prevents distraction)

## Animation Guidelines

### Duration

```jsx
// Micro-interactions: 150ms
<button className="transition-colors duration-150">
  Click me
</button>

// Component transitions: 300ms
<motion.div
  initial={{ opacity: 0 }}
  animate={{ opacity: 1 }}
  transition={{ duration: 0.3 }}
/>

// Page transitions: 500ms max
<motion.div
  initial={{ opacity: 0, y: 20 }}
  animate={{ opacity: 1, y: 0 }}
  transition={{ duration: 0.5 }}
/>
```

### Easing

```jsx
// Use macOS native easing
transition={{ ease: [0.4, 0, 0.2, 1], duration: 0.3 }}

// Or Tailwind's 'ease-out'
className="transition-all duration-300 ease-out"
```

### When to Animate

**DO animate:**
- Button hover/click states
- Modal open/close
- Toast notifications appearing
- Progress bar filling
- Success checkmarks appearing

**DON'T animate:**
- Text content loading
- Large images fading in (can be slow)
- Repeated actions (gets annoying)

## Testing for ADHD-Friendliness

After building a component, ask:

1. **Can I do this without thinking?**
   - If you need to read instructions → redesign

2. **Is it obvious what will happen when I click?**
   - If unsure → add description or preview

3. **Can I undo it if I'm wrong?**
   - If no → add rollback or confirmation

4. **Does it cause anxiety?**
   - If yes → add progress indicators or reduce stakes

5. **Would I use this when tired/distracted?**
   - If no → simplify further

## Examples of ADHD-Hostile Patterns to Avoid

**❌ Multi-step wizards without progress indicators:**
```jsx
// Bad - Where am I in the process?
<div>
  <h2>Step 3</h2>
  {/* ... */}
</div>
```

**✅ Clear progress with context:**
```jsx
// Good
<div>
  <div className="flex items-center gap-2 mb-4">
    <div className="bg-green-500 w-8 h-8 rounded-full flex items-center justify-center">✓</div>
    <div className="text-muted">Upload</div>
    <div className="flex-1 h-px bg-white/20" />
    <div className="bg-green-500 w-8 h-8 rounded-full flex items-center justify-center">✓</div>
    <div className="text-muted">Classify</div>
    <div className="flex-1 h-px bg-white/20" />
    <div className="bg-blue-500 w-8 h-8 rounded-full flex items-center justify-center">3</div>
    <div>Organize</div>
    <div className="flex-1 h-px bg-white/20" />
    <div className="bg-white/20 w-8 h-8 rounded-full flex items-center justify-center">4</div>
    <div className="text-muted">Confirm</div>
  </div>
  {/* Step 3 content */}
</div>
```

---

**❌ Dropdowns with 20+ options:**
```jsx
// Bad - Overwhelming
<select>
  {categories.map(cat => <option key={cat.id}>{cat.name}</option>)}
</select>
```

**✅ Hierarchical selection or search:**
```jsx
// Good
<Popover>
  <PopoverTrigger>Select category</PopoverTrigger>
  <PopoverContent>
    <input placeholder="Search categories..." />
    <div className="space-y-1">
      <CategoryGroup title="Entertainment">
        <CategoryItem>Contracts</CategoryItem>
        <CategoryItem>Projects</CategoryItem>
      </CategoryGroup>
      <CategoryGroup title="Business">
        <CategoryItem>Tax</CategoryItem>
        <CategoryItem>Invoices</CategoryItem>
      </CategoryGroup>
    </div>
  </PopoverContent>
</Popover>
```

---

**❌ Actions without confirmation or undo:**
```jsx
// Bad - Permanent action, no way back
<button onClick={() => deleteAllFiles()}>
  Clear All
</button>
```

**✅ Confirmation + undo option:**
```jsx
// Good
<AlertDialog>
  <AlertDialogTrigger>Clear All</AlertDialogTrigger>
  <AlertDialogContent>
    <AlertDialogTitle>Clear all files?</AlertDialogTitle>
    <AlertDialogDescription>
      This will move 47 files to the Rollback Center.
      You can undo this action for 30 days.
    </AlertDialogDescription>
    <AlertDialogAction onClick={handleClear}>
      Clear (can undo)
    </AlertDialogAction>
    <AlertDialogCancel>Cancel</AlertDialogCancel>
  </AlertDialogContent>
</AlertDialog>
```

---

## Key Takeaway

**Every design decision should answer: "Does this make life easier for someone with ADHD?"**

If the answer is "maybe" or "I don't know," the design needs more work.

---

*Last Updated: 2025-10-29*
*Reference: Ryan's actual ADHD experience + proven UI patterns*
