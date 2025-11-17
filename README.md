# importance

# CSV Search Frequency Processor

A FastAPI + Next.js application that processes CSV files containing search terms and calculates search frequencies from the Bluesky search API.

## Setup

### Backend (FastAPI)

1. Create and activate a virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install Python dependencies:
```bash
pip install -r requirements.txt
```

3. Run the FastAPI server:
```bash
./run.sh
# Or manually:
# source venv/bin/activate
# uvicorn main:app --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`

### Frontend (Next.js)

1. Install Node.js dependencies:
```bash
npm install
```

2. Run the development server:
```bash
npm run dev
```

The frontend will be available at `http://localhost:3000`

## Usage

### Web Interface

1. Start both the backend and frontend servers (see Setup above)
2. Open `http://localhost:3000` in your browser
3. Drag and drop a CSV file or click to browse
4. Click the "Search" button to process the file
5. The processed CSV will automatically download

### API Endpoint

You can also use the API directly by sending a POST request to `/process` with a CSV file that contains a `search_terms` column.

### Example CSV format:
```csv
search_terms
["python","fastapi"]
["javascript","react"]
["machine learning","ai"]
```

### Example request:
```bash
curl -X POST "http://localhost:8000/process" \
  -F "file=@your_file.csv"
```

The response will be a CSV file with an additional `search_frequency` column containing the count of posts from the last 90 days for each search term.

## API Documentation

Once the server is running, visit:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
