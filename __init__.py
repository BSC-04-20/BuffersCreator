# -*- coding: utf-8 -*-
"""
/***************************************************************************
 BufferingClass
                                 A QGIS plugin
 This plugin is meant to develop buffers 
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                             -------------------
        begin                : 2024-11-29
        copyright            : (C) 2024 by BitCoders
        email                : tupomojoo@gmail.com
        git sha              : $Format:%H$
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
 This script initializes the plugin, making it known to QGIS.
"""


# noinspection PyPep8Naming
def classFactory(iface):  # pylint: disable=invalid-name
    """Load BufferingClass class from file BufferingClass.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    #
    from .geo_buffers import BufferingClass
    return BufferingClass(iface)