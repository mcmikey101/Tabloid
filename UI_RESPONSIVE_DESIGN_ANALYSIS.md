# PySide6 Application UI - Responsive Design Analysis

**Analysis Date:** April 12, 2026  
**Application:** Tabloid (Data Synthesis & ML Lab)  
**Current Minimum Window Size:** 1400x900 (hardcoded)

---

## Executive Summary

This PySide6 application has **significant responsive design issues** that will cause usability problems on smaller screens, tablets, and resizable windows. The UI uses many hardcoded dimensions, fixed widths/heights, and does not adapt to different screen sizes or orientations.

**Priority Level:** 🔴 **HIGH** - Multiple critical issues affecting core UI functionality

---

## 1. MAIN WINDOW (ui/main_window.py)

### Fixed Dimensions
- **Startup Window Size:** `1400 x 900` pixels (line 26: `self.resize(1400, 900)`)
  - **Impact:** Users with smaller screens cannot see the full application
  - **Problem:** No minimum/maximum size constraints defined
  
- **Sidebar Width:** `200` pixels (line 56: `sidebar.setFixedWidth(200)`)
  - **Impact:** Wastes 14% of screen width on small displays (< 1024px)
  - **Problem:** Navigation takes up too much space on tablets/small laptops

### Layout Issues
- **Root Layout Margins:** `0, 0, 0, 0` (line 40)
  - No padding around main content; harsh edges
- **Horizontal Layout:** No responsive behavior when resizing below minimum width
- **Navigation Buttons:** Fixed height with expanding width (good pattern, but undermined by fixed sidebar)

### Responsive Design Failures
- ❌ No screen size detection or adaptive geometry
- ❌ No minimum window size enforcement (users can resize below usable bounds)
- ❌ Sidebar cannot be collapsed/toggled for small screens
- ❌ No adaptive sidebar width based on window size

---

## 2. DATASETS PAGE (ui/pages/datasets_page.py)

### Fixed Layout Proportions
- **Splitter Initial Sizes:** `[250, 900, 300]` (line 62)
  - Left panel: 250px (dataset list)
  - Center panel: 900px (data table, stats, plot)
  - Right panel: 300px (version tree)
  - **Problem:** Total = 1450px but window is 1400px - forces horizontal scrollbar!
  - **Impact:** Only works for windows > 1450px; breaks on smaller displays
  
### Widget Layout Issues
- **Top Bar Layout:** Horizontal box with 5 buttons + 2 labels
  - **Problem:** All elements forced on one line; no wrapping
  - **Font sizes:** Hardcoded in style.qss (12px buttons)
  - **Minimum width needed:** ~900px (5 buttons × 140px + labels + spacing)
  - **Failure on:** < 1000px width

- **Center Panel:** Stacked vertically
  ```
  DataTable (variable height)
  ColumnStats (fixed layout, no scroll area)
  DistributionPlot (fixed Matplotlib figure size)
  ```
  - **Problem:** No scroll area for ColumnStats; if window height < 600px, content overflows
  - **Problem:** Three widgets share limited vertical space; no flexible allocation

### High-Risk Areas
- 🔴 Hard-coded splitter proportions won't work on screens < 1450px
- 🔴 Top button bar doesn't wrap or reorganize
- 🔴 No vertical scrolling for stacked widgets
- 🔴 DataTable header not sticky; difficult to navigate large datasets

---

## 3. EXPERIMENTS PAGE (ui/pages/experiments_page.py)

### Layout Structure
- **Vertical Stack:**
  - Filters GroupBox (Form layout)
  - Experiments Table
  - Details Panel (Text + buttons)

### Issues
- **Filters Section:** 
  - `QFormLayout` with 2 rows (Dataset, Model)
  - **Problem:** Fixed layout; no wrapping on narrow screens
  - **Minimum width:** ~350px (label + combobox)

- **Experiments Table:**
  - 6 columns with `setSectionResizeMode(QHeaderView.Stretch)`
  - **Problem:** On small screens, columns too narrow to read
  - **Problem:** No horizontal scrolling or column reorganization
  - **Minimum width:** ~600px for decent readability

- **Button Layout at Bottom:**
  - 2 buttons (Export Model, Delete Experiment)
  - **Problem:** Not responsive to container width

### Vertical Space Management
- ❌ No `addStretch()` between sections
- ❌ Multiple QGroupBox widgets with no scroll area
- ❌ Entire page will overflow on height < 600px

---

## 4. ML LAB PAGE (ui/pages/ml_lab_page.py)

