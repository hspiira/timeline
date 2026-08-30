# Timeline UI - Project TODO

**Last Updated**: December 22, 2024
**Project**: Timeline Event Sourcing System - React Frontend
**Backend**: FastAPI with multi-tenant event sourcing architecture

---

## 📊 Implementation Status Overview

### Backend Status (from ~/dev/timeline)
| Feature | Status | API Available |
|---------|--------|--------------|
| Multi-Tenancy | ✅ Complete | Yes |
| User Authentication | ✅ Complete | Yes |
| Subject Management | ✅ Complete | Yes |
| Event Sourcing | ✅ Complete | Yes |
| Cryptographic Chaining | ✅ Complete | Yes |
| Schema Registry | ✅ Complete | Yes |
| Document Storage | ✅ Complete | Yes |
| RBAC System | ✅ Complete | Yes |
| Workflows | ✅ Complete | Yes |
| Email Integration | ✅ Complete | Yes |

### Frontend Status (ui.timeline)
| Feature | Status | Route/Component |
|---------|--------|----------------|
| Authentication | ✅ Complete | `/login`, `/register` |
| Dashboard | ✅ Complete | `/` - Connected to real API |
| Subjects List | ✅ Complete | `/subjects` |
| Subject Detail | ✅ Complete | `/subjects/$subjectId` |
| Events List | ✅ Complete | `/events` |
| Event Detail (by Subject) | ✅ Complete | `/subjects/$subjectId` (Events tab) |
| Event Creation | ✅ Complete | `/events/create` |
| Subject Creation | ✅ Complete | `/subjects` (modal) |
| Document Upload | ✅ Complete | Component in subject detail page |
| Document List | ✅ Complete | Component in subject detail page |
| Document Viewer | ✅ Complete | PDF/image preview modal |
| Event Schemas | ✅ Complete | `/schemas` (list, create, view, delete) |
| Workflows | ✅ Complete | `/workflows` (list, create, delete) |
| Email Accounts | ✅ Complete | `/email-accounts` (list, create, details, sync) |
| Chain Verification | ✅ Complete | `/verify/$subjectId` |
| RBAC Management | ❌ Missing | - |

---

## 🎯 Priority Tasks

### P0 - Critical (Required for MVP)

#### 1. ✅ COMPLETE - Connect Dashboard to Real API
**File**: `src/routes/index.tsx`

**Status**: ✅ **COMPLETE** - Dashboard fully integrated with real API using Promise.allSettled() for resilient parallel requests

---

#### 2. ✅ COMPLETE - Event Creation Form
**Location**: `/src/routes/events/create.tsx`

**Status**: ✅ **COMPLETE** - Full event creation flow with:
- Dynamic form generation from event schemas
- Subject and event type selectors
- DateTime picker with support for backdating
- Schema-based field validation
- Error handling and API integration

**Components Implemented**:
- ✅ `JsonSchemaForm.tsx` - Dynamic form fields from JSON Schema
- ✅ `SubjectSelector.tsx` - Subject selection with API fetch
- ✅ `EventTypeSelector.tsx` - Event type selection with schema fallback

---

#### 3. ✅ COMPLETE - Document Upload & Management
**Location**: `/src/components/documents/`

**Status**: ✅ **COMPLETE** - Full document handling with:
- ✅ `DocumentUpload.tsx` - Drag & drop, file validation, progress indicator
- ✅ `DocumentList.tsx` - Table view of documents with download/delete
- ✅ `DocumentViewer.tsx` - PDF and image preview modal

**Integration**: Fully integrated into subject detail page (`/events/subject/$subjectId`)

---

#### 4. ✅ COMPLETE - Chain Verification UI
**Location**: `/src/routes/verify/$subjectId.tsx`

**Status**: ✅ **COMPLETE** - Full chain verification implementation with:
- ✅ Verify button on Subject Detail page (navigates to verify route)
- ✅ Real API integration with `GET /events/verify/{subject_id}` endpoint
- ✅ Verification result display with visual status indicators
- ✅ Chain visualization:
  - ✅ Timeline view with per-event verification status
  - ✅ Color-coded indicators (valid: green, invalid: red)
  - ✅ Genesis event highlighting
  - ✅ Event sequence numbers and timestamps
