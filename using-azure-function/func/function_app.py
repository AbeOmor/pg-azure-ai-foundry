"""
To deploy the function app, run the following command:
func azure functionapp publish rentCopopulator
"""

import azure.functions as func
from dotenv import load_dotenv
import logging
import db_helper

load_dotenv(".env")

app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)

@app.route(route="search_case_data", methods=["GET"])
def search_case_data(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')
    logging.info('Python Postgres trigger function processed a request.')
    
    query = req.params.get('query')
    limit = req.params.get('limit')
    if not query:
       try:
           req_body = req.get_json()
       except ValueError:
           pass
       else:
           query = req_body.get('query')

    if query:
       
       return func.HttpResponse(db_helper.get_from_db(query, limit), status_code=200)
    else:
       return func.HttpResponse(
                   "Please pass a query string or in the request body",
                   status_code=400
               )