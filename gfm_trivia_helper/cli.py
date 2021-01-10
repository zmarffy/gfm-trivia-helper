import argparse
import sys

from .common import picker, post, _get_quiz_number, y_to_continue, check_user_answers, set_quiz, view_user_answers, create_quiz, export_data
from .secretstuff import SecretStuff


def _create_quiz(secret):
    '''
    Create a trivia quiz on the site
    '''
    first_time_q = True
    questions_data = []
    while True:
        if first_time_q or y_to_continue("? Add another question?"):
            first_time_q = False
            question_text = input("? Input a question: ")
            first_time_a = True
            answers = []
            while True:
                if first_time_a or y_to_continue("? Add another answer?"):
                    first_time_a = False
                    answers.append(input("? Input the answer: "))
                else:
                    break
            question_data = {
                "questionText": question_text,
                "questionAnswer": {
                    "answer": answers,
                    "type": int(not y_to_continue("? Must the user answer with all answers for their answer to be considered correct?")) if len(answers) != 1 else 0
                }
            }
            questions_data.append(question_data)
        else:
            break
    return create_quiz(secret, questions_data)


def main():

    parser = argparse.ArgumentParser()
    parser.add_argument("--test-mode", action="store_true",
                        help="use test URLs")
    args = parser.parse_args()

    SECRET = SecretStuff(args.test_mode)
    USER_DATA = {}

    index = picker(["View user answers", "Grade user answers",
                    "Close current quiz", "Set quiz", "Make new quiz"])[0]
    if index == 0:
        answers_data = post(
            "ANSWERS", {"quizNumber": _get_quiz_number()}, SECRET)
        view_user_answers(USER_DATA, SECRET, answers_data=answers_data)
        if y_to_continue("? Export data?"):
            print()
            export_data(answers_data, USER_DATA, SECRET)
        if y_to_continue("? Grade users' answers?"):
            check_user_answers(USER_DATA, SECRET, answers_data=answers_data)
        if y_to_continue("? Would you like to close the current quiz?"):
            set_quiz(SECRET, 0)
    elif index == 1:
        check_user_answers(USER_DATA, SECRET, quiz_number=_get_quiz_number())
        if y_to_continue("? Would you like to close the current quiz?"):
            set_quiz(SECRET, 0)
    elif index == 2:
        set_quiz(SECRET, 0)
    elif index == 3:
        set_quiz(SECRET, input("? Input quiz number to set: "))
    elif index == 4:
        print("! When you are prompted to provide the questions' answers, if the question has multiple answers, only input one of them.")
        quiz_number = _create_quiz(SECRET)
        if y_to_continue("? Would you like to set the quiz to the one just created?"):
            set_quiz(SECRET, quiz_number)

    return 0


if __name__ == "__main__":
    sys.exit(main())
