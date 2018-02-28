from PyQt5.QtGui import QPixmap

LEIDSCHENVEEN = "5cc8dc652542c04e6c0ea0e08e0bef72", 52.067357, 4.403365
KALAMATA = "5cc8dc652542c04e6c0ea0e08e0bef72", 37.042237, 22.114126

import datetime
import json
import sys
from lxml import html
import requests
from PyQt5.QtCore import QSize
from googleapiclient.discovery import build
from PyQt5 import QtCore, uic
from PyQt5.QtWidgets import *
from darksky import forecast


class MainWindow(QMainWindow):

    def getService(self):
        service = build("customsearch", "v1",
                        developerKey="AIzaSyC4kDelotzwM_L8VxbZ68InOIIFa3_epE4")

        return service

    def set_datetime(self):
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

    def show_season_items(self, index):
        data = json.load(open("season_items.json"))
        self.seasonItems.setPlainText(data[index])
        
    def set_weather(self):
        weather = forecast(*LEIDSCHENVEEN, units="si", lang="el")
        weather_text = "{:.1f}".format(weather.temperature) + "°C"
        weather_icon = QPixmap("icons/" + weather.icon + ".png")
        print(weather.icon)
        self.weatherIconLabel.setPixmap(weather_icon)
        self.weatherIconLabel.setScaledContents(True)
        self.weatherLabel.setText(weather_text)
        self.weatherLabel.setToolTip(weather.daily[0].summary)

    def set_season_items(self):
        month = datetime.datetime.now().month - 1
        self.show_season_items(month)

    def __init__(self):
        super(self.__class__, self).__init__()

        uic.loadUi("mainwindow.ui", self)

        self.set_datetime()
        self.set_weather()
        self.set_season_items()

        self.datetime_timer = QtCore.QTimer(self)
        self.datetime_timer.setInterval(60000)
        self.datetime_timer.timeout.connect(lambda: self.set_datetime())
        self.datetime_timer.start()

        self.weather_timer = QtCore.QTimer(self)
        self.weather_timer.setInterval(3600000)
        self.weather_timer.timeout.connect(lambda: self.set_weather())
        self.weather_timer.start()

        self.seasons_timer = QtCore.QTimer(self)
        self.seasons_timer.setInterval(86400000)
        self.seasons_timer.timeout.connect(lambda: self.set_season_items())
        self.seasons_timer.start()

        self.searchBtn.clicked.connect(self.search_recipes)
        self.searchBtn.setAutoDefault(True)
        self.searchInput.returnPressed.connect(self.searchBtn.click)
        self.searchResultsList.currentItemChanged.connect(self.show_recipe)

        self.seasonMonthSelect.currentIndexChanged.connect(self.show_season_items)
        self.seasonMonthSelect.setCurrentIndex(datetime.datetime.now().month - 1)


def main():
    app = QApplication(sys.argv)
    form = MainWindow()
    form.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
