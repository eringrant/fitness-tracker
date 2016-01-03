#!/usr/bin/env python


from argparse import ArgumentParser
import csv
from datetime import datetime
import logging
import numpy as np
from scipy.optimize import curve_fit
import sys


__author__ = 'Erin Grant (e.grant41@gmail.com)'


yes = set(['yes', 'y', 'ye', ''])
no = set(['no', 'n'])


activity_levels = [
    '1.200 = sedentary (little or no exercise)',
    '1.375 = light activity (light exercise/sports 1-3 days/week)',
    '1.550 = moderate activity (moderate exercise/sports 3-5 days/week)',
    '1.725 = very active (hard exercise/sports 6-7 days a week)',
    '1.900 = extra active (very hard exercise/sports and physical job)'
]

constants = [
    'gender',
    'height',
    'date of birth'
]

measurements = [
    'waist size at narrowest point',
    'waist size at naval',
    'hip size at widest point',
    'thigh size at widest point',
    'neck at narrowest point',
    'biceps at widest point',
    'forearm at widest point',
    'wrist at narrowest point',
    'calf at widest point',
]

vitals = [
    'resting heart rate',
]

weightlifting = [
    'squat',
    'bench press',
    'row',
    'overhead press',
    'deadlift',
]


# Measurement constants
length_units = [
    'cm',
    'inch',
]

weight_units = [
    'kg',
    'lb',
]

precision = {
    'bf': 0.001,
    'bmr': 0.001,
    'cm': 0.1,
    'inch': 0.1,
    'kg': 0.5,
    'lb': 1.,
}


def exp_func(x, a, b, c):
    return a * np.exp(-b * x) + c


def enumerate_choices_and_return_selection(choices_list):
    choices = dict((i, c) for i, c in enumerate(choices_list))
    for item in sorted(choices.items()):
        print('[%s] %s' % item)
    choice = None
    while choice is None:
        choice = choices.get(sanitised_input('Enter selection index: ',
                             type_=int, min_=0))
        if not choice:
            print('Please make a valid selection.')
    return choice


def get_time_from_input():
    prompt = 'Enter time measured (HH:MM, 24H): '
    while True:
        try:
            hours, minutes = tuple(int(i) for i in input(prompt).split(':'))
        except ValueError:
            print("Invalid format.")
        else:
            while True:
                try:
                    assert hours in range(0, 24)
                    assert minutes in range(0, 60)
                except AssertionError:
                    print("Invalid format.")
                    try:
                        hours, minutes =\
                            tuple(int(i) for i in input(prompt).split(':'))
                    except ValueError:
                        print("Invalid format.")
                        break
                else:
                    return hours + minutes / 60


def round_to(n, precision):
    correction = 0.5 if n >= 0 else -0.5
    return int(n / precision + correction) * precision


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
                    print(template.format(" or ".join
                                          ((", ".join(map(str, range_[:-1])),
                                            str(range_[-1])))))
        else:
            return ui


def cm_to_inch(cm):
    return cm / 2.54


def inch_to_cm(inch):
    return inch * 2.54


def kg_to_lb(kg):
    return kg * 2.20462


def lb_to_kg(lb):
    return lb / 2.20462


def bmr_katch_mcardle(weight, bf, **kwargs):
    return 370 + 21.6 * (weight * (1 - bf))


def bmr_revised_harris_benedict(weight, height, age, gender, **kwargs):
    if gender == 'female':
        return 447.593 + (9.247 * weight) + (3.098 * height) - (4.330 * age)
    elif gender == 'male':
        return 88.362 + (13.397 * weight) + (4.799 * height) - (5.677 * age)


def bmr_mifflin_st_jeor(weight, height, age, gender, **kwargs):
    if gender == 'female':
        return (9.99 * weight) + (6.25 * height) - (4.92 * age) - 161
    elif gender == 'male':
        return (9.99 * weight) + (6.25 * height) - (4.92 * age) + 5


def bmr_owen(weight, gender, **kwargs):
    if gender == 'female':
        return (7.18 * weight) + 795
    elif gender == 'male':
        return (10.2 * weight) + 879


