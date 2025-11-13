#!/usr/bin/env python
# -*- coding: utf-8 -*-

# original creator: James Huang <elastic192@gmail.com>
# https://elastic192.blogspot.com/
# ported by: Ingegneus

import gi
gi.require_version('Gimp', '3.0')
from gi.repository import Gimp
gi.require_version('GimpUi', '3.0')
from gi.repository import GimpUi
from gi.repository import GObject, GLib, Gtk, Gio
import sys, os, string, tempfile, platform

def hide_other_layers(all_layers, this_layer):
    for layer in all_layers:
        layer.set_visible(False)
        if layer == this_layer:
            layer.set_visible(True)

def remove_background(procedure, run_mode, image, drawables, config, run_data):
    """
    Remove the background from an image using an AI model.
    
    Parameters:
        image (gimp.Image): The active image in GIMP.
        drawable (gimp.Drawable): The active layer or drawable in GIMP.
        as_mask (bool): Whether to return the result as a mask.
        selModel (int): The index of the AI model from tupleModel to use for background removal.
        AlphaMatting (bool): Whether to use alpha matting for more refined edges.
        aeValue (int): Alpha Matting Erode Size, used when AlphaMatting is enabled.
    """

    GimpUi.init("remove_background")  
    dialog = GimpUi.ProcedureDialog.new(procedure, config, "Configure Plugin") 
    dialog.fill(["model", "as-mask", "alpha-matting", "alpha-matting-erode-size"])

    if not dialog.run():
        dialog.destroy()
        return procedure.new_return_values(Gimp.PDBStatusType.CANCEL, None)
    dialog.destroy()

    model = config.get_property("model")
    as_mask = config.get_property("as-mask")
    alpha_matting = config.get_property("alpha-matting")
    alpha_matting_erode_size = config.get_property("alpha-matting-erode-size")
   
    # Initial setup and paths
    remove_tmp_file = True       # Whether to remove the temporary files after processing
    output_message = True      # Whether to output debug messages
    os_name = platform.system() # Detect the operating system
    export_sep = os.sep         # OS-specific file path separator
    tmpdir = tempfile.gettempdir()  # Get the temporary directory for file storage
    
    # File paths for intermediate files
    input_png_path = os.path.join(tmpdir, "tmp-gimp-in.png")
    input_png_file = Gio.File.new_for_path(input_png_path)
    output_png_path = os.path.join(tmpdir, "tmp-gimp-out.png")
    output_png_file = Gio.File.new_for_path(output_png_path)
    error_log_path = os.path.join(tmpdir, "err-msg.txt")
    error_log_file = Gio.File.new_for_path(error_log_path)

    # Get the active layer and its offset
    image.undo_group_start()  # Begin the undo group
    selected_layers = Gimp.Image.get_selected_layers(image)

    for current_layer in selected_layers:
        ret, x1, y1 = current_layer.get_offsets()  # Get the layer's position offsets
        
        # Save the image as PNG if no selection exists, otherwise, save only the selection
        if Gimp.Selection.is_empty(image):
            hide_other_layers(image.get_layers(), current_layer)
            
            Gimp.file_save(Gimp.RunMode.NONINTERACTIVE, 
                           image, 
                           input_png_file, 
                           None)
        else:
            # Save only the selected portion as PNG
            Gimp.edit_copy(drawable)
            non_empty, x1, y1, x2, y2 = Gimp.Selection.bounds(image)
            tmp_image = Gimp.Image(x2 - x1, y2 - y1, 0)
            tmp_drawable = gimp.Layer(tmp_image, "Temp", tmp_image.get_width(), tmp_image.get_height(), RGB_IMAGE, 100, NORMAL_MODE)
            Gimp.Image.add_layer(image, tmp_drawable, 0)
            
            # Fill with Leopard pattern and paste the selection
            pat = Gimp.context.get_pattern()
            Gimp.context.set_pattern("Leopard")
            Gimp.Drawable.fill(tmp_drawable, 4)
            Gimp.context.set_pattern(pat)
            Gimp.floating_sel_anchor(Gimp.edit_paste(tmp_drawable, TRUE))
            
            # Save the temp image as PNG
            Gimp.file_save(Gimp.RunMode.NONINTERACTIVE, 
                           image, 
                           input_png_file, 
                           None)
            Gimp.Image.delete(tmp_image)
        
        # Path to the rembg executable (adjust path as necessary)
        rembg_bin = "/home/matteo/.pyenv/versions/3.12.12/envs/rembg-env/bin/rembg"
        if output_message:
            Gimp.message("rembg binary: " + rembg_bin)
        
        # Option for Alpha Matting (optional)
        option = ""
        if alpha_matting:
            option = "-a -ae %d" % alpha_matting_erode_size
        
        # Build the command to run the AI background remover
        cmd = '"%s" i -m %s %s "%s" "%s"' % (rembg_bin, model, option, input_png_path, output_png_path)
        print(cmd)
        if output_message:
            Gimp.message("cmd: " + cmd)
        
        # Execute the command and check for errors
        ret = os.system(cmd + ' 2> ' + error_log_path)
        
        # If an error message was produced, read and display it
        if output_message:
            Gimp.message("cmd out: " + str(ret))   
            if os.path.exists(error_log_file):
                with open(error_log_path, "r") as fp:
                    output = fp.read()
                if output:
                    Gimp.message(output)
                os.remove(error_log_file)

        # If the background was successfully removed, load the result as a new layer
        if os.path.exists(output_png_path):
            new_layer = Gimp.file_load_layer(Gimp.RunMode.NONINTERACTIVE, image, output_png_file)
            image.insert_layer(new_layer, None,  -1)
            Gimp.Layer.set_offsets(new_layer, x1, y1)
            
            # If as_mask is selected, use the result as a mask
            if as_mask:
                pdb.gimp_image_select_item(image, CHANNEL_OP_REPLACE, new_layer)
                image.remove_layer(new_layer)
                copyLayer = pdb.gimp_layer_copy(current_layer, TRUE)
                image.add_layer(copyLayer, -1)
                mask = copyLayer.create_mask(ADD_SELECTION_MASK)
                copyLayer.add_mask(mask)
                pdb.gimp_selection_none(image)

    # End the undo group and refresh the display
    image.undo_group_end()
    Gimp.displays_flush()
    GLib.free()

    # Clean up temporary files if required
    if remove_tmp_file:
        if os_name == "Windows":
            del_command = "del " + input_png_path
            del_command = "del " + output_png_path
        else:
            del_command = "rm " + input_png_path
            del_command = "rm " + output_png_path
        os.system(del_command)

    return 0


