import datetime
import sys
from lxml import html
import requests
from PyQt5.QtCore import QSize
import resources
from googleapiclient.discovery import build
from PyQt5 import QtCore, uic, QtWidgets
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
        self.searchResultsList.clear()
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
        else:
            for item in items:
                listItem = QListWidgetItem(item.get("title"))
                listItem.setData(32, item.get("link"))
                listItem.setSizeHint(QSize(50, 50))
                self.searchResultsList.addItem(listItem)

    def show_recipe(self, curr):
        if curr is None:
            return
        page = requests.get(curr.data(32))
        tree = html.fromstring(page.text)
        ingredientSections = tree.cssselect(".ingredients-list p")
        ingredients = tree.cssselect(".ingredients-list ul")
        method_steps = tree.cssselect(".recipe-main .method .text ul")
        title = tree.cssselect(".recipe .title")
        ingredient_text = ""
        method_text = ""
        title_text = title[0].text

        if ingredientSections:
            if len(ingredients) > len(ingredientSections):
                for ingredient in ingredients[0]:
                    ingredient_text += ingredient.text_content()
                    ingredient_text += "\n"
                for idx, section in enumerate(ingredientSections):
                    ingredient_text += "\n"
                    ingredient_text += ingredientSections[idx].text_content()
                    ingredient_text += "\n"
                    for ingredient in ingredients[idx + 1]:
                        ingredient_text += ingredient.text_content()
                        ingredient_text += "\n"
            else:
                for idx, section in enumerate(ingredientSections):
                    ingredient_text += "\n"
                    ingredient_text += ingredientSections[idx].text_content()
                    ingredient_text += "\n"
                    for ingredient in ingredients[idx]:
                        ingredient_text += ingredient.text_content()
                        ingredient_text += "\n"
        else:
            for ingredient in ingredients[0]:
                ingredient_text += ingredient.text_content()
                ingredient_text += "\n"

        for step in method_steps[0]:
            method_text += step.text_content()
            method_text += "\n"

        self.recipeIngredients.setPlainText(ingredient_text)
        self.recipeIngredients.verticalScrollBar().triggerAction(QScrollBar.SliderToMinimum)
        self.recipeInstructions.setPlainText(method_text)
        self.recipeIngredients.verticalScrollBar().triggerAction(QScrollBar.SliderToMinimum)
        self.recipeTitle.setText(title_text)
        self.recipeDock.show()

    def __init__(self):
        super(self.__class__, self).__init__()

        uic.loadUi('mainwindow.ui', self)

        self.timer = QtCore.QTimer(self)
        self.timer.setInterval(1000)
        self.timer.timeout.connect(lambda: self.update_label())
        self.timer.start()

        self.searchBtn.clicked.connect(self.search_recipes)
        self.searchBtn.setAutoDefault(True)
        self.searchInput.returnPressed.connect(self.searchBtn.click)
        self.searchResultsList.currentItemChanged.connect(self.show_recipe)


def main():
    app = QApplication(sys.argv)
    form = MainWindow()
    form.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