### Layout Structure
```
Dataset Selection (QGroupBox with QFormLayout)
Model Selection (QGroupBox with QFormLayout)
Hyperparameter Section (QGroupBox)
Training Section (QGroupBox)
Metrics Section (QGroupBox)
```

### Critical Issues
- **Form Layouts:** Multiple QFormLayout widgets with form fields
  - **Problem:** Fixed label widths; labels/fields don't wrap
  - **Minimum width:** ~400px minimum
  
- **Feature Selection Dialog:**
  - **Hardcoded Size:** `dialog.resize(400, 400)` (line 108)
  - **Problem:** 400px too small for large feature lists (>20 columns)
  - **Problem:** Not screen-aware; could appear off-screen
  
- **Vertical Stacking:**
  - 5 major sections vertically stacked
  - Last section: `layout.addStretch()` (line 96)
  - **Problem:** Above sections don't have fixed heights; will fight for space
  - **Problem:** No scroll area for entire page
  - **Result:** Metrics section may not be visible without scrolling

### Scrollable Area Needed
- 🔴 Page height > 900px on initial load with all sections expanded
- 🔴 All 5 sections compete for limited vertical space
- 🔴 No scroll area wrapping the main content

---

## 5. DIALOGS

### A. SynthesisDialog (ui/dialogs/synthesis_dialog.py)

**Fixed Geometry:**
- Size: `setGeometry(100, 100, 400, 250)` (line 17)
  - **Problems:**
    - Hard-coded position (100, 100) = top-left, may appear off-screen on multi-monitor setups
    - Fixed size may be too small on large screens
    - May exceed available height on small screens (height=250px)

**Layout Issues:**
- 3 QHBoxLayout sections stacked vertically
- Mode combo, rows spinbox fit on one line
- **Problem:** On narrow screens (< 400px), layout breaks

**Improvement:** Already uses `setModal(True)` (good)

### B. OperationsDialog (ui/dialogs/operations_dialog.py)

**Fixed Geometry:**
- Size: `self.resize(900, 600)` (line 39)
  - **Problems:**
    - May exceed small screen dimensions (height=600px on 768p screen)
    - No responsiveness to screen size
    - No minimum size constraint

**Layout Issues:**
- Operations list (left side)
- Sequence table (center, takes most space)
- Button layout (bottom)
- **Problem:** Table columns don't resize intelligently

### C. ComparisonPlotsDialog (ui/dialogs/compare_plots_dialog.py)

**Responsive Geometry (✓ GOOD):**
```python
width = max(900, int(screen_geometry.width() * 0.8))
height = max(600, int(screen_geometry.height() * 0.85))
self.setGeometry(100, 100, width, height)
```
- **Positive:** Scales with screen size!
- **Negative:** Hard-coded position (100, 100) still problematic

**Layout Issues (Multiple):**
- Row 1: Version1 + Col1 selectors (setMaximumWidth: 200px)
- Row 2: Version2 + Col2 selectors (setMaximumWidth: 200px)  
- Row 3: Plot type + Scatter checkbox
- **Problem:** `setMaximumWidth()` caps growth; on narrow screens, crowded
- **Problem:** 4 labeled controls per row; wrapping needed

**Button Controls:**
- Scatter column buttons: `setMaximumWidth(80)` 
- Color combos: `setMaximumWidth(100)`
- **Problem:** Fixed widths cause misalignment on narrow screens

**Matplotlib Figure:**
```python
self.figure = Figure(figsize=(10, 5), dpi=80, ...)
```
- **Problem:** Hard-coded figsize; doesn't scale with dialog
- **Better:** Use dynamic figsize based on canvas size

### D. ProgressDialog (ui/dialogs/progress_dialog.py)

**Fixed Size:**
- Size: `self.resize(400, 150)` (line 19)
  - **Problem:** Very small dialog; may be hard to read text
  - **Problem:** Not responsive

**Layout:** Simple vertical layout (good), but size is issue

---

## 6. WIDGETS

### A. DataTableWidget (ui/widgets/data_table.py)

**Issues:**
- No row/column height settings; relies on defaults
- **Problem:** If table has many columns (>15), horizontal scrollbar appears
- **Problem:** DataFrame preview limited to 1000 rows (good); but display not optimized
- **Problem:** No fixed column widths mean very narrow columns on large tables

### B. DistributionPlotWidget (ui/widgets/distribution_plot.py)

