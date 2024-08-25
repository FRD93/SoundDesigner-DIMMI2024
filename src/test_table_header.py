import sys
from PyQt6.QtWidgets import QApplication, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget

if __name__ == "__main__":
	app = QApplication(sys.argv)

	# Create QTableWidget
	table = QTableWidget()
	table.setRowCount(3)
	table.setColumnCount(4)

	# Set different header labels for each column
	column_labels = ["Column 1", "Column 2", "Column 3", "Column 4"]
	table.setHorizontalHeaderLabels(column_labels)

	# Fill in some data just for demonstration
	for row in range(table.rowCount()):
		for col in range(table.columnCount()):
			item = QTableWidgetItem(f"Row {row}, Col {col}")
			table.setItem(row, col, item)

	# Create a layout and a widget to contain the table
	layout = QVBoxLayout()
	layout.addWidget(table)
	widget = QWidget()
	widget.setLayout(layout)
	widget.setWindowTitle('QTableWidget with Different Column Names')
	widget.show()

	sys.exit(app.exec())
