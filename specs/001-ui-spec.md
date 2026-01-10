# UI Specification - Admin Interface & Query Chat

## Overview
A modern React-based admin interface with authentication, entity management, and a ChatGPT-like query interface.

## Tech Stack

### Frontend
- **Framework**: React 19 with TypeScript
- **Build Tool**: Vite (fast, modern bundler)
- **Styling**: TailwindCSS
- **UI Components**: shadcn/ui (Radix UI + Tailwind)
- **Icons**: Lucide React
- **Routing**: React Router v6
- **State Management**: 
  - TanStack Query (React Query) for server state
  - Zustand for client state (auth, UI state)
- **HTTP Client**: Axios with interceptors
- **Form Handling**: React Hook Form + Zod validation

### Authentication
- JWT tokens stored in httpOnly cookies
- Protected routes with automatic redirect
- Token refresh mechanism
- Role-based access control (future enhancement)

## Project Structure

```
ui/
├── public/
│   └── favicon.ico
├── src/
│   ├── components/
│   │   ├── ui/                    # shadcn/ui components
│   │   │   ├── button.tsx
│   │   │   ├── input.tsx
│   │   │   ├── card.tsx
│   │   │   ├── dialog.tsx
│   │   │   ├── dropdown-menu.tsx
│   │   │   ├── table.tsx
│   │   │   ├── scroll-area.tsx
│   │   │   ├── separator.tsx
│   │   │   ├── badge.tsx
│   │   │   └── ...
│   │   ├── layout/
│   │   │   ├── Layout.tsx         # Main layout wrapper
│   │   │   ├── Sidebar.tsx        # Collapsible sidebar
│   │   │   ├── Header.tsx         # Top navigation bar
│   │   │   └── ProtectedRoute.tsx # Auth guard
│   │   ├── auth/
│   │   │   ├── LoginPage.tsx      # Login form
│   │   │   └── AuthProvider.tsx   # Auth context
│   │   ├── tenants/
│   │   │   ├── TenantsList.tsx    # List view with table
│   │   │   ├── TenantForm.tsx     # Create/edit form
│   │   │   └── TenantDetails.tsx  # Detail view
│   │   ├── datasets/
│   │   │   ├── DatasetsList.tsx
│   │   │   ├── DatasetForm.tsx
│   │   │   └── DatasetDetails.tsx
│   │   ├── documents/
│   │   │   ├── DocumentsList.tsx
│   │   │   ├── DocumentUpload.tsx # File upload component
│   │   │   └── DocumentViewer.tsx
│   │   └── query/
│   │       ├── ChatInterface.tsx  # Main chat UI
│   │       ├── ChatMessage.tsx    # Individual message
│   │       ├── ChatInput.tsx      # Message input
│   │       └── ChatHistory.tsx    # Conversation list
│   ├── lib/
│   │   ├── api.ts                 # Axios instance & config
│   │   ├── auth.ts                # Auth utilities
│   │   ├── utils.ts               # Helper functions
│   │   └── constants.ts           # App constants
│   ├── hooks/
│   │   ├── useAuth.ts             # Auth hook
│   │   ├── useTenants.ts          # Tenant queries/mutations
│   │   ├── useDatasets.ts         # Dataset queries/mutations
│   │   ├── useDocuments.ts        # Document queries/mutations
│   │   └── useQuery.ts            # Query/chat hooks
│   ├── stores/
│   │   ├── authStore.ts           # Auth state (Zustand)
│   │   └── uiStore.ts             # UI state (sidebar, theme)
│   ├── types/
│   │   ├── auth.ts
│   │   ├── tenant.ts
│   │   ├── dataset.ts
│   │   ├── document.ts
│   │   └── query.ts
│   ├── App.tsx                    # Root component
│   ├── main.tsx                   # Entry point
│   └── index.css                  # Global styles
├── index.html
├── package.json
├── vite.config.ts
├── tailwind.config.js
├── tsconfig.json
├── components.json                # shadcn/ui config
└── .env.example
```

## Features

