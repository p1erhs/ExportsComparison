# 🧾 Softone vs Stripe Export Comparator

This Flask web app allows authenticated users to upload financial export files from **Softone** and **Stripe**, and automatically compare them to identify:

- Missing **Mark Codes** in Stripe
- Missing **Invoice IDs** in Softone
- Differences in **total amounts** per invoice
- Softone entries with missing **Mark Codes**

---

## 🚀 Features

- **User authentication** with predefined credentials
- **Excel (.xlsx)** and **CSV (.csv)** file upload support
- Automatic parsing, cleaning, and comparison of data
- HTML summary of:
  - Missing mark codes
  - Missing invoice IDs
  - Amount mismatches
  - Rows without mark codes
- Export of CSV result files:
  - `missing_mark_code_from_stripe_results.csv`
  - `missing_stripe_invoices_from_softone_results.csv`
  - `amounts_results.csv`
  - `missing_markcode_rows.csv`

---

## 🛠️ Requirements

This project uses the following dependencies:

```
blinker==1.9.0
click==8.1.8
et_xmlfile==2.0.0
Flask==3.1.0
itsdangerous==2.2.0
Jinja2==3.1.6
MarkupSafe==3.0.2
numpy==2.2.5
openpyxl==3.1.5
pandas==2.2.3
python-dateutil==2.9.0.post0
python-dotenv==1.1.0
pytz==2025.2
six==1.17.0
tzdata==2025.2
Werkzeug==3.1.3
```

Install dependencies using:

```bash
pip install -r requirements.txt
```

---

## 🔐 Login Credentials

Use the following credentials to access the system:

- **Username:** `operations@loopcv.com`
- **Password:** `Loopcv123@`

> ⚠️ These credentials are hardcoded for internal use.

---

## 🖥️ How to Run

1. Clone the repository:

```bash
git clone https://github.com/yourusername/softone-stripe-comparator.git
cd softone-stripe-comparator
```

2. Run the app:

```bash
python app.py
```

3. Open your browser and go to:  
`http://localhost:5000`

---

## 📁 Expected File Formats

### Softone Excel Export (.xlsx)
- Starts from row 8
- Must include columns:
  - `A/A`, `Ημερ/νία`, `Παρατηρήσεις`, `Μ.ΑΡ.Κ myDATA`, `Συνολική αξία (+/-)`, `Παραστατικό`

### Stripe CSV Export (.csv)
- Must include columns:
  - `id`, `myDataMark (metadata)`, `Date (UTC)`, `myDataTotal (metadata)`

---

## 📄 Output Files

All result files are saved under:

```
/home/LoopCv/
```

These include:

- `missing_mark_code_from_stripe_results.csv`
- `missing_stripe_invoices_from_softone_results.csv`
- `amounts_results.csv`
- `missing_markcode_rows.csv`

---

## 🧱 Project Structure

```
├── app.py                # Main Flask app
├── templates/            # Inline HTML templates
├── README.md             # This file
```
