# -*- coding: utf-8 -*-
"""
craft_layout: Orientation & Scale Suggester
-------------------------------------------
Analyzes feature geometry against Portrait and Landscape map frames to 
determine the optimal layout orientation and best-fit scale.

Logic:
1. Compares feature extents against usable interior areas of map frames.
2. Incorporates a safety margin to prevent feature clipping.
3. Outputs 'P' or 'L' and a rounded 'Nice Scale' to the attribute table.
"""

import arcpy
import math
from typing import Tuple, Optional
from contextlib import contextmanager

# Default User Settings
PORTRAIT_LAYOUT_NAME = "A3_PORTRAIT"
LANDSCAPE_LAYOUT_NAME = "A3_LANDSCAPE"
MARGIN_PCT = 0.05  # 5% margin on all sides

def _units_to_mm_factor(page_units: str) -> float:
    """Converts layout page units to millimeters."""
    u = (page_units or "").upper()
    factors = {
        "MILLIMETERS": 1.0,
        "CENTIMETERS": 10.0,
        "INCHES": 25.4,
        "POINTS": 25.4 / 72.0
    }
    return factors.get(u, 1.0)

def _find_mapframe_size_mm(aprx: arcpy.mp.ArcGISProject, layout_name: str) -> Tuple[float, float]:
    """Returns the size (W, H) of the first map frame in a named layout in mm."""
    for lyt in aprx.listLayouts():
        if lyt.name == layout_name:
            mfs = lyt.listElements("MAPFRAME_ELEMENT")
            if mfs:
                mf = mfs[0]
                f = _units_to_mm_factor(lyt.pageUnits)
                return mf.elementWidth * f, mf.elementHeight * f
            raise RuntimeError(f"Layout '{layout_name}' has no map frames.")
    
    available = ", ".join([l.name for l in aprx.listLayouts()])
    raise RuntimeError(f"Layout '{layout_name}' not found. Available: {available}")

def _best_fit_scale(ext_w_m: float, ext_h_m: float, frame_w_mm: float, frame_h_mm: float, margin: float) -> int:
    """Computes the optimal scale to fit the extent into the frame considering margins."""
    # Apply margin: eff_dim = dim * (1 - 2*margin)
    eff_w_m = (frame_w_mm * (1.0 - 2.0 * margin)) / 1000.0
    eff_h_m = (frame_h_mm * (1.0 - 2.0 * margin)) / 1000.0
    
    scale_w = ext_w_m / eff_w_m
    scale_h = ext_h_m / eff_h_m
    raw_scale = max(scale_w, scale_h)
    
    # "Nice Scale" rounding logic
    if raw_scale < 1000: return int(math.ceil(raw_scale / 100) * 100)
    if raw_scale < 10000: return int(math.ceil(raw_scale / 1000) * 1000)
    if raw_scale < 100000: return int(math.ceil(raw_scale / 10000) * 10000)
    return int(math.ceil(raw_scale / 100000) * 100000)

@contextmanager
def _edit_session(workspace: str):
    """Context manager for handling Enterprise or File GDB edit sessions."""
    editor = arcpy.da.Editor(workspace)
    editor.startEditing(False, True)
    editor.startOperation()
    try:
        yield
        editor.stopOperation()
        editor.stopEditing(True)
    except Exception as e:
        editor.stopOperation()
        editor.stopEditing(False)
        raise e

def main(input_layer: str):
    arcpy.env.overwriteOutput = True
    aprx = arcpy.mp.ArcGISProject("CURRENT")

    # 1. Initialize Layout Dimensions
    arcpy.AddMessage("Analyzing layout dimensions...")
    p_w_mm, p_h_mm = _find_mapframe_size_mm(aprx, PORTRAIT_LAYOUT_NAME)
    l_w_mm, l_h_mm = _find_mapframe_size_mm(aprx, LANDSCAPE_LAYOUT_NAME)

    # 2. Describe and Validate Input
    desc = arcpy.Describe(input_layer)
    if desc.shapeType.lower() != "polygon":
        arcpy.AddError("Input must be a Polygon feature layer.")
        return

    sr = desc.spatialReference
    if sr.type != "Projected":
        arcpy.AddError("Layer must be in a Projected Coordinate System (Linear units).")
        return

    # 3. Add Fields if missing
    existing_fields = [f.name.upper() for f in arcpy.ListFields(input_layer)]
    if "LAYOUT" not in existing_fields:
        arcpy.management.AddField(input_layer, "LAYOUT", "TEXT", field_length=1)
    if "PAGE_SCALE" not in existing_fields:
        arcpy.management.AddField(input_layer, "PAGE_SCALE", "LONG")

    # 4. Processing Logic
    arcpy.AddMessage(f"Calculating best-fit for {desc.name}...")
    workspace = desc.path
    
    # Foot to Meter conversion factor if applicable
    unit_factor = 1.0
    if "FOOT" in sr.linearUnitName.upper():
        unit_factor = 0.30480060960121924 if "US" in sr.linearUnitName.upper() else 0.3048

    with _edit_session(workspace):
        with arcpy.da.UpdateCursor(input_layer, ["SHAPE@", "LAYOUT", "PAGE_SCALE"]) as cursor:
            for row in cursor:
                ext = row[0].extent
                w_m = float(abs(ext.XMax - ext.XMin)) * unit_factor
                h_m = float(abs(ext.YMax - ext.YMin)) * unit_factor

                s_p = _best_fit_scale(w_m, h_m, p_w_mm, p_h_mm, MARGIN_PCT)
                s_l = _best_fit_scale(w_m, h_m, l_w_mm, l_h_mm, MARGIN_PCT)

                # Determine most efficient orientation (the one with the smaller scale fits better)
                if s_p <= s_l:
                    row[1], row[2] = 'P', s_p
                else:
                    row[1], row[2] = 'L', s_l
                
                cursor.updateRow(row)

    arcpy.AddMessage("Success: LAYOUT and PAGE_SCALE fields updated.")

if __name__ == "__main__":
    # Param 0: Input Polygon Layer
    target_lyr = arcpy.GetParameterAsText(0)
    if not target_lyr:
        arcpy.AddError("No input layer provided.")
    else:
        main(target_lyr)