- ✅ Hash comparison display:
  - ✅ Expected vs. actual hash comparison
  - ✅ Error details for failed events
  - ✅ Hash mismatch highlighting
  - ✅ Tampering details section
- ✅ Integrity metrics:
  - ✅ Overall chain validity status
  - ✅ Event count and validity breakdown
  - ✅ Integrity percentage calculation
- ✅ JSON export:
  - ✅ Export verification report as JSON
  - ✅ Includes summary and event details

**API Endpoint**: `GET /events/subject/{subject_id}/verify`
**Verified Timestamp**: Included in all reports

---

### P1 - High Priority (Core Features)

#### 5. ✅ COMPLETE - Event Schema Management
**Location**: `/src/routes/schemas/`

**Status**: ✅ **COMPLETE** - Full schema management with:
- ✅ Schema listing with table view (event_type, version, is_active, created_at)
- ✅ Create new schema modal with JSON editor
- ✅ View/edit schema modal with full details
- ✅ Delete schema functionality
- ✅ Active/inactive status indicators

**API Integration**: Full integration with backend schema API endpoints

---

#### 6. ✅ COMPLETE - Workflow Management
**Location**: `/src/routes/workflows/`

**Status**: ✅ **COMPLETE** - Full workflow management with:
- ✅ Workflow listing with table view (name, trigger event type, status, actions count)
- ✅ Create new workflow modal with configuration
- ✅ Delete workflow functionality
- ✅ Active/inactive status indicators
- ✅ Filter by event type
- ✅ Error handling for permission-based access

**API Integration**: Full integration with backend workflow API endpoints

---

#### 7. Cryptographic Chain Verification UI
**Location**: Create `/src/routes/verify/$subjectId.tsx`

**Features**:
- [ ] Subject chain verification page:
  - [ ] Verify button on Subject Detail page (already present, navigates to verify route)
  - [ ] Call `GET /events/subject/{id}/verify` endpoint
  - [ ] Display verification result with status indicators
  - [ ] Show integrity status (✅ Valid / ❌ Tampered)
- [ ] Chain visualization:
  - [ ] Timeline view showing hash links between events
  - [ ] Display `hash` and `previous_hash` for each event
  - [ ] Visual indicators for chain breaks and tamper detection
  - [ ] Highlight genesis event (first in chain)
  - [ ] Color-coded status indicators (valid: green, invalid: red)
- [ ] Hash comparison view:
  - [ ] Side-by-side comparison of stored vs. computed hash
  - [ ] Show which events failed verification
  - [ ] Highlight tampering location with details
  - [ ] Display hash mismatch information
- [ ] Export verification report:
  - [ ] PDF report with chain status and verified timestamp
  - [ ] Include all hashes and verification results
  - [ ] Summary of integrity findings

**Priority**: P1
**Estimated Effort**: 6-8 hours
**API Endpoint**: `GET /events/subject/{subject_id}/verify`
**Status**: ❌ NOT STARTED
**Dependencies**: Backend verify endpoint available

---

### P2 - Medium Priority (Enhanced Features)

#### 8. ✅ COMPLETE - Email Integration UI
**Location**: `/src/routes/email-accounts/`

**Status**: ✅ **COMPLETE** - Full email integration with:
- ✅ Email accounts list with table view
- ✅ Provider selection (Gmail, Outlook, IMAP, iCloud, Yahoo)
- ✅ IMAP connection with test functionality
- ✅ Account details page
- ✅ Manual sync (incremental and full)
- ✅ Disconnect account functionality
- ✅ Navigation integration
- ✅ Proper icons for email providers

**Pages**:
- ✅ `/email-accounts/index.tsx` - List email accounts:
  - ✅ Table: email, provider, last sync, status
  - ✅ Connect new account button
  - ✅ Sync now button per account
  - ✅ View account details link