### 1. Authentication
- Login page with email/password
- JWT token management (httpOnly cookies)
- Auto-refresh tokens before expiry
- Logout functionality
- Protected routes (redirect to login if not authenticated)
- Current user info display

### 2. Sidebar Navigation
- **Collapsed State**: 
  - Width: ~64px
  - Shows only icons
  - Tooltip on hover
- **Expanded State**: 
  - Width: ~256px
  - Shows icons + labels
- **Menu Items**:
  - Dashboard (Home icon)
  - Query Chat (MessageSquare icon)
  - Tenants (Users icon)
  - Datasets (Database icon)
  - Documents (FileText icon)
  - Settings (Settings icon)
- Toggle button at bottom
- Active route highlighting

### 3. Tenants Management
- **List View**:
  - Table with columns: Name, Created, Status, Actions
  - Search/filter
  - Pagination
  - Create new button
- **Create/Edit**:
  - Modal dialog with form
  - Fields: name, description, etc.
  - Validation
- **Actions**:
  - View details
  - Edit
  - Delete (with confirmation)
  - View associated datasets

### 4. Datasets Management
- **List View**:
  - Tenant selector dropdown (filter by tenant)
  - Table with columns: Name, Tenant, Doc Count, Created, Actions
  - Search/filter
  - Pagination
- **Create/Edit**:
  - Modal dialog
  - Fields: name, description, tenant selection, language
  - Validation
- **Actions**:
  - View details
  - Edit
  - Delete (with confirmation)
  - View documents
  - Rebuild index

### 5. Documents Management
- **List View**:
  - Tenant + Dataset selectors
  - Table with columns: Title, Type, Size, Chunks, Status, Created, Actions
  - Search/filter
  - Pagination
- **Upload**:
  - Drag & drop area
  - Multi-file support
  - Progress indicator
  - File type validation
- **Actions**:
  - View/preview content
  - Download
  - Delete (with confirmation)
  - View chunks
  - Reprocess

### 6. Query Chat Interface (ChatGPT-like)
- **Layout**:
  - Left: Conversation history sidebar (collapsible)
  - Center: Chat messages area
  - Bottom: Input box with send button
- **Features**:
  - Create new chat
  - Load previous chats
  - Streaming responses (SSE/fetch streams)
  - Message formatting (Markdown support)
  - Code syntax highlighting
  - Copy message button
  - Regenerate response
  - Sources/citations display
  - Tenant/Dataset selector for query context
- **Chat History**:
  - List of previous conversations
  - Timestamps
  - Title preview
  - Delete option
  - Search conversations

### 7. Dashboard (Optional)
- Overview statistics:
  - Total tenants
  - Total datasets
  - Total documents
  - Recent activity
- Quick actions
- Recent queries

## Backend Integration

### New Endpoints Required

#### Authentication
```
POST   /v1/auth/login       # Login and get JWT
POST   /v1/auth/logout      # Logout (invalidate token)
GET    /v1/auth/me          # Get current user info
POST   /v1/auth/refresh     # Refresh JWT token
```

#### Query/Chat
```
POST   /v1/query/stream     # Streaming query with SSE
GET    /v1/query/history    # Get chat history
POST   /v1/query/history    # Save chat message
DELETE /v1/query/history/:id # Delete conversation
```

#### Static Files
```
GET    /ui/*                # Serve React app static files
```

### Existing Endpoints (to be used)
```
# Tenants
GET    /v1/tenants
POST   /v1/tenants
GET    /v1/tenants/:id
PUT    /v1/tenants/:id
DELETE /v1/tenants/:id

# Datasets
GET    /v1/datasets?tenant_id=xxx
POST   /v1/datasets
GET    /v1/datasets/:id
PUT    /v1/datasets/:id
DELETE /v1/datasets/:id

# Documents
GET    /v1/documents?dataset_id=xxx
POST   /v1/documents/upload
GET    /v1/documents/:id
DELETE /v1/documents/:id
```

### FastAPI Static File Serving
Mount the built React app in FastAPI:

