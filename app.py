from flask import Flask, request, jsonify, send_file
import os
import pdfplumber
import logging
from langchain_community.llms import Ollama
from langchain_core.prompts import ChatPromptTemplate
from flask_cors import CORS
from langchain_core.output_parsers import StrOutputParser
import random
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.units import inch
from io import BytesIO

logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)
CORS(app)

# Variabile globale per i temi SQL
temi_sql = [
    "Gestione di un sistema di e-commerce",
    "Sistema di prenotazione per voli aerei",
    "Gestione di un magazzino per un'azienda di logistica",
    "Sistema di tracciamento delle spedizioni",
    "Gestione di un ospedale",
    "Sistema di iscrizione universitaria",
    "Sistema di gestione delle biblioteche",
    "Tracciamento delle vendite di un negozio al dettaglio",
    "Gestione delle prenotazioni per un hotel",
    "Piattaforma di social media",
    "Sistema di gestione di una banca",
    "Sistema di fatturazione per un'azienda",
    "Sistema di gestione per una palestra",
    "Gestione di un ristorante",
    "Sistema di affitto di automobili",
    "Sistema di monitoraggio degli studenti di una scuola",
    "Gestione dei turni per i dipendenti di un'azienda",
    "Sistema di analisi finanziaria",
    "Gestione di un'agenzia di viaggi",
    "Sistema di tracciamento delle scorte di un negozio online",
    "Gestione di un portale di prenotazione eventi",
    "Sistema per la gestione di un'azienda agricola",
    "Sistema di supporto per un helpdesk IT",
    "Gestione delle iscrizioni ad una palestra",
    "Sistema di monitoraggio dei pazienti in un ospedale",
    "Gestione di un centro di assistenza clienti",
    "Sistema di gestione di un cinema",
    "Piattaforma di e-learning",
    "Gestione di una catena di ristoranti",
    "Sistema di gestione delle spedizioni internazionali",
    "Sistema di tracciamento degli ordini per un sito di e-commerce",
    "Gestione del noleggio di biciclette",
    "Gestione delle recensioni per un sito di viaggi",
    "Sistema di gestione per una scuola guida",
    "Sistema di prenotazione per spettacoli teatrali",
    "Gestione delle registrazioni per conferenze",
    "Sistema di monitoraggio per un magazzino alimentare",
    "Sistema di gestione per una cooperativa agricola",
    "Gestione delle operazioni di un centro fitness",
    "Sistema di gestione di una clinica veterinaria",
    "Sistema di tracciamento dei clienti per una startup"
]

def pdf_to_text(file_path):
    try:
        with pdfplumber.open(file_path) as pdf:
            text = ""
            for page in pdf.pages:
                text += page.extract_text() or ""
            logging.debug(f"Extracted text from {file_path}: {text[:100]}...")
            return text
    except Exception as e:
        logging.error(f"Error extracting text from {file_path}: {e}", exc_info=True)
        return ""

def initialise_llama3():
    try:
        logging.debug("Starting chatbot initialization...")
        
        # Prompt per l'esame SQL
        create_prompt_sql = ChatPromptTemplate.from_messages(
            [
                ("system", "Sei un insegnante universitario di database."),
                ("user", "Ecco un esempio di esami di query SQL:\n\n{sql_text}\n\n"
                         "Genera un esame finale simile con circa 11 esercizi SQL, "
                         "ma usa un tema diverso ogni volta. "
                         "Il tema scelto è: {theme}. "
                         "Non scrivere le query, procedure o trigger, ma solo la richiesta da porre allo studente. "
                         "Inserisci nel testo anche dati tramite insert per testare le query. "
                         "Includi almeno un trigger come ultima domanda.")
            ]
        )
        logging.debug("SQL Prompt template created successfully.")

        # Prompt per l'esame ERM
        create_prompt_erm = ChatPromptTemplate.from_messages(
            [
                ("system", "Sei un insegnante universitario di database."),
                ("user", "Ecco un esempio di esami progettazione ERM:\n\n{erm_text}\n\n"
                         "Genera un esame finale simile con circa 11 esercizi di progettazione ERM, "
                         "ma usa un tema diverso ogni volta. "
                         "Il tema scelto è: {theme}. "
                         "Scrivi solo le richieste da porre allo studente.")
            ]
        )
        logging.debug("ERM Prompt template created successfully.")

        llama_model = Ollama(model="llama3.2")
        logging.debug("Llama model initialized.")
        output_parser = StrOutputParser()
        logging.debug("Output parser initialized.")

        # Creazione delle pipeline per SQL e ERM
        chatbot_pipeline_sql = create_prompt_sql | llama_model | output_parser
        chatbot_pipeline_erm = create_prompt_erm | llama_model | output_parser  # Pipeline per ERM
        logging.debug("Chatbot pipelines created successfully.")

        return chatbot_pipeline_sql, chatbot_pipeline_erm

    except Exception as e:
        logging.error("Failed to initialize chatbot:", exc_info=True)
        raise