- ✅ `/email-accounts/create.tsx` - Connect email account:
  - ✅ Provider selection (Gmail, Outlook, IMAP, iCloud, Yahoo)
  - ⏳ Gmail OAuth flow (needs OAuth credentials in backend .env)
  - ⏳ Outlook OAuth flow (needs OAuth credentials in backend .env)
  - ✅ IMAP credentials form:
    - ✅ Email address
    - ✅ Password (app-specific)
    - ✅ IMAP server & port
    - ✅ SSL/TLS toggle
  - ✅ Test connection (client-side validation)
  - ✅ Save account
- ✅ `/email-accounts/$accountId.tsx` - Account details:
  - ✅ Account info display
  - ✅ Sync status (last sync, provider, active status)
  - ✅ Manual sync buttons (incremental & full)
  - ✅ Disconnect account with confirmation
  - ⏳ View email events timeline (use events page with filter)

**Features**:
- ⏳ OAuth popup/redirect flow (UI ready, needs backend OAuth setup)
- ✅ Credential encryption (handled by backend)
- ✅ Sync progress indicator
- ✅ Email events integration (events created as `email_received` type)
- ⏳ Filter events by `event_type=email_received` (use events page)

**Priority**: P2
**Estimated Effort**: 12-14 hours ✅ COMPLETED
**API Endpoints**:
- ✅ `GET /email-accounts/` - List accounts
- ✅ `POST /email-accounts/` - Create account
- ✅ `GET /email-accounts/{id}` - Get account details
- ✅ `PATCH /email-accounts/{id}` - Update account
- ✅ `DELETE /email-accounts/{id}` - Delete/disconnect account
- ✅ `POST /email-accounts/{id}/sync` - Trigger sync

**Next Steps**:
1. Configure OAuth credentials in backend `.env` (see `~/dev/timeline/docs/email_oauth_setup_guide.md`)
2. Run `python scripts/oauth_setup_wizard.py` to get OAuth tokens
3. Add email event filtering to events page

---

#### 9. RBAC & Permissions Management
**Location**: Create `/src/routes/admin/`

**Pages**:
- [ ] `/admin/roles/index.tsx` - List roles:
  - [ ] Table: role name, description, permissions count
  - [ ] Create role button
  - [ ] Edit/delete role
- [ ] `/admin/roles/create.tsx` - Create role:
  - [ ] Role name & description
  - [ ] Permission selector (multi-select)
  - [ ] Save role
- [ ] `/admin/roles/$roleId.tsx` - Edit role:
  - [ ] Update name & description
  - [ ] Add/remove permissions
  - [ ] View users with this role
- [ ] `/admin/permissions/index.tsx` - List permissions:
  - [ ] Table: permission name, resource, action
  - [ ] Create permission button
  - [ ] Filter by resource
- [ ] `/admin/users/$userId/roles.tsx` - Assign roles:
  - [ ] User info
  - [ ] Current roles list
  - [ ] Add role selector
  - [ ] Remove role button

**Features**:
- [ ] Permission matrix view
- [ ] Role hierarchy visualization
- [ ] User role assignment
- [ ] Permission-based UI rendering
- [ ] Protected routes

**Frontend Permission Checks**:
- [ ] Hide/show UI elements based on permissions
- [ ] Disable actions without permission
- [ ] Redirect unauthorized users
- [ ] Display permission denied message

**Priority**: P2
**Estimated Effort**: 10-12 hours
**API Endpoints**: `GET /roles/`, `POST /roles/`, `GET /permissions/`, `POST /user-roles/`

---

#### 10. Tenant Management (Admin Only)
**Location**: Create `/src/routes/admin/tenants/`

**Pages**:
- [ ] `/admin/tenants/index.tsx` - List tenants:
  - [ ] Table: code, name, status, created_at
  - [ ] Create tenant button
  - [ ] Suspend/activate tenant
  - [ ] View tenant details
- [ ] `/admin/tenants/create.tsx` - Create tenant:
  - [ ] Tenant code (unique)
  - [ ] Organization name
  - [ ] Status (active/suspended)
  - [ ] Create tenant
