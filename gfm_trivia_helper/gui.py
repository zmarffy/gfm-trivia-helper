import logging
import os
import subprocess
import sys

import zmtools
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import QThread, pyqtSignal

from .common import post, create_quiz, export_data, set_quiz
from .secretstuff import SecretStuff

from .gui_layouts import quiz_dialogs

zmtools.init_logging()

SECRET = None
USER_DATA = {}
LOGGER = logging.getLogger(__name__)


class Worker(QtCore.QThread):
    output = pyqtSignal(object)

    def __init__(self):
        super(Worker, self).__init__()

    def _run(self):
        # Override me
        LOGGER.info("No action to take")

    def run(self):
        result = self._run()
        self.output.emit(result)


class ShowAnswersWorker(Worker):
    def __init__(self, quiz_number):
        self.quiz_number = quiz_number
        super(ShowAnswersWorker, self).__init__()

    def _run(self):
        LOGGER.info(f"Retrieving answers for quiz {self.quiz_number}")
        return _show_answers(self.quiz_number)


class SetQuizWorker(Worker):
    def __init__(self, quiz_number):
        self.quiz_number = quiz_number
        super(SetQuizWorker, self).__init__()

    def _run(self):
        LOGGER.info(f"Setting quiz to {self.quiz_number}")
        return _set_quiz(self.quiz_number)


class CreateQuizWorker(Worker):
    def __init__(self, quiz_data):
        self.quiz_data = quiz_data
        super(CreateQuizWorker, self).__init__()

    def _run(self):
        LOGGER.info(f"Creating quiz with data:\n{self.quiz_data}")
        return _create_quiz(self.quiz_data)


def open_file_with_default_program(filename):
    '''
    Wonky cross-platform open-a-file-using-its-default-program
    '''
    try:
        os.startfile(filename)
    except AttributeError:
        try:
            subprocess.check_call(["xdg-open", filename])
        except FileNotFoundError:
            subprocess.check_call(["open", filename])


def _show_answers(quiz_number):
    answers_data = post("ANSWERS", {"quizNumber": quiz_number}, SECRET)
    filename = export_data(answers_data, USER_DATA, SECRET)
    open_file_with_default_program(filename)


def _set_quiz(quiz_number):
    set_quiz(SECRET, quiz_number)


def _create_quiz(quiz_data):
    return create_quiz(SECRET, quiz_data)