chatbot_pipeline_sql, chatbot_pipeline_erm = initialise_llama3()

def generate_pdf_exam(output_text):
    pdf_buffer = BytesIO()
    pdf = SimpleDocTemplate(pdf_buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    normal_style = styles['Normal']
    title_style = styles['Title']

    elements = []
    title = Paragraph("Esame SQL/ERM Generato", title_style)
    elements.append(title)
    elements.append(Spacer(1, 12))

    for paragraph in output_text.split("\n"):
        if paragraph.strip():
            elements.append(Paragraph(paragraph, normal_style))
            elements.append(Spacer(1, 12))

    pdf.build(elements)
    pdf_buffer.seek(0)
    return pdf_buffer

# Route per generare l'esame SQL e convertirlo in PDF
@app.route('/genera-esame-sql', methods=['POST'])
def genera_esame_sql():
    logging.debug("Received a POST request to /genera-esame-sql")
    sql_directory = 'uploads/sql'

    try:
        if not os.path.exists(sql_directory):
            return jsonify({"error": "La directory SQL non esiste"}), 404

        sql_text = ""
        for filename in os.listdir(sql_directory):
            if filename.endswith(".pdf"):
                file_path = os.path.join(sql_directory, filename)
                sql_text += pdf_to_text(file_path) + "\n"

        tema_casuale = random.choice(temi_sql)
        logging.debug(f"Tema SQL scelto: {tema_casuale}")

        response = chatbot_pipeline_sql.invoke({'sql_text': sql_text, 'theme': tema_casuale})
        output = format_output(response)
        logging.debug(f"Esame SQL generato con successo: {output}")

        pdf_buffer = generate_pdf_exam(output)
        return send_file(pdf_buffer, as_attachment=True, download_name="generated_exam_sql.pdf", mimetype='application/pdf')

    except Exception as e:
        logging.error(f"Errore durante la generazione dell'esame SQL: {e}", exc_info=True)
        return jsonify({"error": "Errore durante la generazione dell'esame SQL"}), 500

# Route per generare l'esame ERM e convertirlo in PDF
@app.route('/genera-esame-erm', methods=['POST'])
def genera_esame_erm():
    logging.debug("Received a POST request to /genera-esame-erm")
    erm_directory = 'uploads/erm'

    try:
        if not os.path.exists(erm_directory):
            return jsonify({"error": "La directory ERM non esiste"}), 404

        erm_text = ""
        for filename in os.listdir(erm_directory):
            if filename.endswith(".pdf"):
                file_path = os.path.join(erm_directory, filename)
                erm_text += pdf_to_text(file_path) + "\n"

        tema_casuale = random.choice(temi_sql)
        logging.debug(f"Tema ERM scelto: {tema_casuale}")

        # Invocazione per generare l'esame ERM
        response = chatbot_pipeline_erm.invoke({'erm_text': erm_text, 'theme': tema_casuale})  # Utilizza la pipeline per ERM
        output = format_output(response)
        logging.debug(f"Esame ERM generato con successo: {output}")

        pdf_buffer = generate_pdf_exam(output)
        return send_file(pdf_buffer, as_attachment=True, download_name="generated_exam_erm.pdf", mimetype='application/pdf')

    except Exception as e:
        logging.error(f"Errore durante la generazione dell'esame ERM: {e}", exc_info=True)
        return jsonify({"error": "Errore durante la generazione dell'esame ERM"}), 500

def format_output(response):
    formatted_output = response.strip()
    logging.debug(f"Formatted output: {formatted_output}")
    return formatted_output

if __name__ == '__main__':
    os.makedirs('uploads/sql', exist_ok=True)
    os.makedirs('uploads/erm', exist_ok=True)
    app.run(debug=True)