class RemoveBGPlugIn(Gimp.PlugIn):

    def do_query_procedures(self):
        return ["python-fu-remove-background"]

    def do_create_procedure(self, name):
        if name != "python-fu-remove-background":
            return None

        procedure = Gimp.ImageProcedure.new(self, 
                                            name,
                                            Gimp.PDBProcType.PLUGIN,
                                            remove_background, 
                                            None)

        procedure.set_image_types("RGB*")
        procedure.set_sensitivity_mask(Gimp.ProcedureSensitivityMask.ALWAYS)
        procedure.set_menu_label("Remove Background")
        procedure.set_attribution("Ingegneus", "Ingegneus", "2025")
        procedure.add_menu_path("<Image>/Filters")
        procedure.set_documentation(
            "Remove layer background with AI",
            "Remove layer background using the rembg python library",
            None)

        procedure.add_boolean_argument("as-mask", "As Mask", "Remove the background as Mask", False, GObject.ParamFlags.READWRITE)
        procedure.add_boolean_argument("alpha-matting", "Alpha Matting", "???", False, GObject.ParamFlags.READWRITE)
        procedure.add_double_argument("alpha-matting-erode-size", "Alpha Matting Erode Size", "???",1,100, 15, GObject.ParamFlags.READWRITE)

        options = Gimp.Choice.new()
        Gimp.Choice.add(options, "u2net", 0, "u2net", "A pre-trained model for general use cases.") 
        Gimp.Choice.add(options, "u2netp", 1, "u2netp", "A lightweight version of u2net model.")
        Gimp.Choice.add(options, "u2net_human_seg", 2, "u2net_human_seg", "A pre-trained model for human segmentation.") 
        Gimp.Choice.add(options, "u2net_cloth_seg", 3, "u2net_cloth_seg", "A pre-trained model for Cloths Parsing from human portrait. Here clothes are parsed into 3 category: Upper body, Lower body and Full body.")
        Gimp.Choice.add(options, "silueta", 4, "silueta", "Same as u2net but the size is reduced to 43Mb.")
        Gimp.Choice.add(options, "isnet-general-use", 5, "isnet-general-use", "A new pre-trained model for general use cases.") 
        Gimp.Choice.add(options, "isnet-anime", 6, "isnet-anime", "A high-accuracy segmentation for anime character.")
        Gimp.Choice.add(options, "sam", 7, "sam", "A pre-trained model for any use cases.") 
        Gimp.Choice.add(options, "birefnet-general", 8, "birefnet-general", "A pre-trained model for general use cases.") 
        Gimp.Choice.add(options, "birefnet-general-lite", 9, "birefnet-general-lite", "A light pre-trained model for general use cases.") 
        Gimp.Choice.add(options, "birefnet-portrait", 10, "birefnet-portrait", "A pre-trained model for human portraits.") 
        Gimp.Choice.add(options, "birefnet-dis", 11, "birefnet-dis", "A pre-trained model for dichotomous image segmentation (DIS).") 
        Gimp.Choice.add(options, "birefnet-hrsod", 12, "birefnet-hrsod", "A pre-trained model for high-resolution salient object detection (HRSOD).") 
        Gimp.Choice.add(options, "birefnet-cod", 13, "birefnet-cod", "A pre-trained model for concealed object detection (COD).") 
        Gimp.Choice.add(options, "birefnet-massive", 14, "birefnet-massive", " A pre-trained model with massive dataset.") 
        Gimp.Choice.add(options, "ben2-base", 15, "ben2-base", "Introduces a novel approach to foreground segmentation through its innovative Confidence Guided Matting (CGM) pipeline.") 
        Gimp.Choice.add(options, "bria-rmbg", 16, "bria-rmbg", "A pretrained model with excellent outputs") 

        procedure.add_choice_argument("model", "Model", "Choose the AI model to use",
                                      options, "birefnet-general", GObject.ParamFlags.READWRITE)
        
        return procedure

    
# Plugin entry point
Gimp.main(RemoveBGPlugIn.__gtype__, sys.argv)