class MainWindow(QtWidgets.QMainWindow):

    def __init__(self):
        if SECRET is None:
            sys.exit("No SECRET set")
        super(QtWidgets.QMainWindow, self).__init__()

        self.setWindowTitle("Trivia Helper")

        self.setFixedSize(600, 400)
        self.centralwidget = QtWidgets.QWidget(self)
        self.layoutWidget = QtWidgets.QWidget(self.centralwidget)
        self.layoutWidget.setGeometry(QtCore.QRect(210, 120, 179, 177))
        self.verticalLayout_2 = QtWidgets.QVBoxLayout(self.layoutWidget)

        self.viewAnswers = QtWidgets.QPushButton(
            "View answers", self.layoutWidget)
        self.gradeAnswers = QtWidgets.QPushButton(
            "Grade answers", self.layoutWidget)
        self.closeQuiz = QtWidgets.QPushButton("Close quiz", self.layoutWidget)
        self.setQuiz = QtWidgets.QPushButton("Set quiz", self.layoutWidget)
        self.createQuiz = QtWidgets.QPushButton(
            "Create quiz", self.layoutWidget)

        self.verticalLayout_2.addWidget(self.viewAnswers)

        self.verticalLayout_2.addWidget(self.gradeAnswers)

        self.verticalLayout_2.addWidget(self.closeQuiz)

        self.verticalLayout_2.addWidget(self.setQuiz)

        self.verticalLayout_2.addWidget(self.createQuiz)

        self.setCentralWidget(self.centralwidget)
        self.statusBar = QtWidgets.QStatusBar(self)
        self.statusBar.showMessage("Idle")
        self.setStatusBar(self.statusBar)

        self.viewAnswers.setDefault(False)

        # Set other windows
        self.createQuizQuestionForm = quiz_dialogs.QuestionCreationForm(self)

        # Set buttons' actions
        self.viewAnswers.clicked.connect(
            lambda: self._prompt_for_quiz_num_and_perform_action(self.show_answers))
        self.gradeAnswers.clicked.connect(self.alert_not_implemented)
        self.closeQuiz.clicked.connect(self.close_quiz)
        self.setQuiz.clicked.connect(
            lambda: self._prompt_for_quiz_num_and_perform_action(self.set_quiz))
        self.createQuiz.clicked.connect(self.open_create_quiz_dialog)

    def _prompt_for_quiz_num_and_perform_action(self, f):
        quiz_number, ok = QtWidgets.QInputDialog.getInt(
            self, "", "Quiz number", min=0)
        if ok:
            f(quiz_number)

    def _ask_if_should_perform_action(self, question, f):
        question_box = QtWidgets.QMessageBox()
        answer = question_box.question(
            self, "", question, question_box.Yes | question_box.No)
        if answer == question_box.Yes:
            f()

    def open_create_quiz_dialog(self):
        self.createQuizQuestionForm.show()

    def close_quiz(self):
        self.block_show_load("Closing quiz...")
        self.worker = SetQuizWorker(0)
        self.worker.finished.connect(self.reset_all)
        self.worker.start()

    def set_quiz(self, quiz_number):
        if quiz_number != 0:
            msg = "Setting quiz..."
        else:
            msg = "Closing quiz..."
        self.block_show_load(msg)
        self.worker = SetQuizWorker(quiz_number)
        self.worker.output.connect(self.show)
        self.worker.output.connect(self.reset_all)
        self.worker.start()

    def create_quiz(self, quiz_data):
        self.block_show_load("Creating quiz...")
        self.worker = CreateQuizWorker(quiz_data)
        self.worker.output.connect(self.ask_to_set_quiz)
        self.worker.output.connect(self.show)
        self.worker.output.connect(self.reset_all)
        self.worker.start()

    def show_answers(self, quiz_number):
        self.block_show_load("Retrieving answers...")
        self.worker = ShowAnswersWorker(quiz_number)
        self.worker.finished.connect(self.reset_all)
        self.worker.start()

    def ask_to_set_quiz(self, result):
        self._ask_if_should_perform_action(
            f"Go live with new quiz (#{result})?", lambda: self.set_quiz(int(result)))

    def reset_all(self):
        self.set_enabled_everything(True)
        self.statusBar.showMessage("Idle")

    def set_enabled_everything(self, enabled):
        self.viewAnswers.setEnabled(enabled)
        self.gradeAnswers.setEnabled(enabled)
        self.closeQuiz.setEnabled(enabled)
        self.setQuiz.setEnabled(enabled)
        self.createQuiz.setEnabled(enabled)

    def block_show_load(self, status):
        self.set_enabled_everything(False)
        self.statusBar.showMessage(status)
        self.show()

    def alert_not_implemented(self):
        self.alert("Not implemented yet")

    def alert(self, text):
        alert = QtWidgets.QMessageBox(self)
        alert.setIcon(QtWidgets.QMessageBox.Information)
        alert.setText(text)
        alert.setWindowTitle("Alert")
        alert.setStandardButtons(QtWidgets.QMessageBox.Ok)
        alert.show()

def main():
    global SECRET
    if "--test-mode" in sys.argv:
        LOGGER.info("Test mode enabled")
        SECRET = SecretStuff(True)
    else:
        SECRET = SecretStuff(False)
    app = QtWidgets.QApplication(sys.argv)
    mainwin = MainWindow()
    mainwin.show()
    return app.exec_()


if __name__ == "__main__":
    sys.exit(main())
