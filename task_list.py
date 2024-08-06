import sqlite3
import sys

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (QWidget,
                             QApplication,
                             QMessageBox,
                             QListWidgetItem,
                             QComboBox,
                             QDialog,
                             QInputDialog)

from tasks import Ui_Form as tasksForm
from categories import Ui_Form as categoriesForm

DATABASE_NAME = 'tasks_db.db'


def except_hook(cls, exception, traceback):
    sys.__excepthook__(cls, exception, traceback)


def createTables(con):
    try:
        with con:
            con.execute("""
                CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL UNIQUE
                );
            """)
            con.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL UNIQUE,
                description TEXT NULL,
                done INTEGER NOT NULL DEFAULT 0,
                category_id INTEGER NOT NULL,
                FOREIGN KEY (category_id) REFERENCES categories (id) 
                ON DELETE CASCADE
                );
            """)
    except sqlite3.DatabaseError as e:
        print(f'{e.__class__.__name__}: {e}')
        sys.exit(-1)


class Categories(QDialog, categoriesForm):
    def __init__(self, con):
        super().__init__()
        self.setupUi(self)
        self.con = con
        self.loadCategories()
        self.addCategoryButton.clicked.connect(self.addCategory)
        self.deleteCategoryButton.clicked.connect(self.deleteCategory)

    def loadCategories(self):
        result = self.con.execute('''
            SELECT title
            FROM categories
        ''').fetchall()
        self.categoriesList.clear()
        for i in result:
            cat_list = QListWidgetItem(i[0])
            self.categoriesList.addItem(cat_list)

    def addCategory(self):
        text, ok = QInputDialog.getText(self, 'Вы уверены?', 'Категория:')
        if ok and text:
            self.con.execute('''
                INSERT INTO categories(title)
                VALUES (?);
            ''', (text,))
            self.loadCategories()

    def deleteCategory(self):
        category = self.categoriesList.currentItem().text()
        result = QMessageBox.question(self, 'Вы уверены?', f'Удалить категорию {category}?')
        if result != QMessageBox.StandardButton.Yes:
            return
        with self.con:
            self.con.execute('''
                DELETE from categories
                WHERE title = (?);
            ''', (category,))
            self.loadCategories()


class Tasks(QWidget, tasksForm):
    def __init__(self):
        super().__init__()
        self.setupUi(self)
        self.con = sqlite3.connect(DATABASE_NAME)
        createTables(self.con)
        self.con.execute("PRAGMA foreign_keys = 1")
        self.loadTasks()
        self.tasksList.itemClicked.connect(self.taskDetail)
        self.loadCategories()
        self.addTaskButton.clicked.connect(self.addTask)
        self.deleteTaskButton.clicked.connect(self.deleteTask)
        self.filterCategory.currentTextChanged.connect(self.loadTasks)
        self.categoriesButton.clicked.connect(self.showCategories)

    def loadTasks(self):
        result = self.con.execute('''
            SELECT tasks.id, tasks.title, description, done, categories.title
            FROM tasks
            JOIN categories
            ON category_id = categories.id;
        ''')
        self.tasksList.clear()
        for i in result:
            list_w = QListWidgetItem(i[1])
            list_w.setCheckState(Qt.CheckState.Checked if i[3] else Qt.CheckState.Unchecked)
            if self.filterCategory.currentText() == '':
                self.tasksList.addItem(list_w)
            else:
                if self.filterCategory.currentText() == i[4]:
                    self.tasksList.addItem(list_w)

    def loadCategories(self):
        result = self.con.execute('''
            SELECT id, title
            FROM categories;
        ''')
        self.selectCategory.clear()
        self.filterCategory.clear()
        self.filterCategory.addItem('')

        for i in result:
            self.selectCategory.addItem(i[1])
            self.filterCategory.addItem(i[1])

    def taskDetail(self, item):
        title = item.text()
        task = self.con.execute('''
            SELECT tasks.id, tasks.title, description, done, categories.title
            FROM tasks
            LEFT JOIN categories
            ON category_id = categories.id
            WHERE tasks.title = ?;
        ''', (title,)).fetchone()

        done = 1 if item.checkState() == Qt.CheckState.Checked else 0

        with self.con:
            self.con.execute('''
                UPDATE tasks
                SET done = ?
                WHERE id = ?;
            ''', (done, task[0]))
        self.taskTitle.setText(title)
        self.taskDescription.setText(task[2])
        self.selectCategory.setCurrentText(task[4])

    def addTask(self):
        title = self.taskTitle.text()
        description = self.taskDescription.toPlainText()
        done = 0
        category = self.selectCategory.currentText()
        category_id = self.con.execute('''
            SELECT id
            FROM categories
            WHERE title = ?
        ''', (category,)).fetchone()

        with self.con:
            result = self.con.execute('''
                INSERT INTO tasks(title, description, done, category_id)
                VALUES (?, ?, ?, ?);
            ''', (title, description, done, category_id[0]))
            self.loadTasks()

    def deleteTask(self):
        title = self.taskTitle.text()
        task_id = self.con.execute('''
            SELECT id
            FROM tasks
            WHERE title = ?
        ''', (title,)).fetchone()


        result = QMessageBox.question(
            self, 'Вы уверены?', f'Удалить задачу {title}?'
        )
        if result != QMessageBox.StandardButton.Yes:
            return
        with self.con:
            self.con.execute('''
                DELETE from tasks
                WHERE id = ?
            ''', (task_id[0],))
        self.loadTasks()

    def showCategories(self):
        self.categoriesWindow = Categories(self.con)
        self.categoriesWindow.exec()
        self.loadTasks()
        self.loadCategories()


if __name__ == '__main__':
    sys.excepthook = except_hook
    app = QApplication(sys.argv)
    window = Tasks()
    window.show()
    sys.exit(app.exec())
