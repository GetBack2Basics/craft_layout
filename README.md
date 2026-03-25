# 🗺️ craft_layout

**Geometric Optimization & Automated Cartography for ArcGIS Pro Map Series**

`craft_layout` is an ArcGIS Pro automation suite that treats layout selection as a spatial optimization problem. Instead of forcing varied geometries into a single "one-size-fits-all" orientation, it programmatically determines the best-fit aspect ratio and scale for every feature before automating the high-resolution export process.

---

## 🚀 The Logic

### 1. Geometric Analysis (`src/suggest_layout.py`)
This module performs a "best-fit" calculation by projecting feature bounding boxes against the usable area of your map frames.
*   **Orientation Logic:** Compares feature extents against the aspect ratios of Portrait and Landscape frames.
*   **Scale Optimization:** Calculates the maximum possible scale for each orientation, incorporating a 5% safety margin.
*   **Data Enrichment:** Appends `LAYOUT` (P/L) and `PAGE_SCALE` fields to the attribute table.

### 2. Contextual Production (`src/batch_export.py`)
Automates the export of finished PDFs with professional cartographic focus.
*   **Dynamic Switching:** Routes features to their optimized layout (P/L) during a single batch run.
*   **Contextual Backdrop:** Automatically generates a temporary "grey-out" layer for every page, desaturating surrounding features to ensure the primary subject is prominent while maintaining geographic context.

---

## 🛠️ Repository Structure
```text
craft_layout/
├── src/
│   ├── suggest_layout.py      # Spatial fitting & scale logic
│   └── batch_export.py        # Batch exporter with context layering
├── example/                   # Test data and setup instructions
├── toolbox/                   # (.atbx) ArcGIS Pro Script Tool wrapper
└── README.md