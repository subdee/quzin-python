#!/usr/bin/python

import configparser
import datetime
import json
import os
import sqlite3
import sys
import webbrowser

import requests
from PyQt5 import QtCore, uic
from PyQt5.QtCore import QSize, QCoreApplication
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import *
from darksky import forecast
from googleapiclient.discovery import build
from lxml import html
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

guipath = os.path.join(bundle_dir, 'qtcreator/mainwindow.ui')
dialogpath = os.path.join(bundle_dir, 'qtcreator/dialog.ui')
jsonpath = os.path.join(bundle_dir, 'season_items.json')
iconspath = os.path.join(bundle_dir, 'icons/')
translationpath = os.path.join(bundle_dir, 'translations/' + configParser.get('general', 'lang') + '.qm')
dbpath = os.path.join(bundle_dir, 'database/recipes.sqlite')


class RecipeDialog(QDialog):
    curr = None
    curr_recipe = (None, None, None)

    def show_recipe(self):
        if self.curr is None:
            return
        meta = self.curr.data(32)
        if meta == self.curr.text():
            return self.view_saved_recipe()
        page = requests.get(self.curr.data(32))
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

        self.curr_recipe = (title_text, ingredient_text, method_text)
        self.fill_recipe_parts(title_text, ingredient_text, method_text)

    def view_saved_recipe(self):
        conn = sqlite3.connect(dbpath)
        c = conn.cursor()
        c.execute("SELECT * FROM recipes WHERE name=?", (self.curr.text(),))
        recipe = c.fetchone()
        conn.commit()
        conn.close()
        self.fill_recipe_parts(recipe[0], recipe[1], recipe[2], False)

    def save_recipe(self):
        if self.curr_recipe is None:
            return
        conn = sqlite3.connect(dbpath)
        c = conn.cursor()
        try:
            c.execute("INSERT INTO recipes VALUES (?, ?, ?)", (self.curr_recipe[0], self.curr_recipe[1], self.curr_recipe[2]))
        except sqlite3.IntegrityError:
            print('ERROR: Recipe already exists with name {}'.format(self.curr_recipe[0]))
        conn.commit()
        conn.close()

    def fill_recipe_parts(self, title, ingredients, instructions, show_save_btn=True):
        self.recipeIngredients.setPlainText(ingredients)
        self.recipeIngredients.verticalScrollBar().triggerAction(QScrollBar.SliderToMinimum)
        self.recipeInstructions.setPlainText(instructions)
        self.recipeIngredients.verticalScrollBar().triggerAction(QScrollBar.SliderToMinimum)
        self.setWindowTitle(title)
        if not show_save_btn:
            self.saveRecipeBtn.hide()

    def set_recipe(self, curr):
        self.curr = curr

    def __init__(self):
        super(self.__class__, self).__init__()

        uic.loadUi(dialogpath, self)

        self.saveRecipeBtn.clicked.connect(self.save_recipe)


class MainWindow(QMainWindow):
    def set_datetime(self):
        current_time = str(datetime.datetime.now().strftime("%H:%M\n%a, %d %b"))
        self.timeLabel.setText(current_time)

    def search_recipes(self):
        self.searchResultsList.clear()
        search_value = self.searchInput.text()
        service = build("customsearch", "v1", developerKey=configParser.get('recipes', 'developer_key'))
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

    def view_recipes(self):
        self.searchResultsList.clear()
        conn = sqlite3.connect(dbpath)
        c = conn.cursor()
        c.execute("SELECT * FROM recipes ORDER BY name ASC")
        recipes = c.fetchall()
        conn.close()
        if recipes is None:
            listItem = QListWidgetItem(QCoreApplication.translate("main", "No recipes found"))
            self.searchResultsList.addItem(listItem)
        else:
            for recipe in recipes:
                listItem = QListWidgetItem(recipe[0])
                listItem.setData(32, recipe[0])
                listItem.setSizeHint(QSize(50, 50))
                self.searchResultsList.addItem(listItem)

    def show_recipe(self, curr):
        dialog = RecipeDialog()
        dialog.showMaximized()
        dialog.set_recipe(curr)
        dialog.show_recipe()
        dialog.exec_()

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

    def set_slack_message(self):
        sc = SlackClient(configParser.get("slack", "token"))
        resp = sc.api_call("groups.history", channel=configParser.get("slack", "channel"), count=1)
        if not resp["ok"]:
            return

        message = resp["messages"][0]["text"]

        self.slackMessage.setText(message)

    def open_weather(self):
        lat = configParser.get('weather', 'latitude')
        long = configParser.get('weather', 'longitude')
        webbrowser.open_new_tab("https://darksky.net/forecast/" + lat + "," + long + "/ca12/en")

    def __init__(self):
        super(self.__class__, self).__init__()

        uic.loadUi(guipath, self)

        self.set_datetime()
        self.set_weather()
        self.set_season_items()
        self.set_slack_message()

        self.slack_timer = QtCore.QTimer(self)
        self.slack_timer.setInterval(2000)
        self.slack_timer.timeout.connect(lambda: self.set_slack_message())
        self.slack_timer.start()

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
        self.searchResultsList.itemClicked.connect(self.show_recipe)

        self.viewRecipesBtn.clicked.connect(self.view_recipes)

        self.seasonMonthSelect.currentIndexChanged.connect(self.show_season_items)
        self.seasonMonthSelect.setCurrentIndex(datetime.datetime.now().month - 1)

        self.weatherIconLabel.clicked.connect(self.open_weather)


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
