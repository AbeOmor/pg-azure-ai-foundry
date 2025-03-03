import pandas as pd
import os
from sqlalchemy import create_engine
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables
load_dotenv(".env")
CONN_STR = os.getenv("AZURE_PG_CONNECTION")

# Get data from the Postgres database
def get_from_cases_db(vector_search_query, limit=10):
    db = create_engine(CONN_STR)
    
    query = """
    SELECT id, name, opinion FROM cases
    ORDER BY opinions_vector <=> azure_openai.create_embeddings(
    'text-embedding-3-small', 
    %s)::vector
    LIMIT %s;
    """

    df = pd.read_sql(query, db, params=(vector_search_query,limit))
    return df.to_json(orient="records")

def count_related_cases(vector_search_query, start_date="1911-01-01", end_date="2025-12-31", limit=10):
    db = create_engine(CONN_STR)
    
    query = """
    SELECT COUNT(*) 
    FROM cases
    WHERE opinions_vector <=> azure_openai.create_embeddings(
        'text-embedding-3-small', 
    %s)::vector < 0.8 -- 0.8 is the threshold
    AND decision_date BETWEEN %s AND %s
    limit %s;
    """

    df = pd.read_sql(query, db, params=(vector_search_query,datetime.strptime(start_date, "%Y-%m-%d"), datetime.strptime(end_date, "%Y-%m-%d"), limit))
    return df.to_json(orient="records")
# # Fetch cases information
#print(count_related_cases("water leaking from the apartment", start_date="2015-01-01", end_date="2025-12-31",limit=5))

