import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QTableWidget, QTableWidgetItem, QTabWidget, QWidget)
from PyQt5.QtCore import Qt
import numpy as np

class BufferStatsDialog(QDialog):
    def __init__(self, buffer_statistics, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Buffer Analysis Statistics")
        self.resize(800, 600)

        self.setWindowFlags(self.windowFlags() | Qt.WindowMinimizeButtonHint)
        
        # Main layout
        main_layout = QVBoxLayout()
        
        # Create tab widget
        tab_widget = QTabWidget()
        
        # Create tabs
        pie_chart_tab = QWidget()
        details_tab = QWidget()
        
        # Pie Chart Tab Layout
        pie_chart_layout = QVBoxLayout()
        
        # Create matplotlib figure
        plt.close('all')  # Close any existing figures
        fig, ax = plt.subplots(figsize=(10, 7))
        
        # Prepare data for pie chart
        labels = []
        sizes = []
        for i, stat in enumerate(buffer_statistics):
            # Create labels that include buffer number, points, and percentage
            label = f"Buffer {i+1}\n{stat['point_count']} pts\n({stat['percentage']:.1f}%)"
            labels.append(label)
            sizes.append(stat['percentage'])
        
        # Color palette
        colors = plt.cm.Spectral(np.linspace(0, 1, len(labels)))
        
        # Create pie chart with custom labeling
        wedges, texts, autotexts = ax.pie(
            sizes, 
            labels=labels, 
            colors=colors,
            labeldistance=1.15,  # Increase distance of labels from pie
            pctdistance=0.85,    # Position of percentage text
            wedgeprops={'edgecolor': 'white', 'linewidth': 1},
            textprops={'fontsize': 8, 'fontweight': 'bold'},
            autopct='%1.1f%%'
        )
        
        ax.set_title('Point Distribution Across Buffers', fontsize=14, fontweight='bold')
        
        # Create canvas and add to layout
        canvas = FigureCanvas(fig)
        pie_chart_layout.addWidget(canvas)
        pie_chart_tab.setLayout(pie_chart_layout)
        
        # Rest of the code remains the same as in the previous implementation...
        
        # Details Tab Layout
        details_layout = QVBoxLayout()
        
        # Summary Statistics
        summary_label = QLabel("Summary Statistics")
        summary_label.setStyleSheet("font-weight: bold; font-size: 16px;")
        details_layout.addWidget(summary_label)
        
        # Calculate summary statistics
        total_points = sum(stat['point_count'] for stat in buffer_statistics)
        max_buffer = max(buffer_statistics, key=lambda x: x['point_count'])
        max_buffer_index = buffer_statistics.index(max_buffer) + 1
        
        if buffer_statistics:
            max_buffer = max(buffer_statistics, key=lambda x: x['point_count'])
            max_buffer_index = buffer_statistics.index(max_buffer) + 1

            summary_text = (
                f"Total Points: {sum(stat['point_count'] for stat in buffer_statistics)}\n"
                f"Number of Buffers: {len(buffer_statistics)}\n"
                f"Buffer with Most Points: Buffer {max_buffer_index}\n"
                f"Highest Point Concentration: {max_buffer['percentage']:.2f}% "
                f"({max_buffer['point_count']} points)"
         )
        else:
            summary_text = "No buffer statistics available."
        summary_stats_label = QLabel(summary_text)
        details_layout.addWidget(summary_stats_label)
        
        # Detailed Buffer Breakdown Table
        table = QTableWidget()
        table.setColumnCount(4)
        table.setHorizontalHeaderLabels(["Buffer", "Distance", "Points", "Percentage"])
        table.setRowCount(len(buffer_statistics))
        
        for row, stat in enumerate(buffer_statistics):
            table.setItem(row, 0, QTableWidgetItem(f"Buffer {row+1}"))
            table.setItem(row, 1, QTableWidgetItem(f"{stat['buffer_distance']:.2f}"))
            table.setItem(row, 2, QTableWidgetItem(str(stat['point_count'])))
            table.setItem(row, 3, QTableWidgetItem(f"{stat['percentage']:.2f}%"))
        
        details_layout.addWidget(table)
        details_tab.setLayout(details_layout)
        
        # Add tabs to tab widget
        tab_widget.addTab(pie_chart_tab, "Pie Chart")
        tab_widget.addTab(details_tab, "Details")
        
        # Add tab widget to main layout
        main_layout.addWidget(tab_widget)
        
        # Set the layout
        self.setLayout(main_layout)