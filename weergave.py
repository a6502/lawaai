#!/usr/bin/env python3

# std python
import csv
from datetime import date, timedelta
from pathlib import Path
import locale
import re

# pypi
from babel.dates import format_date
from flask import (
    Flask,
    render_template,
    request,
    send_file
)

# todo: centralize config?

# constants
BASEDIR = Path.home() / "lawaai"

# do not touch
csv_dir = BASEDIR / "csv"
ogg_dir = BASEDIR / "ogg"
een_dag = timedelta(days=1)

app = Flask('weergave')

@app.route('/')
def index():

    minutes = []
    maxdblvl = []
    rmsdblvl = []
    saved = []

    csvs = []
    for p in csv_dir.iterdir():
        if p.is_file() and p.suffix == '.csv':
            csvs.append(p.stem)
    
    csvs = sorted(csvs)
    app.logger.debug(f'founds csvs {csvs}')
    csvsdict = dict.fromkeys(csvs, True)

    datum = request.args.get('datum')
    if datum:
        m = re.match(r'^(\d{4}-\d{2}-\d{2})$', datum)
        if not m:
            return f'onherkende datum {datum}', 404
    else:
        datum = csvs[-2]

    if not datum in csvsdict:
        return f'csv-bestand voor datum {datum} niet gevonden', 404

    csv_file = csv_dir.joinpath(f'{datum}.csv')

    with csv_file.open(newline="") as f:
        csvreader = csv.reader(f)
        next(csvreader, None)
        for row in csvreader:
             #print(",".join(row))
             minutes.append(row[0]) #[-5:])
             maxdblvl.append(row[1])
             rmsdblvl.append(row[2])
             saved.append(row[3]=='True')

    vandaag = date.fromisoformat(datum)
    morgen = (vandaag + een_dag).isoformat()
    if morgen not in csvsdict:
        morgen = None
    gisteren = (vandaag - een_dag).isoformat()
    if gisteren not in csvsdict:
        gisteren = None
    vandaag = format_date(vandaag, format='full', locale='nl')
        
    return render_template(
        "index.html",
        datum=datum,
        vandaag=vandaag,
        gisteren=gisteren,
        morgen=morgen,
        csvs=csvs,
        labels=minutes,
        maxdblvl=maxdblvl,
        rmsdblvl=rmsdblvl,
        saved=saved,
    )

@app.route('/favicon.ico')
def favicon():
    return app.send_static_file('favicon.ico')

@app.route('/ogg')
def ogg():
    datumtijd = request.args.get('datumtijd')
    #print(f'{datumtijd=}')
    m = re.match(r'^(\d{4}-\d{2}-\d{2})T\d{2}:\d{2}$', datumtijd)
    if not m:
        return f'geen datum in {datumtijd}', 404
    datum = m.group(1)
    #print(f'{datum=}')
    ogg_datum_dir = ogg_dir.joinpath(datum)
    #print(f'{ogg_datum_dir=}')
    if not ogg_datum_dir.is_dir():
        return f'opnames van {datum} niet gevonden', 404
    ogg_file = ogg_datum_dir.joinpath(f'{datumtijd}.ogg')
    app.logger.debug(f'{ogg_file=}')
    if ogg_file.is_file():
        return send_file(
            ogg_file,
            mimetype='audio/ogg',
        )
    else:
        return f'opname van datumtijd {datumtijd} niet gevonden', 404


if __name__ == '__main__':
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=False,
        load_dotenv=False,
        use_reloader=False,
    )