def bmr(**kwargs):

    bmr_funcs = [
        bmr_katch_mcardle,
        bmr_revised_harris_benedict,
        bmr_mifflin_st_jeor,
        bmr_owen,
    ]

    print([f(**kwargs) for f in bmr_funcs])
    input()
    return np.mean([f(**kwargs) for f in bmr_funcs])


def bf_dod(waist, naval, hips, neck, height, gender, cm=True, **kwargs):
    if cm:
        waist, naval, hips, neck, height =\
            cm_to_inch(waist), cm_to_inch(naval), cm_to_inch(hips),
        cm_to_inch(neck), cm_to_inch(height)

    if gender == 'female':
        bf = 163.205 * np.log10(waist + hips - neck) -\
            97.684 * np.log10(height) - 78.387
    elif gender == 'male':
        bf = 86.010 * np.log10(naval - neck) -\
            70.041 * np.log10(height) + 36.76

    return bf / 100


def bf_cb(hips, thigh, calf, wrist, gender, age, cm=True, **kwargs):
    if cm:
        hips, thigh, calf, wrist =\
            cm_to_inch(hips), cm_to_inch(thigh), cm_to_inch(calf),
        cm_to_inch(wrist)

    if gender == 'female':
        if age <= 30:
            bf = hips + 0.8*thigh - 2*calf - wrist
        else:
            bf = hips + thigh - 2*calf - wrist
    elif gender == 'male':
        if age <= 30:
            bf = 0.5*hips + thigh - 3*calf - wrist
        else:
            bf = 0.5*hips + thigh - 2.7*calf - wrist

    return bf / 100


def bf_mod_ymca(weight, wrist, waist, hips, forearm, gender, kg=True, cm=True,
                **kwargs):
    if kg:
        weight = kg_to_lb(weight)
    if cm:
        wrist, waist, hips, forearm =\
            cm_to_inch(wrist), cm_to_inch(waist), cm_to_inch(hips),
        cm_to_inch(forearm)

    if gender == 'female':
        return (0.268*weight - 0.318*wrist + 0.157*waist + 0.245*hips -
                0.434*forearm - 8.987) / weight
    elif gender == 'male':
        return (-0.082*weight + 4.15*wrist - 94.42) / weight


def bf(**kwargs):

    bf_funcs = [
        bf_dod,
        bf_cb,
        bf_mod_ymca,
    ]

    print([f(**kwargs) for f in bf_funcs])
    input()
    return np.mean([f(**kwargs) for f in bf_funcs])


def one_rep_max(w, r, unit):
    """
    Return the one repetition maximum, in kilograms, computed from weight w and
    number of repetitions r. unit may be either kg for kilograms or lb for
    pounds.

    The formula is that introduced in

    Wathen, D. Load assignment. In: Essentials of Strength Training and
    Conditioning. T.R. Baechle. ed. Champaign. IL: Human Kinetics. 1994.
    pp. 435-439.

    The formula is shown in

    LeSuer, Dale A., James H. McCormick, Jerry L. Mayhew, Ronald L.
    Wasserstein, and Michael D. Arnold. "The Accuracy of Prediction Equations
    for Estimating 1-RM Performance in the Bench Press, Squat, and Deadlift."
    The Journal of Strength & Conditioning Research 11, no. 4 (1997): 211-213.

    to have greatest correlation with actual one rep max values, among a set of
    predictive equations.
    """
    if unit == 'kg':
        w = kg_to_lb(w)
    elif unit == 'lb':
        pass
    else:
        raise NotImplementedError

    return lb_to_kg(100 * w / (48.8 + 53.8 * np.exp(-0.075 * r)))


