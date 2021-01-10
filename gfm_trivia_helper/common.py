import csv
import json
import logging
import operator
import os
from time import sleep

import requests
import zmtools

LOGGER = logging.getLogger(__name__)

QUESTION_TYPES = {
    0: "AND",
    1: "OR"
}


def post(url_type, payload, secret):
    '''
    Do a post request with a secure payload
    '''
    attempt_num = 0
    for attempt_num in range(3):
        try:
            out = requests.post(
                secret.urls[url_type], json=secret.secure_payload(payload)).json()
            LOGGER.debug(out)
            return out
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


def _get_user_data(user_data, user_id, secret):
    '''
    Retrieve a user's data from the user_data dict and if it does not exist, use the API to get it and then append it to the user_data dict
    '''
    try:
        out = user_data[user_id]
    except KeyError:
        out = post("USER", {"id": user_id}, secret)
        user_data[user_id] = out
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


def create_quiz(secret, questions_data):
    '''
    Create a trivia quiz on the site
    '''
    return post("CREATE_QUIZ", {"questions": questions_data}, secret)["quizNumber"]


def view_user_answers(user_data, secret, answers_data=None, quiz_number=None):
    '''
    View users' answers
    '''
    if answers_data is not None and quiz_number is not None:
        raise ValueError("Cannot specify both answers_data and quiz_number")
    if answers_data is None:
        answers_data = post("ANSWERS", {"quizNumber": quiz_number}, secret)
    print("Viewing data for quiz #{}".format(answers_data["quizNumber"]))
    for question in answers_data["questions"]:
        print()
        print("! Question: {}".format(question["questionText"]))
        print("! Answer(s): {} ({})".format(
            question["questionAnswer"]["answer"], QUESTION_TYPES[question["questionAnswer"]["type"]]))
        print("----")
        for answer in question["userAnswers"]:
            print("! {} answered: {}".format(_get_user_data(user_data,
                                                            answer["userID"], secret)["email"], answer["answerText"]))


def export_data(answers_data, user_data, secret):
    '''
    Export answers data to a CSV and return the filename
    '''
    folder = os.path.join(os.path.expanduser("~"), "quiz_results", "gfm")
    os.makedirs(folder, exist_ok=True)
    filename = os.path.join(
        folder, "gfmquizresults-{}.csv".format(answers_data["quizNumber"]))
    with open(filename, "w", newline="") as csvfile:
        fieldnames = ["user", "question", "answer", "answer_id"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for question in answers_data["questions"]:
            for answer in question["userAnswers"]:
                writer.writerow({"user": _get_user_data(user_data, answer["userID"], secret)[
                                "email"], "question": question["questionText"], "answer": answer["answerText"], "answer_id": answer["answerID"]})
    return filename


def set_quiz(secret, quiz_number):
    '''
    Set the site's current quiz number
    '''
    return post("SET_QUIZ", {"quizNumber": quiz_number}, secret)


def check_user_answers(user_data, secret, answers_data=None, quiz_number=None):
    '''
    Grade a user's answers and return the highest's scoring user and the rest of the scores
    '''
    if answers_data is not None and quiz_number is not None:
        raise ValueError("Cannot specify both answers_data and quiz_number")
    if answers_data is None:
        answers_data = post("ANSWERS", {"quizNumber": quiz_number}, secret)
    scores = {}
    for question in answers_data["questions"]:
        for answer in question["userAnswers"]:
            user = _get_user_data(user_data, answer["userID"], secret)["email"]
            if answer["answerText"] == "":
                # Left blank means efinitely wrong
                continue
            match = _compare_answer(
                answer["answerText"], question["questionAnswer"])
            if not match:
                print("! {} answered with non-matching answer for question \"{}\".\n    User answer: {}\n    Actual answer: {} ({})".format(_get_user_data(user_data, answer["userID"], secret)[
                      "email"], question["questionText"], answer["answerText"], question["questionAnswer"]["answer"], QUESTION_TYPES[question["questionAnswer"]["type"]]))
            if match or y_to_continue("? Accept answer?"):
                scores[user] = scores.get(user, 0) + 1
    highest_score_user = max(scores.items(), key=operator.itemgetter(1))[0]
    print("! The user with the highest score is {} (score: {}). You may want to notify them that they won something!".format(
        highest_score_user, scores[highest_score_user]))
    return highest_score_user, scores
