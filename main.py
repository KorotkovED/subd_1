import sys
import sqlite3
# from functools import wraps
from PyQt6 import uic, QtCore
from PyQt6 import QtWidgets as qtw
from PyQt6.QtSql import QSqlDatabase, QSqlQuery, QSqlTableModel

import config

from PyQt6.QtWidgets import QMessageBox
from PyQt6.QtGui import QIntValidator

db_name = 'database.db'


def send_args_inside_func(func):
    def wrapper(*args, **kwargs):
        return lambda: func(*args, **kwargs)
    
    return wrapper


def get_data(db_name, table=None, query="SELECT * FROM {}"):
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    query = query.format(table) or query
    cursor.execute(query)
    data = cursor.fetchall()
    conn.close()
    return data


def get_headers(table):
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    cursor.execute(f"SELECT * FROM {table}")
    cursor.fetchall()
    data = [descr[0] for descr in cursor.description]
    conn.close()
    return data


def new_get_data(table=None, query=None):
    Query = QSqlQuery()
    if not query and not table:
        return None
    query = f"SELECT * FROM {table}"
    Query.exec(query)
    model = QSqlTableModel()
    model.setQuery(Query)
    return model


def show_data(table, query):
    model = new_get_data(table, query)
    view = qtw.QTableView()
    view.setModel(model)
    view.show()


def query_change_db(db_name, query):
    """Запросы на изменения таблицы"""
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    cursor.execute(query)
    conn.commit()
    conn.close()

def get_rows_from_table(index, model):
    """Получение данных строки в таблице (не из БД)"""
    rowIndex = index
    columnCount = model.columnCount()
    rowValues = []
    for columnIndex in range(columnCount):
        cellValue = model.data(model.index(rowIndex, columnIndex))
        rowValues.append(cellValue)
    return rowValues

class Window():
    def __init__(self, ui) -> None:
        # get all table names in self.tables
        Form, Window = uic.loadUiType(ui)
        self.window = Window()
        self.form = Form()
        self.form.setupUi(self.window)
        self.cache = {"FOs": [], "regions": [], "cities": [], "universities": []}
        # window.show()
    
    def filter_by_FO(self):
        FO = self.form.comboBoxFO.currentText()
        if not self.cache['FOs']:
            FOs = get_data(db_name, query="SELECT DISTINCT region FROM VUZ")
            self.cache['FOs'] = [FO[0] for FO in FOs]
        if FO not in self.cache['FOs']:
            return
        self.FO = FO
        regions = get_data(
            db_name,
            query=f"SELECT DISTINCT oblname FROM VUZ  WHERE region = '{FO}'")
        self.cache['regions'] = [region[0] for region in regions]
        self.form.comboBoxRegion.clear()
        self.form.comboBoxRegion.addItems(self.cache['regions'])


    def filter_by_region(self):
        region = self.form.comboBoxRegion.currentText()
        if region not in self.cache['regions']:
            return
        self.region = region
        cities = get_data(
            db_name, 
            query=f"SELECT DISTINCT city FROM VUZ WHERE oblname = '{region}'")
        self.cache['cities'] = [city[0] for city in cities]
        self.form.comboBoxCity.clear()
        self.form.comboBoxCity.addItems(self.cache['cities'])
            


    def filter_by_city(self):
        city = self.form.comboBoxCity.currentText()
        if city not in self.cache['cities']:
            return
        self.city = city
        universities = get_data(
            db_name, 
            query=f"SELECT DISTINCT z2 FROM VUZ WHERE city = '{city}'")
        self.cache['universities'] = [university[0] for university in universities]
        self.form.comboBoxUniversity.clear()
        self.form.comboBoxUniversity.addItems(self.cache['universities'])

    def filter_by_university(self):
        university = self.form.comboBoxUniversity.currentText()
        if university not in self.cache['universities']:
            return
        self.university = university

    def apply_filter(self, main_window):
        def inner():
            data = get_data(main_window.db_name, 
                            query=f"""SELECT Tp_nir.* 
                            FROM Tp_nir JOIN VUZ ON Tp_nir.codvuz = VUZ.codvuz
                            WHERE region = '{self.FO}' 
                            AND oblname = '{self.region}' 
                            AND city = '{self.city}'
                            AND Tp_nir.z2 = '{self.university}'""")
            main_window.show_table('Tp_nir', 'Nir', 'Информация о НИР', config.TP_NIR_HEADERS,
                                config.TP_NIR_COLUMN_WIDTH, data)
        return inner

    def connect_db(self, db_name):
        db = QSqlDatabase.addDatabase('QSQLITE')
        db.setDatabaseName(db_name)
        if not db.open():
            print('Не удалось подключиться к базе')
            return False
        return db


