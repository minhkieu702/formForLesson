from flask import Flask, render_template_string

# === FLASK APP ===
app = Flask(__name__)

# === LINK FORM GOOGLE FORM CỦA BẠN ===
FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLSdcwgPmynO6D2eailGclDiy6_JnHsPWb4XrYOkHzeGWwBJ4qA/viewform?embedded=true"

# === HTML GIAO DIỆN ===
HTML_TEMPLATE = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Google Form Embed</title>
    <style>
        body {{
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            min-height: 100vh;
            margin: 0;
            font-family: Arial, sans-serif;
            background-color: #f5f5f5;
        }}
        h2 {{
            margin-bottom: 20px;
        }}
        iframe {{
            border: none;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            border-radius: 10px;
        }}
    </style>
</head>
<body>
    <h2>Vui lòng điền vào form bên dưới:</h2>
    <iframe src="{FORM_URL}" width="640" height="800" allowfullscreen></iframe>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

if __name__ == '__main__':
    app.run(debug=True)
