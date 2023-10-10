import sys
import os
import string
from typing import Tuple, Union, Dict
import _sqlite3 as sql
from PyQt6 import uic
from PyQt6.QtGui import QDoubleValidator, QIntValidator
from PyQt6.QtWidgets import QApplication, QDialog, QMainWindow, QVBoxLayout, QWidget, QLabel, QHBoxLayout, QPushButton, \
    QMessageBox
from PyQt6.QtSql import *
from PyQt6.QtCore import Qt, pyqtSignal
import numpy as np
import pandas as pd
import datetime

LOGICAL_OPERATORS = [
    '>', '>=', '<', '<=', '='
]

COLUMNS_DICT = {
        'Код_серии': 'Код серии',
        'Дата_торгов': "Дата торгоа",
        'Дата_исполнения': 'Дата исполнения',
        'Дата_погашения': 'Дата погашения',
        'Число_продаж': 'Число продаж',
        'Текущая_цена': 'Текущая цена\nв процентах %',
        'Минимальная_цена': 'Минимальная цена\nв процентах %',
        'Максимальная_цена': 'Максимальная цена\nв процентах %',
        'Код_фьючерса': 'Код фьючерса'
    }

DATE_COLUMNS_LIST = [
    'Дата_торгов',
    'Дата_исполнения',
    'Дата_погашения'
]

Form, Window = uic.loadUiType("SUBD.ui")
addForm, _ = uic.loadUiType("add_record_window.ui")
Directory = os.getcwd()
db_file = os.path.join(Directory, 'fond_db.db')


"""------------------------ФИЛЬТРЫ------------------------"""


def clear_filter():
    form.lineEdit.clear()
    form.lineEdit_2.clear()
    form.lineEdit_3.clear()
    form.lineEdit_4.clear()
    form.lineEdit_5.clear()
    form.lineEdit_6.clear()
    form.lineEdit_7.clear()
    form.comboBox.setCurrentIndex(0)
    form.lineEdit_9.clear()


