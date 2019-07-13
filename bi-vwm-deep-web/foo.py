# from flask import *
# import pandas as pd
# app = Flask(__name__)

# @app.route("/tables")
# def show_tables():
    
#     # data.set_index(['Name'], inplace=True)
#     # data.index.name=None
#     # females = data.loc[data.Gender=='f']
#     return data.to_html()
#     # tables=[females.to_html(classes='female')],
#     # titles = ['na', 'Female surfers'])


# if __name__ == "__main__":
#     app.run()
from flask import Flask, render_template, request, jsonify
import pandas as pd
import numpy as np
import json
import sys
from crawler_export import run_benchmark,get_number_of_results_from_url,get_scrapped_count

# Initialize the Flask application
app = Flask(__name__)

@app.route('/stats')
def stats():
	return render_template('stats.html')

@app.route('/table')
def index():
    return render_template('index.html')

@app.route('/_stat')
def get_stat():
    return jsonify(total=get_number_of_results_from_url("https://knihy.heureka.cz"),count=get_scrapped_count())

@app.route('/_benchmark')
def get_benchmark():
	size=request.args.get('size')
	res=run_benchmark(int(size))
	return jsonify(time=float(res))

@app.route('/_get_table')
def get_table():
	# data = pd.read_csv('scrapped/test2.csv')
	# return data.to_json()

    # a = request.args.get('a', type=int)


    df = pd.read_csv('deduplicated.csv')
    # df = pd.DataFrame(np.random.randint(0, 100, size=(a, b)))
    b=len(df.columns)
    print(df.shape, file=sys.stderr)
    return jsonify( my_table=json.loads(df.to_json(orient="split"))["data"],
                   columns=[{"title": str(col)} for col in json.loads(df.to_json(orient="split"))["columns"]])


if __name__ == '__main__':
    app.run(debug=True)