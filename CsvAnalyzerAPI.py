from flask import Flask, render_template, request, jsonify
import os
import requests
import pandas as pd

app = Flask(__name__)

# URL of the local model
local_model_url = "http://localhost:1234/v1/chat/completions"

# Ensuring the "uploads" directory exists
UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload():
    try:
        file = request.files['file']

        # Check if the file has a .csv extension
        if not file.filename.lower().endswith('.csv'):
            raise ValueError("Invalid file format. Please provide a .csv file.")

        # Save the uploaded file to the server
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(file_path)

        # Read the csv file
        data = pd.read_csv(file_path, encoding="ISO-8859-1")

        # Find the suggested primary column
        primary_column = find_primary_column(data)

        # Display data of the suggested primary column
        primary_column_data = display_column_data(data, primary_column)

        # Zip the data with a range of indices
        data_with_indices = list(zip(range(len(primary_column_data)), primary_column_data))

        return render_template('result.html', primary_column=primary_column, data=data_with_indices)


    except Exception as e:
        return render_template('error.html', error_message=str(e))

def get_column_suggestions(prompt):
    try:
        headers = {"Content-Type": "application/json"}
        payload = {
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "stop": ["### Instruction:"],
            "temperature": 0.1,
            "max_tokens": -1,
            "stream": False
        }

        response = requests.post(local_model_url, json=payload, headers=headers)
        response.raise_for_status()  # Raise an HTTPError for bad responses

        return response.json()["choices"][0]["message"]["content"].strip()

    except requests.exceptions.RequestException as e:
        raise Exception(f"Error: {e}")

def find_primary_column(data):
    try:
        # Generate a prompt for the local model
        prompt = (
            f"Hey there! Your teacher has given you a dataset with columns:\n{', '.join(data.columns)}\n"
            "She's curious about the primary key column. Remember, the primary key column is the one with the following characteristics:\n"
            "1. Each value must be unique.\n"
            "2. It cannot have NULL values.\n"
            "3. It should be stable and not change over time.\n"
            "4. It should be as minimal as possible.\n"
            "5. Its values should persist over time.\n"
            "Your task is to find and tell her the name of the primary key column . "
            "Please respond with only the column name and nothing more.Strictly no explanation to the answer."
        )

        # Get the primary column from the local model
        response = get_column_suggestions(prompt)

        # Find mentions of column names in the response
        column_names = [col for col in data.columns]
        matches = [col for col in column_names if col in response]

        if matches:
            return matches[0]
        else:
            return "No column name found in the response"

    except Exception as e:
        raise Exception(f"Error: {e}")

def display_column_data(data, primary_column):
    try:
        if primary_column == "No column name found in the response":
            return "No valid primary column suggested."
        else:
            return data[primary_column].unique()

    except Exception as e:
        raise Exception(f"Error: {e}")

if __name__ == '__main__':
    app.run(port=7679,debug=True)
