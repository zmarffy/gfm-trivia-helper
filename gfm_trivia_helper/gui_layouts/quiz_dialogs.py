import logging
from PyQt5 import QtGui, QtCore, QtWidgets
import sys

LOGGER = logging.getLogger(__name__)


class QuestionCreationForm(QtWidgets.QDialog):

    QUIZ_DATA = []

    def __init__(self, parent=None):
        super(QuestionCreationForm, self).__init__(parent)

        self.setWindowModality(True)

        self.label = QtWidgets.QLabel("Question")
        self.questionField = QtWidgets.QLineEdit()

        self.addButton = QtWidgets.QPushButton("Add another answer")
        self.addButton.clicked.connect(self.addAnswerField)

        self.cancelButton = QtWidgets.QPushButton("Cancel")
        self.addQuestionButton = QtWidgets.QPushButton(
            "Save and add another question")
        self.addQuestionAndFinishButton = QtWidgets.QPushButton("Done")

        self.cancelButton.clicked.connect(self.close)
        self.addQuestionButton.clicked.connect(self.add_question)
        self.addQuestionAndFinishButton.clicked.connect(self.finish)

        self.buttonsRow = QtWidgets.QHBoxLayout()
        self.buttonsRow.addWidget(self.cancelButton)
        self.buttonsRow.addWidget(self.addQuestionButton)
        self.buttonsRow.addWidget(self.addQuestionAndFinishButton)

        self.buttonsWidget = QtWidgets.QWidget()
        self.buttonsWidget.setLayout(self.buttonsRow)

        self.requiresAll = QtWidgets.QCheckBox(
            "This question requires a user to enter all answers")

        self.scrollLayout = QtWidgets.QFormLayout()

        self.scrollWidget = QtWidgets.QWidget()
        self.scrollWidget.setLayout(self.scrollLayout)

        self.scrollArea = QtWidgets.QScrollArea()
        self.scrollArea.setWidgetResizable(True)
        self.scrollArea.setFocusPolicy(QtCore.Qt.NoFocus)
        self.scrollArea.setWidget(self.scrollWidget)

        self.mainLayout = QtWidgets.QVBoxLayout()

        self.mainLayout.addWidget(self.label)
        self.mainLayout.addWidget(self.questionField)
        self.mainLayout.addWidget(self.scrollArea)
        self.mainLayout.addWidget(self.addButton)
        self.mainLayout.addWidget(self.requiresAll)
        self.mainLayout.addWidget(
            self.buttonsWidget, alignment=QtCore.Qt.AlignRight | QtCore.Qt.AlignBottom)

        self.setLayout(self.mainLayout)

        self.resize(500, 500)

        self.addAnswerField()

        self.setWindowTitle("Add question")

    def addAnswerField(self):
        self.scrollLayout.addRow(AnswerWidget(self))

    def _update_quiz_data(self):
        answers = [answer_widget.answerField.text()
                   for answer_widget in self.findChildren(AnswerWidget)]
        question_data = {
            "questionText": self.questionField.text(),
            "questionAnswer": {
                "answer": answers,
                "type": int(not self.requiresAll.isChecked()) if len(answers) != 1 else 0
            }
        }
        self.QUIZ_DATA.append(question_data)

    def reset_all(self):
        self.questionField.clear()
        for answer_widget in self.findChildren(AnswerWidget)[1:]:
            answer_widget.deleteLater()
        self.findChildren(AnswerWidget)[0].answerField.clear()
        self.requiresAll.setChecked(False)

    def add_question(self):
        self._update_quiz_data()
        self.reset_all()

    def finish(self):
        if self.questionField.text():
            LOGGER.info("Adding last question")
            self._update_quiz_data()
        self.parent().create_quiz(self.QUIZ_DATA)
        self.reset_all()
        self.QUIZ_DATA = []
        self.hide()

    def closeEvent(self, event):
        self.reset_all()
        self.QUIZ_DATA = []


class AnswerWidget(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super(AnswerWidget, self).__init__(parent)

        self.label = QtWidgets.QLabel("Answer")
        self.answerField = QtWidgets.QLineEdit()
        self.removeAnswerButton = QtWidgets.QPushButton("Remove")

        self.removeAnswerButton.clicked.connect(self.deleteLater)

        layout = QtWidgets.QHBoxLayout()
        layout.addWidget(self.label)
        layout.addWidget(self.answerField)
        if parent.scrollLayout.count() != 0:
            layout.addWidget(self.removeAnswerButton)
        self.setLayout(layout)
