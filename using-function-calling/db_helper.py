import pandas as pd
import os
from sqlalchemy import create_engine
from dotenv import load_dotenv

# Load environment variables
load_dotenv(".env")

# Get data from the Postgres database
def get_from_db(vector_search_query, limit=10):
    CONN_STR = os.getenv("AZURE_PG_CONNECTION")
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

# # Fetch cases information
#print(get_from_db("I am looking for a house in a quiet neighborhood"))

