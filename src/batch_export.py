# -*- coding: utf-8 -*-
"""
craft_layout: Contextual Batch Exporter
---------------------------------------
Automates the export of ArcGIS Pro Map Series by dynamically switching 
between layouts and applying automated cartographic context.

Features:
- Dual Layout Support: Exports Portrait and Landscape features in a single run.
- Automated Context: Creates a greyed-out background for non-active features.
- Performance: Includes a high-speed Test Mode for layout verification.
"""

import os
import arcpy
import time
from typing import Optional, List

# --- Configuration Defaults ---
PORTRAIT_LAYOUT_NAME = "A3_PORTRAIT"
LANDSCAPE_LAYOUT_NAME = "A3_LANDSCAPE"
LAYOUT_FIELD = "LAYOUT"
PAGE_NAME_FIELD = "REGION"
CONTEXT_TRANSPARENCY = 80  # 0-100%
CONTEXT_COLOR = [130, 130, 130]  # RGB Grey

def _get_map_objects(aprx: arcpy.mp.ArcGISProject, layout_name: str):
    """Safely retrieves layout and its primary map frame."""
    lyt = next((l for l in aprx.listLayouts() if l.name == layout_name), None)
    if not lyt:
        raise RuntimeError(f"Layout '{layout_name}' not found.")
    
    mfs = lyt.listElements("MAPFRAME_ELEMENT")
    if not mfs:
        raise RuntimeError(f"Layout '{layout_name}' has no map frames.")
    
    return lyt, mfs[0]

def _create_context_layer(map_obj: arcpy.mp.Map, source_lyr: arcpy.mp.Layer):
    """Creates a desaturated context layer to highlight the primary feature."""
    desc = arcpy.Describe(source_lyr)
    ctx_lyr = map_obj.addDataFromPath(desc.catalogPath)
    ctx_lyr.name = f"{source_lyr.name}_context_bg"
    
    # Apply Desaturation Symbology
    sym = ctx_lyr.symbology
    if hasattr(sym, 'renderer'):
        try:
            sym.renderer.symbol.color = {'RGB': CONTEXT_COLOR}
            sym.renderer.symbol.outlineColor = {'RGB': [180, 180, 180]}
            ctx_lyr.symbology = sym
        except:
            arcpy.AddWarning("Could not automate context symbology. Using layer default.")
            
    ctx_lyr.transparency = CONTEXT_TRANSPARENCY
    return ctx_lyr

def _export_series(aprx, layout_name, filter_val, output_path, layer_name, page_field, test_mode):
    """Logic for filtering, context-layering, and PDF generation."""
    lyt, mf = _get_map_objects(aprx, layout_name)
    ms = lyt.mapSeries
    
    if not ms or not ms.enabled:
        arcpy.AddWarning(f"Map Series not enabled on {layout_name}. Skipping.")
        return

    idx_lyr = next((l for l in mf.map.listLayers() if l.name == layer_name), None)
    if not idx_lyr:
        raise RuntimeError(f"Index layer '{layer_name}' not found in {layout_name}.")

    orig_query = idx_lyr.definitionQuery
    ctx_lyr = None
    
    try:
        # Filter primary layer to only P or L features
        idx_lyr.definitionQuery = f"{LAYOUT_FIELD} = '{filter_val}'"
        page_count = ms.pageCount
        
        if page_count == 0:
            arcpy.AddMessage(f"No pages for {layout_name}. Skipping.")
            return

        ctx_lyr = _create_context_layer(mf.map, idx_lyr)
        mf.map.moveLayer(idx_lyr, ctx_lyr, "AFTER") # Place behind primary

        arcpy.AddMessage(f"Exporting {layout_name} ({page_count} pages)...")
        pdf_doc = arcpy.mp.PDFDocumentCreate(output_path)
        
        limit = 1 if test_mode else page_count
        res = 150 if test_mode else 300

        for i in range(1, limit + 1):
            ms.currentPageNumber = i
            page_name = ms.pageRow.getValue(page_field)
            
            # Update context to show everything EXCEPT the current page feature
            if isinstance(page_name, str):
                ctx_lyr.definitionQuery = f"{page_field} <> '{page_name.replace('\'','\'\'')}'"
            else:
                ctx_lyr.definitionQuery = f"{page_field} <> {page_name}"
            
            # Allow time for UI refresh in Pro
            if not test_mode: time.sleep(0.5)
            
            temp_pdf = os.path.join(arcpy.env.scratchFolder, f"tmp_{i}.pdf")
            lyt.exportToPDF(temp_pdf, resolution=res)
            pdf_doc.appendPages(temp_pdf)
            os.remove(temp_pdf)

        pdf_doc.saveAndClose()
        arcpy.AddMessage(f"✓ Saved: {output_path}")

    finally:
        idx_lyr.definitionQuery = orig_query
        if ctx_lyr: mf.map.removeLayer(ctx_lyr)

def main():
    # Parameters from Script Tool
    target_lyr_name = arcpy.GetParameterAsText(0) # String name of layer
    out_folder = arcpy.GetParameterAsText(1)
    name_field = arcpy.GetParameterAsText(2) or PAGE_NAME_FIELD
    test_mode = arcpy.GetParameter(3) # Boolean

    aprx = arcpy.mp.ArcGISProject("CURRENT")
    
    if not out_folder:
        out_folder = os.path.dirname(aprx.filePath)

    # 1. Export Portrait
    _export_series(aprx, PORTRAIT_LAYOUT_NAME, "P", 
                  os.path.join(out_folder, f"{target_lyr_name}_A3_Portrait.pdf"),
                  target_lyr_name, name_field, test_mode)

    # 2. Export Landscape
    _export_series(aprx, LANDSCAPE_LAYOUT_NAME, "L", 
                  os.path.join(out_folder, f"{target_lyr_name}_A3_Landscape.pdf"),
                  target_lyr_name, name_field, test_mode)

if __name__ == "__main__":
    main()
