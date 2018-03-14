import http.client
import os

import requests
from PyQt5.QtGui import QPixmap
import resources
import keyboardlineedit
import datetime
import json
import sys
import configparser
from lxml import html
from PyQt5.QtCore import QSize, QCoreApplication
from googleapiclient.discovery import build
from PyQt5 import QtCore, uic
from PyQt5.QtWidgets import *
from darksky import forecast
from slackclient import SlackClient

if getattr(sys, 'frozen', False):
    # we are running in a bundle
    bundle_dir = sys._MEIPASS
else:
    # we are running in a normal Python environment
    bundle_dir = os.path.dirname(os.path.abspath(__file__))

configpath = 'config'
configParser = configparser.RawConfigParser()
configParser.read(configpath)

guipath = os.path.join(bundle_dir, 'mainwindow.ui')
jsonpath = os.path.join(bundle_dir, 'season_items.json')
iconspath = os.path.join(bundle_dir, 'icons/')
translationpath = os.path.join(bundle_dir, 'translations/' + configParser.get('general', 'lang') + '.qm')


class MainWindow(QMainWindow):
    last_glympse = ("", False)

    def getService(self):
        service = build("customsearch", "v1",
                        developerKey=configParser.get('recipes', 'developer_key'))

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
            cx=configParser.get('recipes', 'cx'),
            lr="lang_" + configParser.get('general', 'lang')
        ).execute()
        items = response.get("items")
        if items is None:
            listItem = QListWidgetItem(QCoreApplication.translate("main", "No recipes found"))
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
        data = json.load(open(jsonpath))
        self.seasonItems.setPlainText(data[index])

    def set_weather(self):
        weather = forecast(configParser.get('weather', 'key'), configParser.get('weather', 'latitude'),
                           configParser.get('weather', 'longitude'), units="si",
                           lang=configParser.get('general', 'lang'))
        weather_text = "{:.1f}".format(weather.temperature) + "°C\n"
        weather_icon = QPixmap(iconspath + weather.icon + ".png")
        self.weatherIconLabel.setPixmap(weather_icon)
        self.weatherIconLabel.setScaledContents(True)
        self.weatherLabel.setText(weather_text)
        self.weatherSummaryLabel.setText(weather.daily[0].summary)

    def set_season_items(self):
        month = datetime.datetime.now().month - 1
        self.show_season_items(month)

    def get_glympse_code(self):
        if self.last_glympse[1]:
            return self.last_glympse[0]

        sc = SlackClient(configParser.get("slack", "token"))
        resp = sc.api_call("groups.history", channel=configParser.get("slack", "channel"), count=1)
        if not resp["ok"]:
            return

        message = resp["messages"][0]
        if "attachments" not in message:
            return self.last_glympse[0]
        link = message["attachments"][0]["title_link"]
        code = link[-9:]
        if code == self.last_glympse[0]:
            return self.last_glympse[0]

        self.last_glympse = (code, True)

        return code

    def set_glympse(self, glympse_code):
        if not self.last_glympse[1]:
            self.glympseLabel.setText(QCoreApplication.translate("main", "No known routes"))
            return
        conn = http.client.HTTPConnection("api.glympse.com")
        headers = {
            'Content-Type': "application/json",
            'Authorization': "Bearer " + configParser.get("glympse", "oauth_key"),
            'Cache-Control': "no-cache"
        }
        conn.request("GET", "/v2/invites/" + glympse_code, headers=headers)
        res = conn.getresponse()
        data = res.read().decode("utf-8")
        data = json.loads(data)
        eta = None
        now = datetime.datetime.now()
        if data["result"] == "failure":
            self.glympseLabel.setText(QCoreApplication.translate("main", "No known routes"))
            self.last_glympse = (glympse_code, False)
            return
        for property in data["response"]["properties"]:
            if property["n"] == "eta":
                eta = now + datetime.timedelta(0, property["v"]["eta"] / 1000)
        if eta is None or eta < now:
            self.glympseLabel.setText(QCoreApplication.translate("main", "No known routes"))
            self.last_glympse = (glympse_code, False)
        else:
            eta_formatted = eta.strftime("%H:%M")
            self.glympseLabel.setText(QCoreApplication.translate("main", "ETA") + ": " + eta_formatted)
            self.last_glympse = (glympse_code, True)

    def __init__(self):
        super(self.__class__, self).__init__()

        uic.loadUi(guipath, self)

        self.set_datetime()
        self.set_weather()
        self.set_season_items()
        self.set_glympse(self.get_glympse_code())

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

        self.glympse_timer = QtCore.QTimer(self)
        self.glympse_timer.setInterval(60000)
        self.glympse_timer.timeout.connect(lambda: self.set_glympse(self.get_glympse_code()))
        self.glympse_timer.start()

        self.searchBtn.clicked.connect(self.search_recipes)
        self.searchBtn.setAutoDefault(True)
        self.searchInput.returnPressed.connect(self.searchBtn.click)
        self.searchResultsList.currentItemChanged.connect(self.show_recipe)

        self.seasonMonthSelect.currentIndexChanged.connect(self.show_season_items)
        self.seasonMonthSelect.setCurrentIndex(datetime.datetime.now().month - 1)


def main():
    app = QApplication(["Quzin"])
    translator = QtCore.QTranslator()
    translator.load(translationpath)
    app.installTranslator(translator)
    form = MainWindow()
    form.showMaximized()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