def script(database_file, **kwargs):

    username = sanitised_input('Enter username: ', type_=str).lower().strip()

    print('')
    print('DATE OF STATUS UPDATE:')
    year = sanitised_input('Enter the year: ', type_=int)
    month = sanitised_input('Enter the (numeric) month: ', type_=int)
    day = sanitised_input('Enter the day: ', type_=int)

    try:
        datetime(year=year, month=month, day=day)
    except ValueError:
        print("Invalid date. Try again.")

        year = sanitised_input('Enter the year: ', type_=int)
        month = sanitised_input('Enter a month: ', type_=int)
        day = sanitised_input('Enter a day: ', type_=int)

        # Will throw an uncaught exception if invalid
        datetime(year=year, month=month, day=day)

    date = str(year) + '-' + str(month) + '-' + str(day)

    database = {}
    database_file = username + '.dat'

    try:
        with open(database_file, 'r') as f:
            reader = csv.DictReader(f)

            gender = None
            height = None
            dob = None

            for row in reader:
                database[row['date']] = row

                if gender:
                    assert gender == row['gender']
                else:
                    gender = row['gender']

                if height:
                    assert height == float(row['height'])
                else:
                    height = float(row['height'])

                if dob:
                    assert dob == row['date of birth']
                else:
                    dob = row['date of birth']

    except IOError:
        print('')
        print("Database does not yet exist; creating...")

        gender = enumerate_choices_and_return_selection(['male', 'female'])

        height = sanitised_input('Enter height: ', type_=float)
        print("Choose among the following height units:")
        height_unit = enumerate_choices_and_return_selection(length_units)

        if height_unit == 'inch':
            height = inch_to_cm(height)

        dob_year = sanitised_input('Enter the year of birth: ', type_=int)
        dob_month = sanitised_input('Enter the (numeric) month of birth: ',
                                    type_=int)
        dob_day = sanitised_input('Enter the day of birth: ', type_=int)

        try:
            datetime(year=dob_year, month=dob_month, day=dob_day)
        except ValueError:
            print("Invalid date of birth. Try again.")

            dob_year = sanitised_input('Enter the year: ', type_=int)
            dob_month = sanitised_input('Enter a month: ', type_=int)
            dob_day = sanitised_input('Enter a day: ', type_=int)

            # Will throw an uncaught exception if invalid
            datetime(year=dob_year, dob_month=month, dob_day=day)

        dob = str(dob_year) + '-' + str(dob_month) + '-' + str(dob_day)

    # Begin data input
    if date in database:
        print('')
        print("You are overwriting an entry.")

    entry_dict = {}
    entry_dict['date'] = date
    entry_dict['gender'] = gender
    entry_dict['height'] = height
    entry_dict['date of birth'] = dob

    entry_dict['age'] = (datetime.now() -
                         datetime(*(int(n) for n in dob.split('-')))).days \
        / 365

    print('')

    if input("Enter weight? (y/n) ") in yes:
        print("Choose among the following weight units:")
        unit = enumerate_choices_and_return_selection(weight_units)

        weight = sanitised_input('Enter weight: ', type_=float)
        if unit == 'lb':
            weight = lb_to_kg(weight)

        entry_dict['weight'] = round_to(weight, precision['kg'])
        entry_dict['weight measurement time'] = get_time_from_input()

    print('')

    if input("Enter vitals? (y/n) ") in yes:
        for measurement in vitals:
            entry_dict[measurement] = sanitised_input('Enter ' + measurement +
                                                      ': ', type_=int)
            entry_dict[measurement + ' measurement time'] =\
                get_time_from_input()

    print('')

    if input("Enter body size measurements? (y/n) ") in yes:

        print("Choose among the following length units:")
        unit = enumerate_choices_and_return_selection(length_units)
        time = get_time_from_input()

        for measurement in measurements:

            size = sanitised_input('Enter ' + measurement + ': ', type_=float)
            if unit == 'inch':
                size = inch_to_cm(size)

            # TODO: make unit conversions modular
            entry_dict[measurement] =\
                round_to(size, precision['cm'])
            entry_dict[measurement + ' measurement time'] = time

        # If applicable, compute body fat percentage and basal metabolic rate
        if 'weight' in entry_dict:

            entry_dict['bf'] = round_to(bf(
                height=entry_dict['height'],
                weight=entry_dict['weight'],
                age=entry_dict['age'],
                gender=entry_dict['gender'],
                waist=entry_dict['waist size at narrowest point'],
                naval=entry_dict['waist size at naval'],
                hips=entry_dict['hip size at widest point'],
                thigh=entry_dict['thigh size at widest point'],
                neck=entry_dict['neck at narrowest point'],
                biceps=entry_dict['biceps at widest point'],
                forearm=entry_dict['forearm at widest point'],
                wrist=entry_dict['wrist at narrowest point'],
                calf=entry_dict['calf at widest point'],
            ), precision['bf'])

            entry_dict['bmr'] = round_to(bmr(
                height=entry_dict['height'],
                weight=entry_dict['weight'],
                age=entry_dict['age'],
                gender=entry_dict['gender'],
                bf=entry_dict['bf'],
            ), precision['bmr'])

    for measurement in weightlifting:

        print('')

        if input("Enter %s stats? (y/n) " % measurement) in yes:

            weight = sanitised_input('Enter ' + measurement + ' weight: ',
                                     type_=int)
            reps = sanitised_input('Enter ' + measurement + ' reps: ',
                                   type_=int)

            print("Choose among the following weight units:")
            unit = enumerate_choices_and_return_selection(weight_units)
            orm = one_rep_max(weight, reps, unit)

            if unit == 'lb':
                orm = lb_to_kg(orm)

            time = get_time_from_input()

            entry_dict[measurement] = round_to(orm, precision['kg'])
            entry_dict[measurement + ' measurement time'] = time

    #entry_dict['activity_level'] = int(input('Enter activity level: '))

    print('')

    if input("Enter heart rate decay information? (y/n) ") in yes:

        print("")
        print("(Assumption: t=0 is at 5 minutes of rigourous exercise,\
              beginning from a resting heart rate.)")
        print("")

        t = []
        y = []

        t.append(sanitised_input("Enter a time t (t>=0): ", type_=float,
                                 min_=0.0))
        y.append(sanitised_input("Enter heart rate at t: ", type_=float,
                                 min_=60.0, max_=200.0))

        while len(t) < 3 or \
                input("Enter more heart rate decay information? (y/n) ") \
                in yes:

            t.append(sanitised_input("Enter a time t (t>=0): ", type_=float,
                                     min_=0.0))
            y.append(sanitised_input("Enter heart rate at t: ", type_=float,
                                     min_=60.0, max_=200.0))

        popt, pcov = curve_fit(exp_func, t, y)
        entry_dict['heart-rate lifetime'] = popt[1]
        entry_dict['heart-rate lifetime measurement time'] =\
            get_time_from_input()

    # Add the measurements to the database
    database[date] = entry_dict

    # Write the data to file
    with open(database_file, 'w') as f:

        fieldnames = ['date']
        fieldnames += ['gender']
        fieldnames += ['height']
        fieldnames += ['date of birth']
        fieldnames += ['age']
        fieldnames += ['weight']
        fieldnames += ['weight measurement time']
        fieldnames += ['bmr']
        fieldnames += ['bf']
        fieldnames += measurements
        fieldnames += [m + ' measurement time' for m in measurements]
        fieldnames += weightlifting
        fieldnames += [m + ' measurement time' for m in weightlifting]
        fieldnames += vitals
        fieldnames += [m + ' measurement time' for m in vitals]
        fieldnames += ['heart-rate lifetime']
        fieldnames += ['heart-rate lifetime measurement time']

        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for date in database:
            writer.writerow(database[date])

    print('')
    print('Done.')


def parse_args(args):
    parser = ArgumentParser()

    parser.add_argument('--logging', type=str, default='INFO',
                        metavar='logging', choices=['DEBUG', 'INFO', 'WARNING',
                                                    'ERROR', 'CRITICAL'],
                        help='Logging level')
    parser.add_argument('--database_file', '-d', metavar='database_file',
                        default='database.json',
                        help='Database containing prior fitness information')

    return parser.parse_args(args)


def main(args=sys.argv[1:]):
    args = parse_args(args)
    logging.basicConfig(level=args.logging)
    script(**vars(args))


if __name__ == '__main__':
    sys.exit(main())
