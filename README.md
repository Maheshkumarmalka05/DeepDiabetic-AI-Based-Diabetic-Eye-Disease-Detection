# Diabetic_Eye
1. Install dependencies: Open your terminal or command prompt, navigate to the DeepDiabetic directory (where app.py is), and run:
>pip install Flask Werkzeug
(Note: sqlite3 is part of Python's standard library, so no separate pip install is needed for it.)

2. Set a Secret Key: For session management (crucial for user login), Flask requires a SECRET_KEY. It is highly recommended to set this as an environment variable in production.

>Linux/macOS: export FLASK_SECRET_KEY='your_very_strong_and_random_secret_key_deepdiabetic_sqlite'
>Windows (Command Prompt): set FLASK_SECRET_KEY=your_very_strong_and_random_secret_key_deepdiabetic_sqlite
>Windows (PowerShell): $env:FLASK_SECRET_KEY='your_very_strong_and_random_secret_key_deepdiabetic_sqlite'

3. Run this command before you run python app.py.
   Run the Flask application: In your terminal, run:
>python app.py

When you run app.py for the first time, the init_db() function will automatically create the deepdiabetic.db file in your DeepDiabetic directory and set up the necessary tables (users, images_data, analysis_results).
