Set-Location "C:\PB_Data"
& ".\.venv\Scripts\Activate.ps1"
python -m pip install -r requirements.txt
python ".\scripts\prepare_data.py"
streamlit run ".\mvp_app.py"
