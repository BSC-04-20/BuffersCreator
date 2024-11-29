# -*- coding: utf-8 -*-
"""
/***************************************************************************
 BufferingClass
                                 A QGIS plugin
 This plugin is meant to develop buffers 
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                              -------------------
        begin                : 2024-11-29
        git sha              : $Format:%H$
        copyright            : (C) 2024 by BitCoders
        email                : tupomojoo@gmail.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
from qgis.PyQt.QtCore import QSettings, QTranslator, QCoreApplication, QVariant
from qgis.core import Qgis, QgsVectorLayer, QgsFeature, QgsProject, QgsGeometry,QgsWkbTypes, QgsSymbol, QgsSimpleFillSymbolLayer, QgsField, QgsPalLayerSettings,QgsVectorLayerSimpleLabeling, QgsTextFormat, QgsCoordinateReferenceSystem 
from qgis.PyQt.QtGui import QIcon, QColor
from qgis.PyQt.QtWidgets import QAction, QFileDialog
import psycopg2
import processing

# Initialize Qt resources from file resources.py
from .resources import *
# Import the code for the dialog
from .geo_buffers_dialog import BufferingClassDialog
import os.path


class BufferingClass:
    """QGIS Plugin Implementation."""

    def __init__(self, iface):
        """Constructor."""
        self.iface = iface
        self.plugin_dir = os.path.dirname(__file__)
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'BufferingClass_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)
            QCoreApplication.installTranslator(self.translator)

        self.actions = []
        self.menu = self.tr(u'&GeoBuffers')
        self.first_start = None

    def tr(self, message):
        return QCoreApplication.translate('BufferingClass', message)

    def add_action(
        self,
        icon_path,
        text,
        callback,
        enabled_flag=True,
        add_to_menu=True,
        add_to_toolbar=True,
        status_tip=None,
        whats_this=None,
        parent=None):
        """Add a toolbar icon to the toolbar."""
        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)
        if status_tip is not None:
            action.setStatusTip(status_tip)
        if whats_this is not None:
            action.setWhatsThis(whats_this)
        if add_to_toolbar:
            self.iface.addToolBarIcon(action)
        if add_to_menu:
            self.iface.addPluginToMenu(self.menu, action)
        self.actions.append(action)
        return action

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""
        icon_path = ':/plugins/geo_buffers/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u''),
            callback=self.run,
            parent=self.iface.mainWindow())
        self.first_start = True

    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'&GeoBuffers'),
                action)
            self.iface.removeToolBarIcon(action)

    def get_postgis_layer_names(self):
        conn = psycopg2.connect(
            dbname='buffering_db',
            user='postgres',
            password='',
            host='localhost',
            port='5432'
        )
        cursor = conn.cursor()
        cursor.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_name NOT IN ('spatial_ref_sys', 'geometry_columns', 'geography_columns');
        """)
        layers = [row[0] for row in cursor.fetchall()]
        conn.close()
        return layers

    def get_file_input(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self.iface.mainWindow(),
            "Open File",
            "",
            "All Files (*);;Text Files (*.txt);;CSV Files (*.csv)"
        )
        if file_path:
            self.dlg.lineEdit.setText(file_path)
        else:
            print("No file selected")

    def generate_buffers(self):
        def create_buffers():
            current_layer = self.iface.activeLayer()
            if not current_layer or not isinstance(current_layer, QgsVectorLayer):
                self.iface.messageBar().pushMessage("Error", "Please select a vector layer", level=Qgis.Critical)
                return

            # Get input values
            try:
                base_distance = float(self.dlg.lineEdit_2.text())  # Base buffer distance
                ring_count = int(self.dlg.lineEdit_3.text())  # Number of buffer rings
            except ValueError:
                self.iface.messageBar().pushMessage("Error", "Invalid input values", level=Qgis.Critical)
                return

            # Get the selected point layer from the comboBox
            selected_point_layer_name = self.dlg.comboBox.currentText()
            point_layer = QgsProject.instance().mapLayersByName(selected_point_layer_name)
            if not point_layer:
                self.iface.messageBar().pushMessage("Error", "Selected point layer not found", level=Qgis.Critical)
                return
            point_layer = point_layer[0]

            # Create a new memory layer for buffers
            buffer_layer = QgsVectorLayer("Polygon?crs=" + current_layer.crs().authid(),
                                          f"Buffers_{current_layer.name()}", "memory")
            buffer_provider = buffer_layer.dataProvider()

            # Add fields for buffer attributes, including a count field
            buffer_provider.addAttributes(current_layer.fields())
            buffer_provider.addAttributes([QgsField("point_count", QVariant.Int)])
            buffer_layer.updateFields()

            # Generate buffer rings for each selected feature
            for feature in current_layer.selectedFeatures():
                original_geom = feature.geometry()
                attrs = feature.attributes()

                previous_buffer_geom = None
                for i in range(1, ring_count + 1):
                    buffer_distance = base_distance * i
                    buffered_geom = original_geom.buffer(buffer_distance, 5)

                    # Exclude the area covered by the previous buffer to create an exclusive ring
                    if previous_buffer_geom:
                        buffered_geom = buffered_geom.difference(previous_buffer_geom)

                    # Count points within this exclusive buffer
                    point_count = sum(1 for point in point_layer.getFeatures()
                                      if buffered_geom.contains(point.geometry()))

                    # Create a new feature for this buffer
                    buffer_feature = QgsFeature(buffer_layer.fields())
                    buffer_feature.setGeometry(buffered_geom)
                    buffer_feature.setAttributes(attrs + [point_count])
                    buffer_provider.addFeature(buffer_feature)

                    # Update the previous buffer geometry
                    previous_buffer_geom = original_geom.buffer(buffer_distance, 5)

            # Add the buffer layer to the project
            QgsProject.instance().addMapLayer(buffer_layer)

            # Set a simple visualization with transparency
            symbol = QgsSymbol.defaultSymbol(QgsWkbTypes.PolygonGeometry)
            symbol.setOpacity(0.5)
            buffer_layer.renderer().setSymbol(symbol)
                    # Configure labels for the buffer layer
            label_settings = QgsPalLayerSettings()
            label_settings.fieldName = "point_count"  # Use the 'point_count' field for labeling
            label_settings.placement = QgsPalLayerSettings.OverPoint # Adjust as needed for placement

            text_format = QgsTextFormat()
            text_format.setSize(14)  # Set the font size to 14 (adjust as needed)
            label_settings.setFormat(text_format)

            # Set a white background for the label
            label_settings.backgroundEnabled = True
            label_settings.backgroundColor = QColor(255, 255, 255)  # White background
            label_settings.backgroundOpacity = 0.5 
            
            label_settings.enabled = True

            labeler = QgsVectorLayerSimpleLabeling(label_settings)
            buffer_layer.setLabelsEnabled(True)
            buffer_layer.setLabeling(labeler)
            buffer_layer.triggerRepaint()
            buffer_layer.triggerRepaint()
            self.iface.zoomToActiveLayer()

        create_buffers()

    def run(self):
        if self.first_start:
            self.first_start = False
            self.dlg = BufferingClassDialog()
            self.dlg.pushButton.clicked.connect(self.get_file_input)
            self.dlg.button_box.clicked.connect(self.generate_buffers)

        layers = self.get_postgis_layer_names()
        self.dlg.comboBox.addItems(layers)
        self.dlg.show()
        result = self.dlg.exec_()
        if result:
            pass