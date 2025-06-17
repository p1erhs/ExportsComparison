from flask import Flask, request, render_template_string, redirect, url_for, session, flash
import pandas as pd
import ast
import smtplib
from email.message import EmailMessage
import logging
import os

app = Flask(__name__)
app.secret_key = "flask secret"
USER     = "putyourusenamehere"
PASSWORD = "putyourpasswordhere"

print(USER ,PASSWORD)


# Login page
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        u = request.form.get('username')
        p = request.form.get('password')
        if u == USER and p == PASSWORD:
            session['logged_in'] = True
            return redirect(url_for('upload'))
        flash('Λανθασμένα στοιχεία', 'error')
    return render_template_string(LOGIN_HTML)

# Upload and compare
@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    missing_marks = []
    missing_invs = []
    diff_amounts    = []
    missing_code_rows = []

    if request.method == 'POST':
        # load exports
        df = pd.read_excel(request.files['accounting'], skiprows=7)
        inv = pd.read_csv(request.files['stripe'])

        # parse observations
        df['Παρατηρήσεις'] = df['Παρατηρήσεις'].fillna('{}').apply(ast.literal_eval)
        df['stripe_invoice_id'] = df['Παρατηρήσεις'].apply(lambda d: d.get('stripe_invoice_id'))
        df['invoice_code'] = df['Παραστατικό']
        df = df.drop(columns=['Υποκ/μα', 'Κωδικός', 'Παρατηρήσεις'])

        # rename & format
        df = df.rename(columns={
            'A/A': 'id',
            'Ημερ/νία': 'date',
            'Μ.ΑΡ.Κ myDATA': 'mydata code',
            'Συνολική αξία (+/-)': 'total'
        })

        df['date'] = pd.to_datetime(df['date'], dayfirst=True, errors='coerce').dt.strftime('%-d/%-m/%Y')
        df['mydata code'] = df['mydata code'].astype('Int64')
        df['total']= pd.to_numeric(df['total'], errors='coerce')

        inv = inv.rename(columns={
            'id': 'invoice_id',
            'myDataMark (metadata)': 'mark_code',
            'Date (UTC)': 'date',
            'myDataTotal (metadata)': 'mydata_total'
        })[['invoice_id', 'mark_code', 'date', 'mydata_total']]
        inv['date'] = pd.to_datetime(inv['date'], utc=True, errors='coerce').dt.tz_localize(None).dt.strftime('%-d/%-m/%Y')

         # convert to integers, ignore non-numeric values (like 'TO_CHECK')
        df["mydata code"] = pd.to_numeric(df["mydata code"], errors='coerce')  # replace invalid values with NaN
        inv["mark_code"] = pd.to_numeric(inv["mark_code"], errors='coerce')  # replace invalid values with NaN
        inv['mydata_total']   = pd.to_numeric(inv['mydata_total'], errors='coerce')


        # find all empty mark codes based on id and date
        empty_markcodes = df[df['mydata code'].isna() & df['id'].notna()]
        missing_code_rows = []
        for _, row in empty_markcodes.iterrows():
            missing_code_rows.append(
                {
                    'invoice_code': row['invoice_code'],
                    'id': int(row['id']),
                    'date': row['date']})

        empty_codes_df = pd.DataFrame(missing_code_rows)
        empty_codes_df.to_csv("/home/LoopCv/missing_markcode_rows.csv", index=False)

        # filter negative amounts
        df = df[df['total'] > 0]

        # filter out NA
        df_valid = df[df['mydata code'].notna()]
        inv_valid = inv[inv['invoice_id'].notna()]
        inv_valid["mark_code"] = inv_valid["mark_code"].astype("Int64")

        # build lookup maps
        mark_map = df_valid.assign(code_str=df_valid['mydata code'].astype(str)).set_index('code_str')['date'].to_dict()
        inv_map = inv_valid.assign(id_str=inv_valid['invoice_id'].astype(str)).set_index('id_str')['date'].to_dict()

        # compare
        acc_marks = set(mark_map.keys())
        stripe_marks = set(inv_valid['mark_code'].astype(str))
        for m in sorted(acc_marks - stripe_marks):
            missing_marks.append({'code': m, 'date': mark_map[m], 'stripe_invoice_id': df_valid[df_valid['mydata code'] == int(m)]['stripe_invoice_id'].iloc[0]})

        acc_invs = set(df_valid['stripe_invoice_id'].astype(str))
        stripe_invs = set(inv_map.keys())
        for iid in sorted(stripe_invs - acc_invs):
            missing_invs.append({'id': iid, 'date': inv_map[iid]})


        merged = pd.merge(
            df_valid[['mydata code','date','total','stripe_invoice_id']],
            inv_valid[['invoice_id','mark_code','date','mydata_total']],
            left_on='mydata code', right_on='mark_code', how='inner',
            suffixes=('_softone','_stripe')
        )
        diffs = merged[merged['total'] != merged['mydata_total']]
        for _, row in diffs.iterrows():
            diff_amounts.append({
                'code': int(row['mydata code']),
                'date_softone': row['date_softone'],
                'amount_softone': row['total'],
                'date_stripe': row['date_stripe'],
                'amount_stripe': row['mydata_total'],
                'stripe_invoice_id': row['invoice_id']
            })

        result_df = pd.DataFrame(missing_marks)
        result_df.to_csv("/home/LoopCv/missing_mark_code_from_stripe_results.csv", index=False)  # Save missing marks

        inv_results_df = pd.DataFrame(missing_invs)
        inv_results_df.to_csv("/home/LoopCv/missing_stripe_invoices_from_softone_results.csv", index=False)  # Save missing invoices

        amount_res = pd.DataFrame(diff_amounts)
        amount_res.to_csv("/home/LoopCv/amounts_results.csv", index=False)







    return render_template_string(UPLOAD_HTML,
                                  missing_marks=missing_marks,
                                  missing_invs=missing_invs,
                                  diff_amounts=diff_amounts,
                                  empty_codes=missing_code_rows)