class MainWindow(Window):
    def __init__(self, ui, db_name) -> None:
        if not self.connect_db(db_name):
            sys.exit(-1)

        print('Connection OK')
        self.db_name = db_name
        tables = get_data(db_name, 
                          query="SELECT * FROM sqlite_master WHERE type='table'")
        self.tables = [t[1] for t in tables]
        super().__init__(ui)

        

    def show_table(self, table, widgetname, title='', headers=None,
                   column_widths=None, data=None):
        # check if table exists in database
        if not data:
            data = get_data(self.db_name, table)

        getattr(self.form, f"{widgetname}ViewWidget").setRowCount(len(data))
        getattr(self.form, f"{widgetname}ViewWidget").setColumnCount(len(data[0]))
        for i in range(len(data)):
            for j in range(len(data[0])):
                item = qtw.QTableWidgetItem(str(data[i][j]))
                item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignLeft)
                getattr(self.form, f"{widgetname}ViewWidget").setItem(i, j, item)

        if headers:
            getattr(self.form, f"{widgetname}ViewWidget").setHorizontalHeaderLabels(headers)

        if column_widths and len(column_widths) == len(data[0]):
            for column, width in enumerate(column_widths):
                getattr(self.form, f"{widgetname}ViewWidget").setColumnWidth(column, width)

        sort_enabled = False if widgetname == "Nir" else True
        getattr(self.form, f"{widgetname}ViewWidget").setSortingEnabled(sort_enabled)
        getattr(self.form, f"{widgetname}Label").setText(title) 


@send_args_inside_func
def sort_selected(window: MainWindow):
    item = window.form.comboBoxSort.currentText()
    if item.endswith('Кода'):
        if item == "Сортировка по Убыванию Кода":
            order = QtCore.Qt.SortOrder.DescendingOrder
        elif item == "Сортировка по Увеличению Кода":
            order = QtCore.Qt.SortOrder.AscendingOrder
        window.form.NirViewWidget.setSortingEnabled(False)
        column_names = ', '.join(get_headers('Tp_nir')[2:])
        data = get_data(db_name,
                        query=f"""SELECT codvuz || rnw AS clmn,  {column_names} 
                        FROM Tp_nir 
                        ORDER BY codvuz, clmn""")
        headers = ['Код + рнв ебень'] + list(config.TP_NIR_HEADERS[2:])
        window.show_table('Tp_nir', 'Nir', 'Информация о НИР', data=data, headers=headers)
        window.form.NirViewWidget.sortItems(0, order)
    else:
        sort_toggle = False if item == "Без сортировки" else True
        window.show_table('Tp_nir', 'Nir', 'Информация о НИР', headers=config.TP_NIR_HEADERS,
                            column_widths=config.TP_NIR_COLUMN_WIDTH)
        window.form.NirViewWidget.setSortingEnabled(sort_toggle)

@send_args_inside_func     
def deleteRow(Indexes, window: MainWindow):
    """Вспомогательный метод удаления строки для delete_button"""
    for index in Indexes:
        window.form.NirViewWidget.model().removeRow(index)
    window.form.NirViewWidget.model().submit()
    # main_window.show_table('Tp_nir', 'Nir', 'Информация о НИР', headers=config.TP_NIR_HEADERS,
    #                         column_widths=config.TP_NIR_COLUMN_WIDTH)
    # delete_window.window.close()