**Fixed Figure Sizes:**
```python
self.figure = Figure(figsize=(8, 4), dpi=100, ...)  # Distribution plot
self.scatter_figure = Figure(figsize=(8, 4), dpi=100, ...)  # Scatter plot
```
- **Problem:** `figsize=(8, 4)` hardcoded; doesn't adapt to widget size
- **Problem:** On narrow displays, plot area too cramped
- **Better:** Use `FigureCanvas.get_width_height()` and calculate dynamic figsize

**Button Layout Issues:**
- `Export Plot` button: inline with type selector
- **Problem:** On narrow tabs, button wraps awkwardly

**Tab Widget:**
- Has 3 tabs (Distribution, Scatter, Metadata)
- **Problem:** On small screens, tab bar may wrap or become crowded

### C. ColumnStatsWidget (ui/widgets/column_stats.py)

**Layout:**
- QGroupBox → QScrollArea → QTextEdit
- **Good:** Has scroll area
- **Problem:** Text styling with monospace font (JetBrains Mono, 12px)
- **Problem:** Fixed 50-character separator line: `"=" * 50`
  - Doesn't scale with available width

### D. DatasetListWidget (ui/widgets/dataset_list.py)

**Items:**
- Search input field
- Dataset list
- "Add Dataset" button

**Layout:** Simple vertical (good)
**Problem:** No adaptive sizing for large dataset names

### E. VersionTreeWidget (ui/widgets/version_tree.py)

**Controls:**
- Search input
- Operation filter (QComboBox, `setMaximumWidth()` implicit from style)
- Sort option (QComboBox)
- **Problem:** 3 controls in one row; may wrap on narrow screens
- **Problem:** No collapsible controls

**Tree Widget:**
- Hierarchical display of versions
- **Good:** Scrollable by default
- **Problem:** No fixed column widths; entries may be very wide

---

## 7. STYLESHEET (ui/style.qss)

### Font Settings
- **App-wide font:** "Space Mono" monospace
  - **Problem:** Fixed after import; no fallback sizes
- **Button padding:** `8px 12px` (hardcoded)
- **Font sizes:** Hardcoded throughout
  - Buttons: `12px`
  - Labels in mini-UI: `10px`, `9px`
  - **Problem:** Not DPI-aware; text may be unreadable on high-DPI displays

### Scrollbar Widths
- Vertical: `width: 12px` (hardcoded)
- Horizontal: `height: 12px` (hardcoded)
- **Problem:** Fixed; may be too thick/thin on different displays

### Checkbox/Radio Button Sizes
- Checkbox indicator: `16px x 16px` (hardcoded)
- **Problem:** May be too small on 4K displays

---

## Summary Table: Responsive Design Issues by File

| File | Issue | Severity | Impact |
|------|-------|----------|--------|
| **main_window.py** | Fixed 1400×900, sidebar 200px | 🔴 HIGH | Unusable on screens < 1400px |
| **datasets_page.py** | Splitter: [250, 900, 300] = 1450px total | 🔴 HIGH | Horizontal scroll on all small screens |
| **datasets_page.py** | Top bar: 5 buttons don't wrap | 🔴 HIGH | Overflow on width < 1000px |
| **datasets_page.py** | No vertical scroll for stacked widgets | 🟠 MEDIUM | Overflow on height < 600px |
| **experiments_page.py** | Form layout no row wrapping | 🟠 MEDIUM | Hard to use on width < 600px |
| **experiments_page.py** | Table: 6 columns squeeze on small screens | 🟠 MEDIUM | Unreadable on width < 800px |
| **ml_lab_page.py** | Feature dialog: 400×400 hardcoded | 🟠 MEDIUM | May not fit; no screen scaling |
| **ml_lab_page.py** | 5 sections stacked, page height > 900px | 🟠 MEDIUM | Content overflow without scroll |
| **synthesis_dialog.py** | 400×250 hardcoded, position (100, 100) | 🟠 MEDIUM | Off-screen on multi-monitor; too small |
| **operations_dialog.py** | 900×600 hardcoded | 🟠 MEDIUM | Exceeds height on 768p; not responsive |
| **compare_plots_dialog.py** | Row controls: maxWidth caps (80-200px) | 🟡 LOW | Crowded on narrow screens |
| **compare_plots_dialog.py** | Figure figsize hardcoded (10, 5) | 🟡 LOW | Plot doesn't scale with dialog |
| **distribution_plot.py** | Figure figsize hardcoded (8, 4) | 🟡 LOW | Plot cramped on narrow tabs |
| **all dialogs** | Position hardcoded to (100, 100) | 🟡 LOW | Off-screen on multi-monitor |
| **style.qss** | Font sizes hardcoded (12px, 10px, 9px) | 🟡 LOW | Unreadable on high-DPI displays |
| **style.qss** | Scrollbar widths: 12px fixed | 🟡 LOW | Wrong scale on high-DPI/4K |