```python
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# Serve static files
app.mount("/ui/assets", StaticFiles(directory="ui/dist/assets"), name="ui-assets")

# Serve index.html for all /ui/* routes (SPA routing)
@app.get("/ui/{full_path:path}")
async def serve_ui(full_path: str):
    return FileResponse("ui/dist/index.html")
```

## Development Workflow

### Initial Setup
```bash
cd ui
npm install
```

### Development Mode
```bash
# Terminal 1: Run backend
cd /Users/wyp/develop/rag
uvicorn app.main:app --reload --port 7615

# Terminal 2: Run frontend dev server
cd ui
npm run dev  # Runs on port 5173 with proxy to :7615
```

### Production Build
```bash
cd ui
npm run build  # Outputs to ui/dist/

# FastAPI serves from ui/dist/
```

### Vite Config (Proxy to Backend)
```typescript
// vite.config.ts
export default defineConfig({
  server: {
    proxy: {
      '/v1': 'http://localhost:7615',
      '/health': 'http://localhost:7615',
    },
  },
})
```

## Styling Guidelines

### TailwindCSS Theme
- Primary color: Blue (customize)
- Dark mode support (optional)
- Consistent spacing scale
- Typography scale

### Component Patterns
- Use shadcn/ui primitives
- Consistent button styles
- Form field validation states
- Loading states (skeletons, spinners)
- Empty states
- Error states

## Security Considerations

1. **Authentication**:
   - httpOnly cookies for JWT
   - CSRF protection
   - Secure token storage

2. **Authorization**:
   - Validate permissions on backend
   - UI only hides controls, doesn't enforce security

3. **Input Validation**:
   - Client-side: React Hook Form + Zod
   - Server-side: Pydantic models

4. **XSS Prevention**:
   - Sanitize user input
   - Use React's built-in XSS protection

## Performance Optimizations

1. **Code Splitting**: 
   - Route-based lazy loading
   - Component-level code splitting

2. **Caching**:
   - TanStack Query cache
   - Stale-while-revalidate strategy

3. **Virtualization**:
   - Virtual scrolling for large lists
   - Pagination for tables

4. **Bundling**:
   - Vite's optimized bundling
   - Tree-shaking unused code
   - Asset optimization

## Accessibility

- Semantic HTML
- ARIA labels
- Keyboard navigation
- Focus management
- Screen reader support
- Color contrast compliance

## Future Enhancements

1. User management (multi-user support)
2. Role-based access control
3. Activity logs/audit trail
4. Advanced analytics dashboard
5. Export functionality
6. Bulk operations
7. Real-time notifications (WebSocket)
8. Dark mode toggle
9. Multi-language support (i18n)
10. Mobile responsive design

## Dependencies Overview

```json
{
  "dependencies": {
    "react": "^19.0.0",
    "react-dom": "^19.0.0",
    "react-router-dom": "^6.22.0",
    "@tanstack/react-query": "^5.17.0",
    "zustand": "^4.5.0",
    "axios": "^1.6.5",
    "react-hook-form": "^7.49.0",
    "zod": "^3.22.4",
    "@hookform/resolvers": "^3.3.4",
    "lucide-react": "^0.312.0",
    "clsx": "^2.1.0",
    "tailwind-merge": "^2.2.0",
    "class-variance-authority": "^0.7.0",
    "react-markdown": "^9.0.1",
    "react-syntax-highlighter": "^15.5.0"
  },
  "devDependencies": {
    "@types/react": "^19.0.0",
    "@types/react-dom": "^19.0.0",
    "@vitejs/plugin-react": "^4.2.1",
    "typescript": "^5.3.3",
    "vite": "^5.0.11",
    "tailwindcss": "^3.4.1",
    "postcss": "^8.4.33",
    "autoprefixer": "^10.4.16",
    "@types/node": "^20.11.5"
  }
}
```

## File Size Budget

- Initial JS bundle: < 200KB gzipped
- Total page load: < 500KB
- Time to interactive: < 3s on 3G

## Testing Strategy

- Unit tests: Vitest + React Testing Library
- E2E tests: Playwright (optional)
- Integration tests: API mocking with MSW

## Documentation

- Inline JSDoc comments
- README.md in ui/ folder
- Storybook for component documentation (optional)
