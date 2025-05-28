from qgis.PyQt import uic
from qgis.PyQt.QtWidgets import QDialog, QMessageBox
from qgis.core import QgsProject, QgsVectorLayer, QgsField, QgsFeature, QgsGeometry, QgsExpression, QgsFeatureRequest
from qgis.PyQt.QtCore import QVariant
from .myMapReader import MyMapReader, MyLine
from openlr import binary_decode
from openlr_dereferencer import decode
from typing import cast
import os
import logging

# ロギング設定
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# 相対パスを絶対パスに変換
FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), 'OpenLRDecoder_dialog_base.ui'))

class OpenLRDecoderDialog(QDialog, FORM_CLASS):
    def __init__(self, parent=None):
        super(OpenLRDecoderDialog, self).__init__(parent)
        self.setupUi(self)

        self.decodeButton.setEnabled(False)
        self.connectButton.clicked.connect(self.connect_to_db)
        self.decodeButton.clicked.connect(self.decode)

    def connect_to_db(self):
        user = self.userLineEdit.text()
        password = self.passwordLineEdit.text()
        dbname = self.dbNameLineEdit.text()
        try:
            self.map_reader = MyMapReader(user=user, password=password, dbname=dbname)
            QMessageBox.information(self, "Connection", "Connected successfully!")
            self.decodeButton.setEnabled(True)
        except Exception as e:
            logger.error(f"Failed to connect: {e}", exc_info=True)
            QMessageBox.critical(self, "Connection", f"Failed to connect: {e}")

    def decode(self):
        encoded_locations = self.encodedLocationTextEdit.toPlainText().splitlines()
        decoded_location = self.decode_locations(encoded_locations)
        self.decodedLocationTextEdit.setPlainText(decoded_location)
        self.add_lines_to_map(self.decoded_lines)

    def decode_locations(self, encoded_locations):
        result_str = ""
        self.decoded_lines = []
        try:
            for encoded_location in encoded_locations:
                if encoded_location.strip():
                    ref = binary_decode(encoded_location.strip())
                    res = decode(reference=ref, reader=self.map_reader)
                    for r in res.lines:
                        tmp = cast(MyLine, r)
                        result_str += f"ID: {tmp.id}, FRC: {tmp.frc}, FOW: {tmp.fow}, Length: {tmp.length}\n"
                        self.decoded_lines.append(tmp)
            return result_str
        except Exception as e:
            logger.error(f"Decoding error: {e}", exc_info=True)
            QMessageBox.critical(self, "Decoding Error", f"An error occurred during decoding: {e}")
            return ""

    def add_lines_to_map(self, lines):
        try:
            project = QgsProject.instance()
            roads_layer = project.mapLayersByName('roads')[0]
            crs = roads_layer.crs()  # roadsレイヤーのCRSを取得

            # 新しいベクターレイヤーを作成
            layer = QgsVectorLayer("LineString?crs=" + crs.authid(), "Decoded OpenLR Lines", "memory")
            provider = layer.dataProvider()

            # フィールドを追加
            provider.addAttributes([
                QgsField("ID", QVariant.Int),
                QgsField("FRC", QVariant.String),
                QgsField("FOW", QVariant.String),
                QgsField("Length", QVariant.Double)
            ])
            layer.updateFields()

            # フィーチャーを追加
            for line in lines:
                query = QgsExpression(f'"id" = {line.id}')
                request = QgsFeatureRequest(query)
                for feature in roads_layer.getFeatures(request):
                    new_feature = QgsFeature()
                    new_feature.setGeometry(feature.geometry())
                    new_feature.setAttributes([line.id, str(line.frc), str(line.fow), line.length])
                    provider.addFeature(new_feature)

            # レイヤーを地図に追加
            QgsProject.instance().addMapLayer(layer)
        except Exception as e:
            logger.error(f"Error adding lines to map: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"An error occurred while adding lines to the map: {e}")
