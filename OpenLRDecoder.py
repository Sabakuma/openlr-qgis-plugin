from qgis.PyQt.QtWidgets import QAction, QDialog
from qgis.core import QgsProject
from .OpenLRDecoder_dialog import OpenLRDecoderDialog

class OpenLRDecoder:
    def __init__(self, iface):
        self.iface = iface
        self.action = None

    def initGui(self):
        self.action = QAction("OpenLR Decoder", self.iface.mainWindow())
        self.action.triggered.connect(self.run)
        self.iface.addToolBarIcon(self.action)
        self.iface.addPluginToMenu("&OpenLR Decoder", self.action)

    def unload(self):
        self.iface.removeToolBarIcon(self.action)
        self.iface.removePluginMenu("&OpenLR Decoder", self.action)

    def run(self):
        dialog = OpenLRDecoderDialog()
        dialog.exec_()
