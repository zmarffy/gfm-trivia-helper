#! /usr/bin/env python3

import argparse
import csv
import json
import operator
from time import sleep

import requests

try:
    from secretstuff import secure_payload, URLS
except ImportError:
    raise ValueError(
        "Need to create secretstuff.py with a function called secure_payload in it and a dict of API URLS")

parser = argparse.ArgumentParser()
parser.add_argument("--test-mode", action="store_true", help="use test URLs")
args = parser.parse_args()

QUESTION_TYPES = {
    0: "AND",
    1: "OR"
}

if not args.test_mode:
    for k, v in URLS.items():
        URLS[k] = v.replace("_functions-dev", "_functions")
USER_DATA = {}


def post(url, payload):
    '''
    Do a post request with a secure payload
    '''
    attempt_num = 0
    for attempt_num in range(3):
        try:
            return requests.post(url, json=secure_payload(payload)).json()
        except json.decoder.JSONDecodeError:
            sleep(2)
            attempt_num += 1
    raise ValueError("Response was not JSON")


def picker(options):
    '''
    Prints a nice picker for selecting an answer
    '''
    for index, option in enumerate(options):
        print("{}) {}".format(index + 1, option))
    i = int(input("? Type a selection: ")) - 1
    return (i, options[i])


def _get_user_data(user_id):
    '''
    Retrieve a user's data from the USER_DATA dict and if it does not exist, use the API to get it and then append it to the USER_DATA dict
    '''
    try:
        out = USER_DATA[user_id]
    except KeyError:
        out = post(URLS["USER"], payload={"id": user_id})
        USER_DATA[user_id] = out
    return out


def _compare_answer(user_answer, actual_answer):
    '''
    Return False if the user's answer is not obviously the correct answer
    '''
    s = [s.upper() for s in actual_answer["answer"]]
    try:
        modified_answer = json.loads(user_answer)
        if isinstance(modified_answer, list):
            modified_answer = [s.strip().upper() for s in modified_answer]
        else:
            # No good
            modified_answer = [user_answer.upper()]
    except json.decoder.JSONDecodeError:
        # No good
        modified_answer = [s.strip().upper() for s in user_answer.split(",")]
        if len(modified_answer) == 1:
            # No good
            modified_answer = [user_answer.upper()]
    if actual_answer["type"] == 0:
        return modified_answer == s
    elif actual_answer["type"] == 1:
        return (all(x in s for x in modified_answer))


def y_to_continue(prompt="? Enter y to continue:"):
    '''
    If the user types "y" or "Y" and hits enter, return True
    '''
    return input(prompt + " (y/n): ").lower() == "y"


def _get_quiz_number():
    '''
    Return None if user's input is a blank string; else return user's input casted to an integer
    '''
    quiz_number = input("? Enter quiz number (leave blank for current quiz): ")
    return None if quiz_number == "" else int(quiz_number)


def view_user_answers(answers_data=None, quiz_number=None):
    '''
    View users' answers and export data if desired
    '''
    if answers_data is not None and quiz_number is not None:
        raise ValueError("Cannot specify both answers_data and quiz_number")
    if answers_data is None:
        answers_data = post(URLS["ANSWERS"], {"quizNumber": quiz_number})
    print("Viewing data for quiz #{}".format(answers_data["quizNumber"]))
    for question in answers_data["questions"]:
        print("! Question: {}".format(question["questionText"]))
        print("! Answer(s): {} ({})".format(
            question["questionAnswer"]["answer"], QUESTION_TYPES[question["questionAnswer"]["type"]]))
        print("----")
        for answer in question["userAnswers"]:
            print("! {} answered: {}".format(_get_user_data(
                answer["userID"])["email"], answer["answerText"]))
        print()
    if y_to_continue("? Export data?"):
        with open("gfmquizresults-{}.csv".format(answers_data["quizNumber"]), "w", newline="") as csvfile:
            fieldnames = ["user", "question", "answer", "answer_id"]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for question in answers_data["questions"]:
                for answer in question["userAnswers"]:
                    writer.writerow({"user": _get_user_data(answer["userID"])[
                                    "email"], "question": question["questionText"], "answer": answer["answerText"], "answer_id": answer["answerID"]})


def set_quiz(quiz_number):
    '''
    Set the site's current quiz number
    '''
    return post(URLS["SET_QUIZ"], {"quizNumber": quiz_number})


def check_user_answers(answers_data=None, quiz_number=None):
    '''
    Grade a user's answers and return the highest's scoring user
    '''
    if answers_data is not None and quiz_number is not None:
        raise ValueError("Cannot specify both answers_data and quiz_number")
    if answers_data is None:
        answers_data = post(URLS["ANSWERS"], {"quizNumber": quiz_number})
    scores = {}
    for question in answers_data["questions"]:
        for answer in question["userAnswers"]:
            user = _get_user_data(answer["userID"])["email"]
            if answer["answerText"] == "":
                continue
            match = _compare_answer(
                answer["answerText"], question["questionAnswer"])
            if not match:
                print("! {} answered with non-matching answer for question \"{}\".\n    User answer: {}\n    Actual answer: {} ({})".format(_get_user_data(answer["userID"])[
                      "email"], question["questionText"], answer["answerText"], question["questionAnswer"]["answer"], QUESTION_TYPES[question["questionAnswer"]["type"]]))
            if match or y_to_continue("? Accept answer?"):
                scores[user] = scores.get(user, 0) + 1
    highest_score_user = max(scores.items(), key=operator.itemgetter(1))[0]
    print("! The user with the highest score is {} (score: {}). You may want to notify them that they won something!".format(
        highest_score_user, scores[highest_score_user]))
    return highest_score_user


def create_quiz():
    '''
    Create a trivia quiz on site
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
    return post(URLS["CREATE_QUIZ"], {"questions": questions_data})["quizNumber"]


# Main
index, option = picker(["View user answers", "Grade user answers",
                        "Close current quiz", "Set quiz", "Make new quiz"])
if index == 0:
    answers_data = post(
        URLS["ANSWERS"], {"quizNumber": _get_quiz_number()})
    view_user_answers(answers_data=answers_data)
    if y_to_continue("? Grade users' answers?"):
        check_user_answers(answers_data=answers_data)
    if y_to_continue("? Would you like to close the current quiz?"):
        set_quiz(0)
elif index == 1:
    check_user_answers(quiz_number=_get_quiz_number())
    if y_to_continue("? Would you like to close the current quiz?"):
        set_quiz(0)
elif index == 2:
    set_quiz(0)
elif index == 3:
    set_quiz(input("? Input quiz number to set: "))
elif index == 4:
    print("! When you are prompted to provide the questions' answers, if the question has multiple answers, only input one of them.")
    quiz_number = create_quiz()
    if y_to_continue("? Would you like to set the quiz to the one just created?"):
        set_quiz(quiz_number)
