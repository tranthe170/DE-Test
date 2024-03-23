import os
import time
from contextlib import contextmanager
from dataclasses import dataclass

import psycopg2
import requests
from bs4 import BeautifulSoup


@dataclass
class DBConnection:
    db: str
    user: str
    password: str
    host: str
    port: int = 5432


class WarehouseConnection:
    def __init__(self, dbconn: DBConnection):
        self.conn_url = (
            f"postgresql://{dbconn.user}:{dbconn.password}@"
            f"{dbconn.host}:{dbconn.port}/{dbconn.db}"
        )

    @contextmanager
    def managed_cursor(self, cursor_factory=None):
        self.conn = psycopg2.connect(self.conn_url)
        self.conn.autocommit = True
        self.curr = self.conn.cursor(cursor_factory=cursor_factory)
        try:
            yield self.curr
        finally:
            self.curr.close()
            self.conn.close()


def get_warehouse_creds() -> DBConnection:
    return DBConnection(
        user=os.getenv("WAREHOUSE_USER", ""),
        password=os.getenv("WAREHOUSE_PASSWORD", ""),
        db=os.getenv("WAREHOUSE_DB", ""),
        host=os.getenv("WAREHOUSE_HOST", ""),
        port=int(os.getenv("WAREHOUSE_PORT", 5432)),
    )


def scrape_company_url(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.3"
    }
    companies_list = []
    r = requests.get(url, headers=headers)
    soup = BeautifulSoup(r.text, "html.parser")
    body = soup.find(class_="body")
    companies = body.find_all("li")
    for company in companies:
        company_url = company.h4.a["href"]
        companies_list.append(company_url)

    return companies_list


def extract_company_info(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
    }
    r = requests.get(url, headers=headers)
    soup = BeautifulSoup(r.text, "html.parser")

    # Extracting company name
    company_name = soup.find("h1").text.strip()

    # Extracting company info section
    company_info = soup.find(class_="the07")

    # Extracting contact info section
    contact_info = soup.find(class_="the09")

    # Extracting company information
    operational_address = None
    location = None
    contact_person = None
    telephone = None
    website = None

    for li in company_info.find_all("li"):
        text = li.get_text()
        if "Operational Address" in text:
            operational_address = text.replace("Operational Address :", "").strip()
        elif "Location" in text:
            location = text.replace("Location :", "").strip()

    for li in contact_info.find_all("li"):
        text = li.get_text()
        if "Contact Person" in text:
            contact_person = text.replace("Contact Person :", "").strip()
        elif "Telephone" in text:
            telephone = text.replace("Telephone :", "").strip()
        elif "Website" in text:
            website = li.find("a")["href"]

    # Creating dictionary to store extracted information
    company_information = {
        "company_name": company_name,
        "operational_address": operational_address,
        "location": location,
        "contact_person": contact_person,
        "telephone": telephone,
        "website": website,
    }

    return company_information


def insert_company_info(company_info):
    dbconn = get_warehouse_creds()
    with WarehouseConnection(dbconn) as conn:
        with conn.managed_cursor() as cur:
            cur.execute(
                "INSERT INTO companies (company_name, operational_address, location, contact_person, telephone, website) VALUES (%s, %s, %s, %s, %s, %s)",
                (
                    company_info["company_name"],
                    company_info["operational_address"],
                    company_info["location"],
                    company_info["contact_person"],
                    company_info["telephone"],
                    company_info["website"],
                ),
            )


headers = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3.1 Safari/605.1.1"
}
base_url = "https://www.listofcompaniesin.com/"
wood_furniture_companies = "wood-furniture-companies"
url = base_url + wood_furniture_companies + ".html"
r = requests.get(url, headers=headers)
soup = BeautifulSoup(r.text, "html.parser")
last_page_url = soup.find("a", title="Last")["href"]
last_page_number = int(last_page_url.split("/")[-1].split(".")[0][1:])
all_companies = []

for i in range(1, last_page_number + 1):
    url = base_url + wood_furniture_companies + f"/p{i}.html"
    companies = scrape_company_url(url)
    all_companies.extend(companies)
    break
    time.sleep(15)


for company in all_companies:
    company_url = base_url + company
    company_info = extract_company_info(company_url)
    print(company_info)
    time.sleep(15)
