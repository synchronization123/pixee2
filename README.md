# DefectDojo Engagement Manager v1.0.9

Flask web application with **Open Jiras** modal for viewing and managing tests with mcr_jira tag.

## 🆕 Version 1.0.9 - Jiras Management Modal

### What's New in v1.0.9

#### 📋 **"Open Jiras" Button & Modal**

**New Button:** "Open Jiras" (info/cyan color) in action bar
- Opens fullscreen modal
- Shows tests with mcr_jira tag
- No data loaded until user clicks GO
- Modal closes only with X button (backdrop disabled)

**Modal Features:**
- Fullscreen layout for maximum visibility
- Advanced filters in single row
- Pagination with total records
- 10-column table display
- Inline editing capability

### Jiras Modal Structure

**Filters Row (7 fields):**
```
[Title Search] [Jira Status ▼] [Jira Type ▼] [Analysis Status ▼] [Assigned To ▼] [Build Type ▼] [Task ▼]
                                                            [GO]  [Clear Filters]
```

**Total & Pagination:**
```
Total Records: 156     [First] [Prev] [1] [2] [3] [Next] [Last]     Rows: [10 ▼]
```

**Table Columns:**
| ID | Added On | Jira | Jira Status | Jira Type | Analysis Status | Assigned To | Build Type | Task | Actions |
|----|----------|------|-------------|-----------|-----------------|-------------|------------|------|---------|
| 123 | 2025-10-15 | JIRA-456 | Ready | Security | Pending ▼ | John Doe ▼ | Dev ▼ | Assessment | 🖊️ |

### Filter Dropdowns

| Filter | API Source | Populated From |
|--------|------------|----------------|
| **Title** | Free text search | - |
| **Jira Status** | `branch_tag` | Unique values from tests |
| **Jira Type** | `commit_hash` | Unique values from tests |
| **Analysis Status** | `build_id` | Unique values from tests |
| **Assigned To** | `lead` | Users API (first_name last_name) |
| **Build Type** | `environment` | `/api/v2/development_environments/` |
| **Task** | `engagement` | Engagements API (name) |

### Table Column Mappings

| Display Column | API Field | Type | Notes |
|----------------|-----------|------|-------|
| **ID** | `id` | int | Test ID |
| **Added On** | `created` | date | Format: YYYY-MM-DD |
| **Jira** | `title` | string | Jira ticket title |
| **Jira Status** | `branch_tag` | string | Read-only |
| **Jira Type** | `commit_hash` | string | Read-only |
| **Analysis Status** | `build_id` | dropdown | Editable (Pending, On Hold, Approved, Rejected) |
| **Assigned To** | `lead` | dropdown | Editable (user dropdown) |
| **Build Type** | `environment` | string | Read-only, mapped from environments API |
| **Task** | `engagement` | string | Read-only, mapped from engagements API |
| **Actions** | - | button | Edit icon |

### Edit Test Modal

**Fields:**
- **Title:** Read-only (required for PUT)
- **Analysis Status:** Dropdown (Pending, On Hold, Approved, Rejected)
- **Assigned To:** Dropdown (required - users list)
- **Build Type:** Dropdown (required - environments list)

**Mandatory PUT Parameters:**
- id (URL parameter)
- title
- target_start
- target_end
- test_type_name
- engagement
- lead
- test_type
- environment

## Workflow

### 1. Open Jiras Modal
```
User clicks "Open Jiras" button
  ↓
Fullscreen modal opens
  ↓
Filters displayed (empty)
  ↓
Table shows: "Click GO to load Jira items"
  ↓
Load filter options (background)
```

### 2. Filter & Load Data
```
User selects filters
  ↓
Clicks GO button
  ↓
Loading modal shows
  ↓
GET /api/tests with filters
  ↓
Table populated with results
  ↓
Pagination enabled
```

### 3. Edit Test
```
Click edit icon in Actions column
  ↓
Edit modal opens
  ↓
Fields populated with current values
  ↓
User edits Analysis Status / Assigned To / Build Type
  ↓
Clicks Save
  ↓
PUT /api/test/<id>
  ↓
Toast notification
  ↓
Edit modal closes
  ↓
Jiras table reloads
```

### 4. Close Jiras Modal
```
Click X button (top-right)
  ↓
Modal closes
  ↓
Back to engagements view
```

## API Endpoints

### GET /api/tests

**Purpose:** Fetch tests with mcr_jira tag

**Query Parameters:**
- page (int)
- limit (int)
- title (string) - search filter
- jira_status (string) - branch_tag filter
- jira_type (string) - commit_hash filter
- analysis_status (string) - build_id filter
- assigned_to (int) - lead filter
- build_type (int) - environment filter
- task (int) - engagement filter