def set_filter():
    def get_statements():
        return {
            'Дата_торгов': form.lineEdit.text(),
            'Дата_исполнения': form.lineEdit_2.text(),
            'Дата_погашения': form.lineEdit_3.text(),
            'Число_продаж': form.lineEdit_4.text(),
            'Текущая_цена': form.lineEdit_5.text(),
            'Минимальная_цена': form.lineEdit_6.text(),
            'Максимальная_цена': form.lineEdit_7.text(),
            'Код_фьючерса': form.comboBox.currentText(),
            'Код_серии': form.lineEdit_9.text()
        }

    def handle_statements(statements: Dict[str, str]) -> Dict[str, str]:
        handled_statements = dict()
        for column, raw_string in statements.items():
            statement = raw_string.strip()
            if statement:
                if column == 'Код_фьючерса':
                    if statement == 'Все':
                        continue
                    handled_statements[column] = f"{column} = '{statement}'"

                elif statement.count(' '):
                    handled_statements[column] = f'{column} SPACE_ERROR'

                elif column == 'Код_серии':
                    if statement.startswith('='):
                        statement = statement.replace('=', '')
                    for symbol in statement:
                        if symbol not in '1234567890ABCDEFGHIJKLMNOPQRSTUVWXYZ':
                            handled_statements[column] = f"{column} DATE_SYMBOLS_ERROR"
                            break
                    else:
                        operator = 'LIKE'
                        for logical_operator in LOGICAL_OPERATORS:
                            if statement.startswith(logical_operator):
                                operator = logical_operator
                                statement = statement.replace(logical_operator, '')
                                break
                        if len(statement) > 11:
                            handled_statements[column] = f"{column} DATE_LENGTH_ERROR"
                        else:
                            handled_statements[column] = f"{column} {operator} '{statement}%'"

                elif column in DATE_COLUMNS_LIST:
                    if statement.startswith('='):
                        statement = statement.replace('=', '')
                    for symbol in statement:
                        if symbol not in ''.join(LOGICAL_OPERATORS) + '1234567890-':
                            handled_statements[column] = f"{column} DATE_SYMBOLS_ERROR"
                            break
                    else:
                        operator = 'LIKE'
                        for logical_operator in LOGICAL_OPERATORS:
                            if statement.startswith(logical_operator):
                                operator = logical_operator
                                statement = statement.replace(logical_operator, '')
                                break
                        if len(statement) > 10:
                            handled_statements[column] = f"{column} DATE_LENGTH_ERROR"
                        else:
                            handled_statements[column] = f"{column} {operator} '{statement}%'"

                else:
                    for logical_operator in LOGICAL_OPERATORS:
                        if statement.startswith(logical_operator):
                            operator = logical_operator
                            statement = statement.replace(logical_operator, '')
                            handled_statements[column] = f"{column} {operator} {statement}"
                            break
                    else:
                        if statement.isdecimal():
                            handled_statements[column] = f"{column} = {statement}"
                        else:
                            handled_statements[column] = f"{column} DECIMAL_ERROR"
        return handled_statements

    def get_sql_filter():
        handled_statements = handle_statements(get_statements())
        filter_statements = list()
        errors = list()

        if handled_statements:
            for column, statement in handled_statements.items():
                if statement.endswith('ERROR'):
                    errors.append(statement)
                else:
                    filter_statements.append(statement)
            return ' AND '.join(filter_statements), errors
        return '', []

    filter_statement, errors = get_sql_filter()
    print(filter_statement)
    model.setFilter(filter_statement)
    if errors:
        columns = {
            'Дата_торгов': 'Дата торгов',
            'Дата_исполнения': 'Дата исполнения',
            'Дата_погашения': 'Дата погашения',
            'Число_продаж': 'Число продаж',
            'Текущая_цена': 'Текущая цена',
            'Минимальная_цена': 'Минимальная цена',
            'Максимальная_цена': 'Максимальная цена',
            'Код_серии': 'Код серии',
            'Код_фьючерса': 'Код фьючерса'
        }
        errors_list = list()
        for error in errors:
            column, error_type = error.split(' ')

            if error_type == 'SPACE_ERROR':
                errors_list.append(f'"{columns[column]}" заданы лишние символы пробела')

            elif error_type == 'DATE_LENGTH_ERROR':
                errors_list.append(f'"{columns[column]}" задана слишком длинная строка')

            elif error_type == 'DATE_SYMBOLS_ERROR':
                errors_list.append(f'"{columns[column]}" использованы некорректные символы')

            elif error_type == 'DECIMAL_ERROR':
                errors_list.append(f'"{columns[column]}" задано не десятичное число')

        form.message = QMessageBox(QMessageBox.Icon.Warning, 'Ошибка в задании фильтра', '\n'.join(errors_list))
        form.message.show()


"""------------------------УДАЛЕНИЕ СТРОКИ------------------------"""



def delete_row():
    selected_indexes = form.tableView.selectedIndexes()
    form.message = QMessageBox()
    if len(selected_indexes) > 0:
        form.message.setText("Вы уверены, что хотите удалить выделенные записи?")
        form.message.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if form.message.exec() == form.message.StandardButton.Yes:
            for index in sorted(selected_indexes, reverse=True):
                model.removeRow(index.row())
            model.select()
        else:
            message_text = 'Удаление отменено'
            form.message = QMessageBox(QMessageBox.Icon.Critical, 'Ошибка удаления', message_text)
            form.message.show()
    else:
        message_text = 'Не выбрана запись для удаления'
        form.message = QMessageBox(QMessageBox.Icon.Critical, 'Ошибка удаления', message_text)
        form.message.show()


"""------------------------ДОБАВЛЕНИЕ/ИЗМЕНЕНИЕ СТРОКИ------------------------"""


