import datetime
import sys
from lxml import html
import requests
from PyQt5.QtCore import QSize
import resources
from googleapiclient.discovery import build
from PyQt5 import QtCore, uic
from PyQt5.QtWidgets import *


class MainWindow(QMainWindow):

    def getService(self):
        service = build("customsearch", "v1",
                        developerKey="AIzaSyC4kDelotzwM_L8VxbZ68InOIIFa3_epE4")

        return service

    def update_label(self):
        current_time = str(datetime.datetime.now().strftime("%H:%M\n%a, %d %b"))
        self.timeLabel.setText(current_time)

    def search_recipes(self):
        search_value = self.searchInput.text()
        service = self.getService()
        response = service.cse().list(
            q=search_value,
            cx="006492090401638723872:ovfp61qkljo",
            lr="lang_el"
        ).execute()
        items = response.get("items")
        if items is None:
            listItem = QListWidgetItem("Δεν υπήρξαν αποτελέσματα")
            self.searchResultsList.addItem(listItem)
        else :
            for item in items:
                listItem = QListWidgetItem(item.get("title"))
                listItem.setData(32, item.get("link"))
                listItem.setSizeHint(QSize(50, 50))
                self.searchResultsList.addItem(listItem)

    def show_recipe(self, curr):
        page = requests.get(curr.data(32))
        tree = html.fromstring(page.content)
        print(page.content)
        ingredients = tree.cssselect(".ingredients-list")
        print(ingredients)

    def __init__(self):
        super(self.__class__, self).__init__()

        uic.loadUi('mainwindow.ui', self)

        self.timer = QtCore.QTimer(self)
        self.timer.setInterval(1000)
        self.timer.timeout.connect(lambda: self.update_label())
        self.timer.start()

        self.searchBtn.clicked.connect(self.search_recipes)
        self.searchResultsList.currentItemChanged.connect(self.show_recipe)


def main():
    app = QApplication(sys.argv)
    form = MainWindow()
    form.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