@send_args_inside_func
def delete_button(window: MainWindow):
    """Кнопка удаления строки."""
    selected_rows = window.form.NirViewWidget.selectionModel().selectedRows()
    selected_indexes = [index.row() for index in selected_rows]
    window.form.message = QMessageBox()
    if len(selected_indexes) > 0:
        window.form.message.setText("Вы уверены, что хотите удалить выделенные записи?")
        window.form.message.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if window.form.message.exec() == window.form.message.StandardButton.Yes:
            stack = []
            for index in selected_indexes:
                print(selected_indexes)
                window.form.NirViewWidget.model().removeRow(index)
                stack.append(get_rows_from_table(index, window.form.NirViewWidget.model()))
            window.form.NirViewWidget.model().submit()
            
            for i in range(len(stack)):
                query = f"DELETE FROM Tp_nir WHERE codvuz = '{stack[i][0]}' AND rnw = '{stack[i][1]}'"
                query_change_db(db_name=db_name, query=query)
        else:
            message_text = 'Удаление отменено'
            window.form.message = QMessageBox(QMessageBox.Icon.Critical, 'Ошибка удаления', message_text)
            window.form.message.show()
    else:
        message_text = 'Не выбрана запись для удаления'
        window.form.message = QMessageBox(QMessageBox.Icon.Critical, 'Ошибка удаления', message_text)
        window.form.message.show()
 

@send_args_inside_func
def add_button(add_window, main_window):
    """Кнопка добавления строки."""

    add_window.window.show()

    cod_vuz = add_window.form.cod_vuz
    reg_number_nir = add_window.form.reg_number_nir
    character_nir = add_window.form.character_nir
    socr_name_vuz = add_window.form.socr_name_vuz
    cod_grnti = add_window.form.cod_grnti
    ruk_nir = add_window.form.ruk_nir
    post = add_window.form.post
    financial = add_window.form.financial
    naming_nir = add_window.form.naming_nir

    stack_naming = [
        cod_vuz,
        reg_number_nir,
        character_nir,
        socr_name_vuz,
        cod_grnti,
        ruk_nir,
        post,
        financial,
        naming_nir
        ]
    # if add_window.form.agreeButton.clicked():
    
    #     for i in stack_naming:
    #         if not i:
    #             message_text = 'Все поля должны быть заполненными!'
    #             add_window.message = QMessageBox(QMessageBox.Icon.Critical, 'Ошибка', message_text)
    #             add_window.message.show()


    #     if cod_vuz and reg_number_nir:
    #         data = get_data(db_name,
    #                         query=f"""SELECT codvuz, rnw FROM Tp_nir""") 
    #         set_cod_vuz_reg_number_nir = (cod_vuz, reg_number_nir)
    #         if set_cod_vuz_reg_number_nir in data:
    #             message_text = 'Связь код ВУЗа и рег.номера НИР не уникальна!'
    #             add_window.message = QMessageBox(QMessageBox.Icon.Critical, 'Ошибка', message_text)
    #             add_window.message.show()

    #     if int(financial) <= 0:
    #         message_text = 'Значение планового финиансирования не может быть меньше или равно нулю!'
    #         add_window.message = QMessageBox(QMessageBox.Icon.Critical, 'Ошибка', message_text)
    #         add_window.message.show()
    

    #     model = main_window.form.NirViewWidget
    #     record = model.record()

    #     record.setValue("Код ВУЗа", cod_vuz)
    #     record.setValue("Рег. номер НИР", reg_number_nir)
    #     record.setValue("Характер НИР", character_nir)
    #     record.setValue("Сокр. назв. ВУЗа", socr_name_vuz)
    #     record.setValue("Код ГРНТИ", cod_grnti)
    #     record.setValue("Руководитель НИР", ruk_nir)
    #     record.setValue("Должность руководителя", post)
    #     record.setValue("Плановое финанс.", financial)
    #     record.setValue("Наименование НИР", naming_nir)

    #     model.insertRecord(0, record)
    #     model.submitAll()
    #     model.select()
    # else:
    #     add_window.window.close()

    # if is_row_edit:
    #     model.setRecord(row_to_edit, record)
    # else:
    #     model.insertRecord(0, record)

    
    # add_dialog.accept()