- [ ] `/admin/tenants/$tenantId.tsx` - Tenant details:
  - [ ] Tenant info
  - [ ] User count
  - [ ] Subject count
  - [ ] Event count
  - [ ] Update settings
  - [ ] Suspend/delete tenant

**Features**:
- [ ] Tenant status management
- [ ] Usage statistics per tenant
- [ ] Tenant configuration
- [ ] Superadmin only access

**Priority**: P2
**Estimated Effort**: 6-8 hours
**API Endpoints**: `GET /tenants/`, `POST /tenants/`, `PATCH /tenants/{id}`

---

### P3 - Low Priority (Polish & UX)

#### 11. Enhanced Dashboard Analytics
**File**: `src/routes/index.tsx`

**Features**:
- [ ] Event volume chart:
  - [ ] Line chart for last 7/30 days
  - [ ] Event count per day
  - [ ] Hover tooltips with details
- [ ] Event type distribution:
  - [ ] Pie chart of event types
  - [ ] Percentage breakdown
  - [ ] Click to filter
- [ ] Subject type breakdown:
  - [ ] Bar chart of subject types
  - [ ] Count per type
- [ ] Recent workflow executions:
  - [ ] List of last 10 executions
  - [ ] Status indicators
  - [ ] Link to workflow details
- [ ] System health indicators:
  - [ ] API status
  - [ ] Database status
  - [ ] Storage usage
- [ ] Quick actions section:
  - [ ] Create subject button
  - [ ] Log event button
  - [ ] Verify chain button

**Chart Library**: Recharts or Chart.js

**Priority**: P3
**Estimated Effort**: 8-10 hours

---

#### 12. Advanced Search & Filtering
**Location**: Enhance existing list pages

**Global Features**:
- [ ] Global search bar in header
- [ ] Search across subjects and events
- [ ] Advanced filter panel:
  - [ ] Date range picker
  - [ ] Event type multi-select
  - [ ] Subject type filter
  - [ ] Payload field filters
- [ ] Saved filters:
  - [ ] Save current filter as preset
  - [ ] Quick access to saved filters
  - [ ] Share filters via URL
- [ ] Export functionality:
  - [ ] Export results to CSV
  - [ ] Export to JSON
  - [ ] Include filters in export

**Priority**: P3
**Estimated Effort**: 8-10 hours

---

#### 13. User Profile & Settings
**Location**: Create `/src/routes/profile/`

**Pages**:
- [ ] `/profile/index.tsx` - User profile:
  - [ ] Display user info
  - [ ] Edit name, email
  - [ ] Avatar upload
  - [ ] Change password
- [ ] `/profile/settings.tsx` - User settings:
  - [ ] Email notifications
  - [ ] UI preferences (theme, language)
  - [ ] API tokens management
  - [ ] Activity log

**Features**:
- [ ] Profile picture upload
- [ ] Password change with validation
- [ ] API token generation
- [ ] Personal activity log viewer

**Priority**: P3
**Estimated Effort**: 6-8 hours

---

#### 14. Notifications System
**Location**: Create `/src/components/notifications/`

**Components**:
- [ ] `NotificationToast.tsx` - Toast notifications
- [ ] `NotificationCenter.tsx` - Notification panel
- [ ] `NotificationBell.tsx` - Bell icon with count

**Features**:
- [ ] Toast notifications for:
  - [ ] Event created
  - [ ] Subject created
  - [ ] Workflow executed
  - [ ] Document uploaded
  - [ ] Errors
- [ ] Notification center:
  - [ ] List of recent notifications
  - [ ] Mark as read
  - [ ] Clear all
- [ ] Real-time notifications (WebSocket optional)

**Priority**: P3
**Estimated Effort**: 6-8 hours

---

## 🔧 Technical Debt & Improvements

### Code Quality

#### Refactoring
- [ ] Extract event timeline to `<EventTimeline />` component
- [ ] Create shared form components:
  - [ ] `<DateTimePicker />`
  - [ ] `<SubjectSelector />`
  - [ ] `<EventTypeSelector />`