def record_dialog(row_record: Tuple[int, QSqlRecord] = None):
    add_dialog = QDialog(window)
    add_ui = addForm()
    add_ui.setupUi(add_dialog)
    is_row_edit = True if row_record else False
    add_dialog.setWindowTitle("Редактирование записи" if is_row_edit else "Добавление записи")
    row_to_edit, record = None, None
    if is_row_edit:
        row_to_edit, record = row_record
    else:
        record = model.record()

    query = QSqlQuery('SELECT Код_фьючерса, Код_серии, Дата_исполнения FROM Даты_исполнения_фьючерсов')
    cod_with_date_and_stat = dict()
    while query.next():
        cod_with_date_and_stat[query.value(0)] = query.value(1), query.value(2)

    add_ui.comboBox.addItems(cod_with_date_and_stat.keys())
    validator = QDoubleValidator(0, 9999, 2)
    validator_1 = QIntValidator(0, 9999)
    add_ui.lineEdit_4.setValidator(validator)
    add_ui.lineEdit_5.setValidator(validator)
    add_ui.lineEdit_6.setValidator(validator)
    add_ui.lineEdit_7.setValidator(validator_1)
    add_ui.message = None

    if is_row_edit:
        add_ui.comboBox.setCurrentIndex(add_ui.comboBox.findText(record.value("Код_фьючерса")))
        add_ui.lineEdit_2.setText('-'.join(record.value('Дата_торгов').split('-')))
        add_ui.lineEdit_3.setText('-'.join(record.value('Дата_погашения').split('-')))
        add_ui.lineEdit_4.setText(str(record.value('Текущая_цена')).replace('.', ','))
        add_ui.lineEdit_5.setText(str(record.value('Минимальная_цена')).replace('.', ','))
        add_ui.lineEdit_6.setText(str(record.value('Максимальная_цена')).replace('.', ','))
        add_ui.lineEdit_7.setText(str(record.value('Число_продаж')))

    def add_record():
        f_code = add_ui.comboBox.currentText()
        exec_date = cod_with_date_and_stat[f_code][1]
        serial_number = cod_with_date_and_stat[f_code][0]
        torg_date = add_ui.lineEdit_2.text()
        torg_date = "-".join(torg_date.split('-'))
        if torg_date >= exec_date:
            message_text = f'"Дата торгов"\nВведите дату меньшую даты погашения: {".".join(exec_date.split("-"))}'
            add_ui.message = QMessageBox(QMessageBox.Icon.Critical, 'Ошибка', message_text)
            add_ui.message.show()
            return
        if len(torg_date) != 10:
            message_text = f'"Дата торгов"\nЗаполните поле корректно'
            add_ui.message = QMessageBox(QMessageBox.Icon.Critical, 'Ошибка', message_text)
            add_ui.message.show()
            return
        try:
            datetime.datetime.strptime(torg_date, '%d-%m-%Y')
        except ValueError:
            message_text = f'"Дата торгов"\nВведите существующую дату'
            add_ui.message = QMessageBox(QMessageBox.Icon.Critical, 'Ошибка', message_text)
            add_ui.message.show()
            return
        maturity_date = add_ui.lineEdit_3.text()
        maturity_date = '-'.join(maturity_date.split('-'))
        if len(maturity_date) != 10:
            message_text = f'"Дата погашения"\nЗаполните поле корректно'
            add_ui.message = QMessageBox(QMessageBox.Icon.Critical, 'Ошибка', message_text)
            add_ui.message.show()
            return
        if torg_date >= maturity_date:
            message_text = f'"Дата торгов"\nВведите дату большую даты торгов: {torg_date}'
            add_ui.message = QMessageBox(QMessageBox.Icon.Critical, 'Ошибка', message_text)
            add_ui.message.show()
            return
        if exec_date >= maturity_date:
            message_text = f'"Дата погашения"\nВведите дату большую даты исполнения: {exec_date}'
            add_ui.message = QMessageBox(QMessageBox.Icon.Critical, 'Ошибка ', message_text)
            add_ui.message.show()
            return
        try:
            datetime.datetime.strptime(maturity_date, '%d-%m-%Y')
        except ValueError:
            message_text = f'"Дата погашения"\nВведите существующую дату'
            add_ui.message = QMessageBox(QMessageBox.Icon.Critical, 'Ошибка', message_text)
            add_ui.message.show()
            return
        value = float(str(add_ui.lineEdit_4.text()).replace(',', '.'))
        min_value = float(str(add_ui.lineEdit_5.text()).replace(',', '.'))
        max_value = float(str(add_ui.lineEdit_6.text()).replace(',', '.'))
        if max_value != 0 and value > max_value:
            message_text = f'"Цена"\nТекущая цена не может быть больше максимальной'
            add_ui.message = QMessageBox(QMessageBox.Icon.Critical, 'Ошибка', message_text)
            add_ui.message.show()
            return
        if value < min_value:
            message_text = f'"Цена"\nТекущая цена не может быть меньше минимальной'
            add_ui.message = QMessageBox(QMessageBox.Icon.Critical, 'Ошибка', message_text)
            add_ui.message.show()
            return
        record.setValue("Дата_торгов", torg_date)
        record.setValue("Дата_исполнения", exec_date)
        record.setValue("Дата_погашения", maturity_date)
        record.setValue("Число_продаж", int(add_ui.lineEdit_7.text()))
        record.setValue("Текущая_цена", float(str(add_ui.lineEdit_4.text()).replace(',', '.')))
        record.setValue("Минимальная_цена", float(str(add_ui.lineEdit_5.text()).replace(',', '.')))
        record.setValue("Максимальная_цена", float(str(add_ui.lineEdit_6.text()).replace(',', '.')))
        record.setValue("Код_серии", serial_number)
        record.setValue("Код_фьючерса", f_code)

        if is_row_edit:
            model.setRecord(row_to_edit, record)
        else:
            model.insertRecord(0, record)

        model.submitAll()
        model.select()
        add_dialog.accept()

    add_ui.pushButton.clicked.connect(add_record)
    add_ui.pushButton_2.clicked.connect(add_dialog.close)
    add_dialog.exec()