LOGIN_HTML = '''
<!doctype html>
<html lang="el">
<head>
  <meta charset="utf-8">
  <title>Login</title>
  <style>
    body { margin:0; padding:0; font-family: Arial, sans-serif; background: #f0f2f5; height:100vh; display:flex; align-items:center; justify-content:center; }
    .login-container { background:#fff; padding:2rem; border-radius:8px; box-shadow:0 4px 12px rgba(0,0,0,0.15); width:320px; }
    h2 { margin-bottom:1rem; text-align:center; color:#333; }
    form { display:flex; flex-direction:column; }
    input { margin-bottom:1rem; padding:0.5rem 0.75rem; border:1px solid #ccc; border-radius:4px; font-size:1rem; }
    input:focus { border-color:#4CAF50; outline:none; }
    button { background:#4CAF50; color:#fff; padding:0.75rem; border:none; border-radius:4px; font-size:1rem; cursor:pointer; }
    button:hover { background:#45A049; }
  </style>
</head>
<body>
  <div class="login-container">
    <h2>Σύνδεση</h2>
    <form method="post">
      <input name="username" placeholder="Username" required>
      <input name="password" type="password" placeholder="Password" required>
      <button type="submit">Σύνδεση</button>
    </form>
  </div>
</body>
</html>
'''

UPLOAD_HTML = '''
<!doctype html>
<html lang="el">
<head>
  <meta charset="utf-8">
  <title>Σύγκριση Εξαγωγών</title>
  <style>
    body { font-family: Arial, sans-serif; background: #e8f5e9; padding: 2rem; }
    .box { background: #fff; border-radius: 6px; padding: 1rem; margin: 1rem auto;
            max-width: 600px; box-shadow: 0 2px 6px rgba(0,0,0,0.1); }
    h2 { text-align: center; }
    .summary { font-weight: bold; margin-bottom: 0.5rem; }
    ul { list-style: none; padding: 0; }
    li { background: #e0ffe0; margin: 0.5rem 0; padding: 0.5rem; border-left: 4px solid #0a0; }
  </style>
</head>
<body>
  <div class="box">
    <h2>Upload Exports</h2>
    <form method="post" enctype="multipart/form-data">
      <label>Softone Excel Export:</label><br>
      <input type="file" name="accounting" accept=".xlsx" required><br><br>
      <label>Stripe CSV Export:</label><br>
      <input type="file" name="stripe" accept=".csv" required><br><br>
      <button type="submit">Σύγκριση</button>
    </form>
  </div>

  <div class="box">
    <h2>Αποτελέσματα Σύγκρισης</h2>

    <div class="summary">Mark codes που ΔΕΝ υπάρχουν στο stripe: {{ missing_marks|length }}</div>
    <ul>
      {% if missing_marks %}
        {% for m in missing_marks %}
          <li>{{ m.code }} — {{ m.date }} — Stripe Invoice ID: {{ m.stripe_invoice_id }}</li>
        {% endfor %}
      {% else %}
        <li>Κανένα</li>
      {% endif %}
    </ul>

    <div class="summary">Invoice IDs που ΔΕΝ υπάρχουν στο accounting: {{ missing_invs|length }}</div>
    <ul>
      {% if missing_invs %}
        {% for i in missing_invs %}
          <li>{{ i.id }} — {{ i.date }}</li>
        {% endfor %}
      {% else %}
        <li>Κανένα</li>
      {% endif %}
    </ul>
  </div>

  <div class="box">
    <h2>Διαφορές Ποσών ανά Mark Code</h2>
    <div class="summary">Γραμμές με ίδιο mark code αλλά διαφορετικό ποσό: {{ diff_amounts|length }}</div>
    <ul>
      {% if diff_amounts %}
        {% for d in diff_amounts %}
          <li>
            {{ d.code }} — Softone: {{ d.amount_softone }} € ({{ d.date_softone }})<br>
            &nbsp;&nbsp;&nbsp;&nbsp;Stripe: {{ d.amount_stripe }} € ({{ d.date_stripe }})<br>
            &nbsp;&nbsp;&nbsp;&nbsp;Stripe Invoice ID: {{ d.stripe_invoice_id }}
          </li>
        {% endfor %}
      {% else %}
        <li>Κανένα</li>
      {% endif %}
    </ul>
  </div>

  <div class="box">
      <h2>Γραμμές χωρίς Mark Code</h2>
      <ul>
        {% if empty_codes %}
          {% for e in empty_codes %}
            <li>{{ e.invoice_code }}  —  {{ e.id }} — {{ e.date }}</li>
          {% endfor %}
        {% else %}
          <li>Κανένα</li>
        {% endif %}
      </ul>
    </div>
</body>
</html>
'''

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    app.logger.setLevel(logging.INFO)
    app.run(debug=True, host="0.0.0.0")