- [ ] Consolidate error handling patterns
- [ ] Standardize loading states
- [ ] Create custom hooks:
  - [ ] `useEvents()`
  - [ ] `useSubjects()`
  - [ ] `useWorkflows()`
  - [ ] `useEventSchemas()`

#### TypeScript
- [x] All components have proper TypeScript types
- [x] No `any` types in components
- [ ] Add JSDoc comments to utility functions
- [ ] Type guards for API responses
- [ ] Shared types package between frontend/backend
- [ ] Strict mode enabled

#### Testing
- [ ] Set up Vitest for unit tests
- [ ] Add React Testing Library
- [ ] Test authentication flows:
  - [ ] Login
  - [ ] Register
  - [ ] Logout
  - [ ] Token refresh
- [ ] Test CRUD operations:
  - [ ] Subject creation
  - [ ] Event creation
  - [ ] Document upload
- [ ] E2E tests with Playwright:
  - [ ] User journey tests
  - [ ] Critical path coverage
- [ ] API mocking with MSW

---

### Performance

#### Optimization
- [ ] Implement TanStack Query for caching:
  - [ ] Cache subjects list
  - [ ] Cache events
  - [ ] Cache event schemas
  - [ ] Cache workflows
  - [ ] Stale-while-revalidate strategy
- [ ] Add pagination:
  - [ ] Subjects list (100 per page)
  - [ ] Events list (50 per page)
  - [ ] Workflow executions (50 per page)
- [ ] Virtual scrolling:
  - [ ] Long event timelines
  - [ ] Large subject lists
- [ ] Debounce search inputs (300ms)
- [ ] Lazy load routes:
  - [ ] Code splitting per route
  - [ ] Suspense boundaries
- [ ] Bundle optimization:
  - [ ] Tree shaking
  - [ ] Dynamic imports
  - [ ] Minimize bundle size

#### Caching Strategy
- [ ] Cache TTL configuration
- [ ] Invalidation on mutations
- [ ] Optimistic updates for:
  - [ ] Event creation
  - [ ] Subject creation
  - [ ] Document upload
- [ ] Background refetching

---

### UX/UI Polish

#### Design System
- [ ] Component documentation
- [ ] Storybook setup
- [ ] Component usage examples
- [ ] Accessibility audit (WCAG 2.1 AA):
  - [ ] Keyboard navigation
  - [ ] Screen reader support
  - [ ] Focus management
  - [ ] Color contrast
  - [ ] ARIA labels

#### Responsive Design
- [x] Mobile-responsive layouts
- [ ] Touch-friendly controls (larger tap targets)
- [ ] Mobile navigation menu (hamburger)
- [ ] Tablet layout optimizations
- [ ] Progressive Web App:
  - [ ] Service worker
  - [ ] Offline support
  - [ ] Install prompt

#### Dark Mode
- [x] Theme toggle implemented
- [x] All pages support dark mode
- [x] OKLCH monochromatic color scheme
- [ ] System theme sync
- [ ] Persist theme preference to backend
- [ ] Chart colors for dark mode

---

## 🚀 Future Enhancements (Post-MVP)

### Advanced Features

#### 1. Event Replay & Time Travel
- [ ] Query state at specific timestamp
- [ ] Event replay functionality
- [ ] State snapshots
- [ ] Historical comparisons
- [ ] "What-if" scenarios

#### 2. GraphQL API Layer
- [ ] GraphQL schema
- [ ] Apollo Client integration
- [ ] Subscription support
- [ ] Real-time updates
- [ ] Optimistic UI

#### 3. Real-time Collaboration
- [ ] WebSocket connection
- [ ] Live event updates
- [ ] Multi-user presence
- [ ] Conflict resolution
- [ ] Collaborative editing

#### 4. Compliance Features
- [ ] GDPR data export
- [ ] Right to deletion UI
- [ ] Retention policy management
- [ ] Audit log viewer
- [ ] Compliance reports