@send_args_inside_func
def change_button(window: MainWindow):
    """Кнопка изменения/редактирования строки."""
    
    # selected_indexes = window.form.NirViewWidget.selectedIndexes()
    # if selected_indexes:
    #     row = selected_indexes[0].row()
    #     record = model.record(row)
        # record_dialog((row, record))


# Form_row_deletion_confirmation, Window_row_deletion_confirmation = Window("delete_button.ui")
# Form_message_delete_row, Window_message_delete_row = Window("message_delete.ui")
# window_row_deletion = Window_row_deletion_confirmation()
# form_row_deletion = Form_row_deletion_confirmation()
# form_row_deletion.setupUi(window_row_deletion)

# # окно-сообщение что строка для удаления не выделена
# window_message_delete_row = Window_message_delete_row()
# form_message_delete_row = Form_message_delete_row()
# form_message_delete_row.setupUi(window_message_delete_row)

def close_all():
    main_window.window.close()
    filter_window.window.close()
    exit_window.window.close()
    # delete_window.close()
    # delete_messege_window.close()


app = qtw.QApplication([])
main_window = MainWindow('MainForm_layout.ui', db_name)
filter_window = Window('filtr.ui')
exit_window = Window('ex_aht.ui')

delete_window = Window('delete_button.ui')
delete_messege_window = Window('message_delete.ui')
add_window = Window('add_button.ui')

for values in zip(main_window.tables, config.widgetnames,
                    ['Информация о финансировании', 'Информация о ВУЗах',
                    'Информация о рубриках ГРНТИ', 'Информация о НИР', ],
                    [config.TP_FV_HEADERS, config.VUZ_HEADERS,
                    config.GRNTI_HEADERS, config.TP_NIR_HEADERS],
                    [config.TP_FV_COLUMN_WIDTH, config.VUZ_COLUMN_WIDTH,
                    config.GRNTI_COLUMN_WIDTH, config.TP_NIR_COLUMN_WIDTH], [None]*4):
    main_window.show_table(*values)

for FO in get_data(db_name, query="SELECT DISTINCT region FROM VUZ"):
    filter_window.cache['FOs'].append(FO[0])




filter_window.form.comboBoxFO.addItems(filter_window.cache['FOs'])
filter_window.form.comboBoxFO.currentTextChanged.connect(filter_window.filter_by_FO)
filter_window.form.comboBoxRegion.currentTextChanged.connect(filter_window.filter_by_region)
filter_window.form.comboBoxCity.currentTextChanged.connect(filter_window.filter_by_city)
filter_window.form.comboBoxUniversity.currentTextChanged.connect(filter_window.filter_by_university)
filter_window.form.filterButton.clicked.connect(filter_window.apply_filter(main_window))

main_window.form.comboBoxSort.currentTextChanged.connect(sort_selected(main_window))
main_window.form.filterButton.clicked.connect(filter_window.window.show)
filter_window.form.cancelButton.clicked.connect(filter_window.window.close)
main_window.window.show()
main_window.form.exitButton.clicked.connect(exit_window.window.show)
exit_window.form.agreeButton.clicked.connect(close_all)
exit_window.form.cancelButton.clicked.connect(exit_window.window.close)

main_window.form.removeButton.clicked.connect(delete_button(main_window))

main_window.form.appendButton.clicked.connect(add_button(add_window, main_window))

exit(app.exec())
