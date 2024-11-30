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
from .buffer_stats import BufferStatsDialog
from qgis.PyQt.QtCore import QSettings, QTranslator, QCoreApplication, QVariant
from qgis.core import Qgis, QgsVectorLayer, QgsFeature, QgsProject, QgsGeometry,QgsWkbTypes, QgsSymbol, QgsSimpleFillSymbolLayer, QgsField, QgsPalLayerSettings,QgsVectorLayerSimpleLabeling, QgsTextFormat, QgsCoordinateReferenceSystem, QgsPropertyCollection, QgsPalLayerSettings 
from qgis.PyQt.QtGui import QIcon, QColor
from qgis.PyQt.QtWidgets import QAction, QFileDialog
from PyQt5.QtCore import Qt
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

    def get_db_connection(self):
        conn = psycopg2.connect(
            dbname='buffering_db',
            user='postgres',
            password='',
            host='localhost',
            port='5432'
        )
        return conn

    def get_postgis_layer_names(self):   
        cursor= self.get_db_connection().cursor()
        cursor.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_name NOT IN ('spatial_ref_sys', 'geometry_columns', 'geography_columns');
        """)
        layers = [row[0] for row in cursor.fetchall()]
        self.get_db_connection().close()
        return layers

    def get_table(self, table_name):
        cursor= self.get_db_connection().cursor()
        cursor.execute(f"""
            SELECT * from {table_name}
           """)

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
                ring_count = int(self.dlg.spinBox.value())  # Number of buffer rings
            except ValueError:
                self.iface.messageBar().pushMessage("Error", "Invalid input values", level=Qgis.Critical)
                return

            # Fetch the selected point layer from the database
            selected_table_name = self.dlg.comboBox.currentText()
            conn = self.get_db_connection()
            uri = f"dbname='buffering_db' host='localhost' port='5432' user='postgres' password='' table=\"{selected_table_name}\" (geom)"
            point_layer = QgsVectorLayer(uri, selected_table_name, "postgres")
            if not point_layer.isValid():
                self.iface.messageBar().pushMessage("Error", "Unable to load point layer from database", level=Qgis.Critical)
                return

            # Create a new memory layer for buffers
            buffer_layer = QgsVectorLayer("Polygon?crs=" + current_layer.crs().authid(),
                                          f"Buffers_{current_layer.name()}", "memory")
            buffer_provider = buffer_layer.dataProvider()

            # Add fields for buffer attributes, including a count field
            buffer_provider.addAttributes(current_layer.fields())
            buffer_provider.addAttributes([QgsField("point_count", QVariant.Int)])
            buffer_layer.updateFields()

            # Collect buffer data for statistics
            buffer_statistics = []

            # Calculate total points in the point layer
            total_points = sum(1 for _ in point_layer.getFeatures())
            if total_points == 0:
                self.iface.messageBar().pushMessage("Error", "No points found in the selected point layer", level=Qgis.Critical)
                return

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

                    percentage = (point_count / total_points) * 100 if total_points > 0 else 0

                    buffer_statistics.append({
                        'point_count': point_count,
                        'percentage': percentage,
                        'buffer_distance': buffer_distance
                     })

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
            label_settings.fieldName = 'point_count'  # Use the 'point_count' field for labeling
            label_settings.placement = QgsPalLayerSettings.OverPoint  # Adjust as needed for placement

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

            # Show statistics dialog
            stats_dialog = BufferStatsDialog(buffer_statistics)
            stats_dialog.exec_()

        create_buffers()


    def toggle_widgets(self):
        """Toggle the enabled/disabled state of widgets based on the checkbox state."""
        if self.dlg.checkBox.isChecked():
            # Disable label_2, lineEdit, and pushButton
            self.dlg.label_2.setEnabled(False)
            self.dlg.lineEdit.setEnabled(False)
            self.dlg.pushButton.setEnabled(False)

            # Enable comboBox_2
            self.dlg.comboBox_2.setEnabled(True)
        else:
            # Enable label_2, lineEdit, and pushButton
            self.dlg.label_2.setEnabled(True)
            self.dlg.lineEdit.setEnabled(True)
            self.dlg.pushButton.setEnabled(True)

            # Disable comboBox_2
            self.dlg.comboBox_2.setEnabled(False)


    def load_database_layer(self, table_name):
        """Load a layer from the specified database table."""
        if not table_name:
            return
        # Construct the connection URI for the PostGIS layer
        #conn_info = self.get_db_connection()
        uri = f"dbname='buffering_db' host='localhost' port='5432' user='postgres' password='' table=\"{table_name}\" (geom)"
        
        # Create the vector layer
        point_layer = QgsVectorLayer(uri, table_name, "postgres")
        
        # Check if the layer is valid
        if not point_layer.isValid():
            self.iface.messageBar().pushMessage("Error", f"Unable to load layer {table_name}", level=Qgis.Critical)
            return
        
        # Add the layer to the project
        QgsProject.instance().addMapLayer(point_layer)
        
        # Set the layer as active
        self.iface.setActiveLayer(point_layer)
        
        # Zoom to the layer
        self.iface.zoomToActiveLayer()

    def load_file_layer(self, file_path):
        """Load a layer from the specified file path."""
        if not file_path or not os.path.exists(file_path):
            return
        # Determine the layer type based on file extension
        file_ext = os.path.splitext(file_path)[1].lower()
        
        # Supported file types and their corresponding provider
        file_types = {
            '.shp': 'ogr',
            '.csv': 'delimitedtext',
            '.gpx': 'ogr',
            '.geojson': 'ogr',
            '.kml': 'ogr',
            '.txt': 'delimitedtext'
        }
        
        # Get the appropriate provider
        provider = file_types.get(file_ext)
        
        if not provider:
            self.iface.messageBar().pushMessage("Error", f"Unsupported file type: {file_ext}", level=Qgis.Critical)
            return
        # Construct the layer URI
        if provider == 'delimitedtext':
            # Special handling for delimited text files
            uri = f"file:///{file_path}?type=csv&decimalPoint=.&xField=longitude&yField=latitude&crs=EPSG:4326"
        else:
            # Generic OGR provider URI
            uri = file_path
        # Create the vector layer
        layer_name = os.path.splitext(os.path.basename(file_path))[0]
        file_layer = QgsVectorLayer(uri, layer_name, provider)
        # Check if the layer is valid
        if not file_layer.isValid():
            self.iface.messageBar().pushMessage("Error", f"Unable to load layer {layer_name}", level=Qgis.Critical)
            return
        # Add the layer to the project
        QgsProject.instance().addMapLayer(file_layer)
        
        # Set the layer as active
        self.iface.setActiveLayer(file_layer)
        
        # Zoom to the layer
        self.iface.zoomToActiveLayer()


    def run(self):
        if self.first_start:
            self.first_start = False
            self.dlg = BufferingClassDialog()
            self.dlg.pushButton.clicked.connect(self.get_file_input)
            self.dlg.button_box.clicked.connect(self.generate_buffers)
            self.dlg.checkBox.stateChanged.connect(self.toggle_widgets)
            self.dlg.comboBox_2.currentTextChanged.connect(self.load_database_layer)
            self.dlg.lineEdit.textChanged.connect(self.load_file_layer)

                    # Clear previous items
        self.dlg.comboBox.clear()
        self.dlg.comboBox_2.clear()
        self.dlg.lineEdit.clear()
        self.dlg.lineEdit_2.clear()
        self.dlg.spinBox.setValue(1)  # Reset to default value
        self.dlg.checkBox.setChecked(False)  # Uncheck the checkbox


        layers = self.get_postgis_layer_names()
        self.dlg.comboBox.addItems(layers)
        self.dlg.comboBox_2.addItem("")
        self.dlg.comboBox_2.addItems(layers)
        self.dlg.show()
        result = self.dlg.exec_()
        if result:
            pass