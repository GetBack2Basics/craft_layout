Because GIS scripts rely on specific Project (`.aprx`) and Layer configurations, use this guide to set up a test environment in ArcGIS Pro.

## 1. Project Setup
1.  Open ArcGIS Pro and create a new project.
2.  **Create Two Layouts** named exactly:
    *   `A3_PORTRAIT`
    *   `A3_LANDSCAPE`
3.  In each layout, insert a **Map Frame**. Ensure the map frames are the primary elements in the layout.

## 2. Prepare Test Data
1.  Add a Polygon layer to your map (e.g., administrative boundaries or parcels).
2.  Ensure the layer is in a **Projected Coordinate System** (e.g., MGA Zone 55, Web Mercator, etc.). The scripts will fail on Geographic (Lat/Lon) systems to prevent scale errors.
3.  Select a few features that are clearly "wide" and a few that are "tall."

## 3. Running the Test
### Step A: Suggestion
*   Open the Python window in ArcGIS Pro.
*   Run `src/suggest_layout.py` passing your layer as the parameter.
*   **Verify:** Open your layer's attribute table. You should see two new fields: `LAYOUT` (filled with P or L) and `PAGE_SCALE` (filled with a rounded scale integer).

### Step B: Configuration
*   In your `A3_PORTRAIT` layout, configure the **Map Series**:
    *   **Index Layer:** Your test layer.
    *   **Map Series Filter:** `LAYOUT = 'P'`.
    *   **Map Series Scale:** Use the `PAGE_SCALE` field.
*   Repeat for `A3_LANDSCAPE` using `LAYOUT = 'L'`.

### Step C: Export
*   Run `src/batch_export.py`.
*   **Verify:** Check your output folder. You should have two PDFs. Open them to see the automated "grey-out" context layer applied to every page.

## 🧪 Expected Results
The final PDFs should show each feature perfectly centered in its optimal orientation, with the surrounding features significantly faded (80% transparency) to emphasize the focus area.