**Response:**
```json
{
    "success": true,
    "data": [{
        "id": 123,
        "created": "2025-10-15",
        "title": "JIRA-456",
        "branch_tag": "Ready",
        "commit_hash": "Security",
        "build_id": "Pending",
        "lead": "John Doe",
        "lead_id": 5,
        "environment": "Development",
        "environment_id": 2,
        "engagement": "Security Assessment",
        "engagement_id": 14,
        "target_start": "2025-11-01",
        "target_end": "2025-11-15",
        "test_type": 3,
        "test_type_name": "Security Scan"
    }],
    "total": 156,
    "page": 1,
    "limit": 10
}
```

### PUT /api/test/<id>

**Purpose:** Update test

**Request:**
```json
{
    "title": "JIRA-456",
    "target_start": "2025-11-01",
    "target_end": "2025-11-15",
    "test_type_name": "Security Scan",
    "engagement": 14,
    "lead": 5,
    "test_type": 3,
    "environment": 2,
    "build_id": "Approved"
}
```

**Response:**
```json
{
    "success": true,
    "message": "Test updated successfully",
    "data": { /* updated test object */ }
}
```

### GET /api/test-filter-options

**Purpose:** Get unique values for filter dropdowns

**Response:**
```json
{
    "success": true,
    "jira_status": ["Ready", "In Progress", "Done"],
    "jira_type": ["Security", "Functional"],
    "analysis_status": ["Pending", "On Hold", "Approved"],
    "assigned_to": [{"id": 5, "name": "John Doe"}],
    "build_type": [{"id": 2, "name": "Development"}],
    "task": [{"id": 14, "name": "Security Assessment"}]
}
```

## All Features (v1.0.9)

### New in v1.0.9
- ✅ **Open Jiras button** (cyan/info color)
- ✅ **Fullscreen Jiras modal**
- ✅ **7 filters in single row**
- ✅ **GO button** (loads data on-demand)
- ✅ **Tests table** with 10 columns
- ✅ **Edit test modal**
- ✅ **PUT /api/test/<id>** endpoint
- ✅ **Analysis Status dropdown** in table
- ✅ **Pagination** for tests
- ✅ **Environment mapping** from API
- ✅ **Engagement mapping** from API

### From Previous Versions
- ✅ Edit engagement modal (v1.0.8)
- ✅ Actions column (v1.0.8)
- ✅ Toast notifications (v1.0.7)
- ✅ branch_tag support (v1.0.7)
- ✅ On-demand Jira counts with caching (v1.0.6)
- ✅ 7 Jira count columns (v1.0.5)
- ✅ Status filtering, date highlighting
- ✅ Advanced filtering, pagination
- ✅ Fast initial loading

## Project Structure

```
DefectDojo-Engagement-Manager/
│
├── Launcher.pyw           # GUI launcher
├── app.py                 # ✨ Added /api/tests, /api/test/<id>, /api/test-filter-options
├── token.json             # API token
├── project.json           # ✨ v1.0.9 metadata
├── requirements.txt       # Dependencies
├── README.md              # This file
│
├── templates/
│   └── engagement.html    # ✨ Open Jiras button + fullscreen modal + edit test modal
│
└── static/
    ├── css/
    │   └── style.css      # Styling
    └── js/
        └── engagement.js  # ✨ Jiras modal logic + test management
```

## Installation & Usage

```bash
pip install -r requirements.txt
python app.py
```

Open: http://127.0.0.1:5000

## Usage Example

1. **View Engagements:** Default page shows engagements table
2. **Open Jiras:** Click "Open Jiras" button → fullscreen modal opens
3. **Filter Tests:** Select filters (e.g., Analysis Status = Pending)
4. **Load Data:** Click GO → tests load with filters applied
5. **Edit Test:** Click edit icon → edit modal opens → change Analysis Status → Save
6. **Close Modal:** Click X button → back to engagements

## Version Info

- **Version**: 1.0.9
- **Serial**: DDJ-ENG-2025-001
- **Date**: October 26, 2025
- **Token**: 23c9945cca388d552531c814f8079803c25d8dca

## Troubleshooting

### Modal Not Opening
1. Check console for JavaScript errors
2. Verify Bootstrap JS loaded

### No Data in Jiras Table
1. Click GO button to load data
2. Check filters - may be too restrictive
3. Verify tests have mcr_jira tag

### Edit Test Fails
1. Verify all required fields filled
2. Check API connectivity
3. Review server logs

## Browser Support

- ✅ Chrome 90+
- ✅ Firefox 88+
- ✅ Edge 90+
- ✅ Safari 14+

---

**DefectDojo Engagement Manager - Complete Test Management with Jiras Modal**