---

## Prioritized Recommendations

### **Phase 1: CRITICAL (Must fix for < 1400px screens)**

1. **Adjust Main Window Default Size**
   - Change from `1400×900` to `1200×700` (more realistic)
   - Add: `self.setMinimumSize(960, 600)` (minimum usable size)
   - Add: `self.setMaximumSize(QGuiApplication.primaryScreen().availableGeometry().size())`

2. **Fix Datasets Page Splitter**
   - Current: `[250, 900, 300]` (1450px total)
   - Change to: `[150, 1, 200]` (proportional ratios, not pixels)
   - Or: percentage-based: `width_px = self.width(); sidebar = width_px * 0.15; rest = width_px * 0.85`

3. **Add Scroll Area to Datasets Page Center Panel**
   - Wrap DataTable + Stats + Plot in QScrollArea
   - Allow unlimited height without overflow

4. **Reorganize Top Button Bar**
   - Move buttons to dropdown menu OR
   - Use gridLayout with wrapping OR
   - Create two-row button layout

### **Phase 2: HIGH (Should fix for tablets/1024p devices)**

5. **Make Sidebar Collapsible**
   - Add toggle button in top-left
   - Sidebar slides away on mobile/small screens
   - Or use hamburger menu icon

6. **Make Dialog Sizes Responsive**
   - `OperationsDialog`: Use screen % like ComparisonPlotsDialog
   - `SynthesisDialog`: Use screen % and add scroll area
   - `ProgressDialog`: Increase default size to 500×200

7. **Fix Dialog Positioning**
   - Replace `setGeometry(100, 100, ...)` with centered positioning:
     ```python
     screen = QApplication.primaryScreen().availableGeometry()
     self.move(screen.center() - self.rect().center())
     ```

8. **Fix Form Layouts in ML Lab**
   - Use `QScrollArea` wrapping entire page
   - Or make form fields stacked (label on top, field below)

### **Phase 3: MEDIUM (Nice-to-have improvements)**

9. **Dynamic Figure Sizes**
   - Calculate Matplotlib figsize based on canvas/widget size
   - Listen to resize events and regenerate plots

10. **Responsive Typography**
    - Scale font sizes based on screen DPI
    - Use `device().logicalDotsPerInch()` to calculate relative sizes

11. **Adaptive Sidebar Width**
    - Sidebar: 200px @ 1400px → 120px @ 1000px → 0px (collapsed) @ < 800px

12. **Table Column Optimization**
    - Auto-hide columns on narrow screens
    - Or use single-column card layout

---

## Files Needing Immediate Work

### 🔴 Highest Priority
1. [ui/main_window.py](ui/main_window.py) - Window sizing
2. [ui/pages/datasets_page.py](ui/pages/datasets_page.py) - Splitter + top bar + scroll
3. [ui/dialogs/operations_dialog.py](ui/dialogs/operations_dialog.py) - Responsive sizing

### 🟠 High Priority
4. [ui/dialogs/synthesis_dialog.py](ui/dialogs/synthesis_dialog.py) - Responsive sizing + positioning
5. [ui/pages/ml_lab_page.py](ui/pages/ml_lab_page.py) - Scroll area + form layout
6. [ui/widgets/distribution_plot.py](ui/widgets/distribution_plot.py) - Dynamic figure sizing

### 🟡 Medium Priority
7. [ui/dialogs/compare_plots_dialog.py](ui/dialogs/compare_plots_dialog.py) - Control widths + figure sizing
8. [ui/pages/experiments_page.py](ui/pages/experiments_page.py) - Form wrapping + table columns
9. [ui/style.qss](ui/style.qss) - DPI-aware font/scrollbar sizing

---

## Testing Checklist

- [ ] Test on 1920×1080 (Full HD) - current best case
- [ ] Test on 1440×810 - small laptop
- [ ] Test on 1024×768 - netbook/tablet
- [ ] Test on 800×600 - minimum usable (FAILS)
- [ ] Test window resizing down to 960×600
- [ ] Test on 2560×1440 (2K) - text scaling
- [ ] Test on 4K display - DPI scaling
- [ ] Test dialog centering with multiple monitors
- [ ] Test on mobile viewport (360px) with responsive redesign

---

## Next Steps

1. Create a responsive design utility module with screen-size helper functions
2. Implement a base widget class with auto-scaling behavior
3. Start with Phase 1 critical fixes in main_window.py and datasets_page.py
4. Add QScreen signal handling to re-layout on screen changes