"""------------------------ПОДКЛЮЧЕНИЕ БД------------------------"""


def connect_db(db_file):
    db = QSqlDatabase.addDatabase("QSQLITE")
    db.setDatabaseName(db_file)
    if not db.open():
        print("Cannot establish a database connection to {}!".format(db_file))
        return False
    return db


"""------------------------ОТКРЫТИЕ ОКНА ДОБАВЛЕНИЯ/ИЗМЕНЕНИЯ------------------------"""


def open_add_record_window():
    record_dialog()


def open_edit_record_window():
    selected_indexes = form.tableView.selectedIndexes()
    if selected_indexes:
        row = selected_indexes[0].row()
        record = model.record(row)
        record_dialog((row, record))


app = QApplication([])
window = Window()
form = Form()
form.setupUi(window)
form.message = None

if not connect_db(db_file):
    sys.exit(-1)
else:
    print("connection ok")

model = QSqlTableModel()
model_2 = QSqlTableModel()
model_2.setTable('Общая_таблица')
model_2.select()
model.setTable('Общая_таблица')
for i in range(model.columnCount()):
    header_data = model.headerData(i, Qt.Orientation.Horizontal, Qt.ItemDataRole.DisplayRole)
    column_name = COLUMNS_DICT[header_data]

    model.setHeaderData(i, Qt.Orientation.Horizontal, column_name, Qt.ItemDataRole.DisplayRole)
    model.setHeaderData(i, Qt.Orientation.Horizontal, header_data, Qt.ItemDataRole.UserRole)

model.select()

form.tableView.setSortingEnabled(True)
form.tableView.setModel(model)
form.pushButton.clicked.connect(open_add_record_window)
form.pushButton_2.clicked.connect(open_edit_record_window)
form.pushButton_3.clicked.connect(delete_row)

query = QSqlQuery('SELECT Код_фьючерса FROM Даты_исполнения_фьючерсов')
cod_list = ['Все']
while query.next():
    cod_list.append(query.value(0))
form.comboBox.addItems(cod_list)
form.pushButton_4.clicked.connect(set_filter)
form.pushButton_5.clicked.connect(clear_filter)

window.show()
app.exec()