#### 5. Integration Marketplace
- [ ] Plugin system
- [ ] Third-party integrations
- [ ] Webhook configuration
- [ ] OAuth app management

---

## 📋 Immediate Next Steps

### Current Status Summary
✅ **MVP Foundation Complete**: Dashboard, Events, Subjects, Documents, Schemas, and Workflows are all fully implemented and integrated.

### Next Priority: Chain Verification UI (P1)
**Estimated Timeline**: 1-2 days

**Tasks**:
1. [ ] Create `/src/routes/verify/$subjectId.tsx`
2. [ ] Implement verification result fetching from API
3. [ ] Build chain visualization component
4. [ ] Display hash verification status
5. [ ] Create tamper detection visualization
6. [ ] Add export/report functionality
7. [ ] Test verification flow end-to-end
8. [ ] Integrate with subject detail page

**Dependencies**: Backend verify endpoint at `/events/subject/{id}/verify` must be available

### After Chain Verification: P2 Features
1. **Email Integration** (12-14 hours) - Connect email accounts (Gmail, Outlook, IMAP)
2. **RBAC Management** (10-12 hours) - Role-based access control UI
3. **Tenant Management** (6-8 hours) - Admin tenant management interface

---

## 🔗 Related Documentation

### Backend
- **Architecture Guide**: `~/dev/timeline/docs/ARCHITECTURE_GUIDE.md`
- **API Documentation**: `http://localhost:8000/docs`
- **Models**: `~/dev/timeline/models/`
- **API Endpoints**: `~/dev/timeline/api/`
- **Services**: `~/dev/timeline/services/`

### Frontend
- **Components**: `src/components/`
- **Routes**: `src/routes/`
- **API Client**: `src/lib/api-client.ts`
- **Types**: `src/lib/types.ts`
- **Hooks**: `src/hooks/`

---

## 📝 Notes & Known Issues

### Known Issues
1. **Session Timeout**: JWT tokens expire after 8 hours
   - Backend config: `~/dev/timeline/core/config.py:18`
   - Recently increased from 30 minutes
   - **Status**: ✅ EXPECTED BEHAVIOR - Not an issue, designed for security

### Fixed Issues (December 25, 2024)
1. **Workflow Toggle** ✅ FIXED
   - Added workflow update endpoint to API client: `workflows.update(id, { is_active: boolean })`
   - Implemented toggle functionality with loading state and error handling
   - File: `src/routes/settings/workflows/index.tsx:119-156`
   - Button now enables/disables workflows with proper permission checking

2. **Schema Delete** ✅ VERIFIED - Already Working
   - File: `src/routes/settings/schemas/index.tsx:97`
   - The backend delete call was already implemented - issue was incorrectly documented
   - DELETE endpoint properly called and UI correctly updates

3. **Chain Verification Permissions** ✅ ENHANCED
   - File: `src/routes/verify/$subjectId.tsx:42-74`
   - Improved error handling to distinguish between:
     - 403 Forbidden: "You do not have permission to verify this chain"
     - 401 Unauthorized: "Your session has expired"
     - Generic errors: Display actual error message
   - Now provides user-friendly error messages based on error type

### Design Decisions
- **Monochromatic Theme**: Pure grayscale OKLCH for accessibility
- **Type Safety**: OpenAPI-generated types ensure alignment
- **Component Structure**: Shared in `/components`, page-specific in routes
- **State Management**: TanStack Store for auth, TanStack Query for data
- **Routing**: TanStack Router with type-safe routes

### Questions for Product Owner
- [ ] Email integration visibility: all users or admin-only?
- [ ] Permissions for event creation vs. viewing?
- [ ] Workflows: tenant-wide or user-specific?
- [ ] Compliance requirements: GDPR, HIPAA, SOC 2?
- [ ] Mobile app needed or responsive web only?

---

**Status Key**:
- ✅ Complete - Fully implemented and tested
- 🟡 Partial - Started but incomplete
- ❌ Missing - Not yet started
- 🔄 In Progress - Currently being worked on
- ⭐ High priority item
