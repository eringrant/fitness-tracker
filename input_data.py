#!/usr/bin/env python


from argparse import ArgumentParser
import csv
from datetime import datetime
import logging
import numpy as np
from scipy.optimize import curve_fit
import sys

yes = set(['yes','y', 'ye', ''])
no = set(['no','n'])


constants = [
    'gender',
    'height (cm)',
    'date of birth'
]

measurements = [
    'weight (kg)',
    'waist size at narrowest point (cm)',
    'waist size at naval (cm)',
    'hip size at widest point (cm)',
    'thigh size at widest point (cm)',
    'neck at narrowest point (cm)',
    'biceps at widest point (cm)',
    'forearm at widest point (cm)',
    'wrist at narrowest point (cm)',
]

vitals = [
    'resting heart rate (AM)',
]

weightlifting = [
    'squat (weight, sets, rep)',
    'bench press (weight, sets, rep)',
    'row (weight, sets, rep)',
    'overhead press (weight, sets, rep)',
    'deadlift (weight, sets, rep)',
]

activity_levels = [
    '1.200 = sedentary (little or no exercise)',
    '1.375 = light activity (light exercise/sports 1-3 days/week)',
    '1.550 = moderate activity (moderate exercise/sports 3-5 days/week)',
    '1.725 = very active (hard exercise/sports 6-7 days a week)',
    '1.900 = extra active (very hard exercise/sports and physical job)'
]


__author__ = 'Erin Grant (e.grant41@gmail.com)'


def exp_func(x, a, b, c):
    return a * np.exp(-b * x) + c

def sanitised_input(prompt, type_=None, min_=None, max_=None, range_=None):
    if min_ is not None and max_ is not None and max_ < min_:
        raise ValueError("min_ must be less than or equal to max_.")
    while True:
        ui = input(prompt)
        if type_ is not None:
            try:
                ui = type_(ui)
            except ValueError:
                print("Input type must be {0}.".format(type_.__name__))
                continue
        if max_ is not None and ui > max_:
            print("Input must be less than or equal to {0}.".format(max_))
        elif min_ is not None and ui < min_:
            print("Input must be greater than or equal to {0}.".format(min_))
        elif range_ is not None and ui not in range_:
            if isinstance(range_, range):
                template = "Input must be between {0.start} and {0.stop}."
                print(template.format(range_))
            else:
                template = "Input must be {0}."
                if len(range_) == 1:
                    print(template.format(*range_))
                else:
                    print(template.format(" or ".join((", ".join(map(str, range_[:-1])), str(range_[-1])))))
        else:
            return ui


def bmr_katch_mcardle(weight, bf):
    assert bf in range(0, 1)
    return 370 + 21.6 * (weight * (1 - bf))

def bmr_revised_harris_benedict(weight, height, age, gender):
    if gender == 'female':
        return 447.593 + (9.247 * weight) + (3.098 * height) - (4.330 * age)
    elif gender == 'male':
        return 88.362 + (13.397 * weight) + (4.799 * height) - (5.677 * age)

def bmr_mifflin_st_jeor(weight, height, age, gender):
    if gender == 'female':
        return (9.99 * weight) + (6.25 * height) - (4.92 * age) - 161
    elif gender == 'male':
        return (9.99 * weight) + (6.25 * height) - (4.92 * age) + 5

def bmr_owen(weight, gender):
    if gender == 'female':
        return (7.18 * weight) + 795
    elif gender == 'male':
        return (10.2 * weight) + 879

def bf_dod(waist, naval, hip, neck, height, gender, cm=True):
    if cm:
        waist, naval, hip, neck, height = cm_to_in(waist), cm_to_in(naval), cm_to_in(hip), cm_to_in(neck), cm_to_in(height)

    if gender == 'female':
       return 163.205 * np.log10(waist + hip - neck) - 97.684 * np.log10(height) - 78.387
    elif gender == 'male':
        return 86.010 * np.log10(naval - neck) - 70.041 * np.log10(height) + 36.76

def bf_cb(hips, thigh, calf, wrist, gender, age, cm=True):
    if cm:
        hips, thigh, calf, wrist = cm_to_in(hips), cm_to_in(thigh), cm_to_in(calf), cm_to_in(wrist)

    if gender == 'female':
        if age <= 30:
            return hips + 0.8*thigh - 2*calf - wrist
        else:
            return hips + thigh - 2*calf - wrist
    elif gender == 'male':
        if age <= 30:
            return 0.5*hips + thigh - 3*calf - wrist
        else:
            return 0.5*hips + thigh - 2.7*calf - wrist

def bf_mod_ymca(weight, wrist, waist, hips, forearm, gender, kg=True, cm=True):
    if kg:
        weight = kg_to_lbs(weight)
    if cm:
        wrist, waist, hips, forearm = cm_to_in(wrist), cm_to_in(waist), cm_to_in(hips), cm_to_in(forearm)

    if gender == 'female':
        return (0.268*weight - 0.318*wrist + 0.157*waist + 0.245*hips - 0.434*forearm - 8.987) / weight
    elif gender == 'male':
        return (-0.082*weight + 4.15*wrist - 94.42) / weight

def cm_to_in(cm):
    return cm / 2.54

def kg_to_lbs(kg):
    return kg / 2.20462

def script(database_file, **kwargs):


    username = input('Enter username: ').lower().split()
    year = int(input('Enter the year: '))
    month = int(input('Enter a month: '))
    day = int(input('Enter a day: '))

    try:
        datetime(year=year,month=month,day=day)
    except ValueError:
        print("Invalid date. Try again.")

        year = int(input('Enter the year: '))
        month = int(input('Enter a month: '))
        day = int(input('Enter a day: '))

        # Will throw an uncaught exception if invalid
        datetime(year=year, month=month, day=day)

    date = str(year) + '-' + str(month) + '-' + str(day)

    database = {}
    database_file = username + '.dat'

    try:
        with open(database_file, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                database[row['date']] = row

    except IOError:
        print("Database does not yet exist; creating...")

    # Begin data input
    if date in database:
        print("You are overwriting an entry.")

    entry_dict = {}

    for measurement in measurements + weightlifting:
        entry_dict[measurement] = int(input('Enter ' + measurement + ': '))

    # Write the data to file
    with open(database_file, 'w') as f:
        fieldnames = ['date'] + measurements + weightlifting
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for date in database:
            writer.writerow(database[date])

    if input("Enter heart rate decay information? (y/n)" ) in yes:

        print("")
        print("(Assumption: t=0 is at 5 minutes of rigourous exercise, beginning from a resting heart rate.)")
        print("")

        t = []
        y = []

        t.append(sanitised_input("Enter a time t (t>=0):", type=float, min_=0.0))
        y.append(sanitised_input("Enter heart rate at t:", type=float, min_=60.0, max_=200.0))

        while input("Enter more heart rate decay information? (y/n)" ) in yes:

            t.append(sanitised_input("Enter a time t (t>=0):", type=float, min_=0.0))
            y.append(sanitised_input("Enter heart rate at t:", type=float, min_=60.0, max_=200.0))

        popt, pcov = curve_fit(exp_func, t, y)
        entry_dict['heart-rate lifetime'] = popt[1]

    #


def parse_args(args):
    parser = ArgumentParser()

    parser.add_argument('--database_file', '-d', metavar='database_file',
                        default='database.json',
                        help='Database containing all prior fitness information')

    return parser.parse_args(args)

def main(args = sys.argv[1:]):
    args = parse_args(args)
    logging.basicConfig(level=args.logging)
    script(**vars(args))


if __name__ == '__main__':
    sys.exit(main())
