import pandas as pd
import os
from sqlalchemy import create_engine
from dotenv import load_dotenv


# Load environment variables
load_dotenv(".env")

# Insert DataFrame into database
def get_from_db(embed_me, limit=10):
    # Load DataFrame from CSV
    CONN_STR = os.getenv("AZURE_PG_CONNECTION")
    db = create_engine(CONN_STR)
    
    query = """
    SELECT id, name, opinion  FROM cases
    ORDER BY opinions_vector <=> azure_openai.create_embeddings(
    'text-embedding-3-small', 
    %s)::vector
    LIMIT %s;
    """

    df = pd.read_sql(query, db, params=(embed_me,limit))
    return df.to_json(orient="records")
