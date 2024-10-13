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
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.units import inch
from io import BytesIO
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
from datetime import datetime
from functools import wraps

logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)
CORS(app)

#Per caricare i font
pdfmetrics.registerFont(TTFont('DejaVuSans', 'DejaVuSans.ttf'))

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

# Token fisso, da utilizzare per la verifica
FIXED_TOKEN = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c'

def pdf_to_text(file_path):
    try:
        with pdfplumber.open(file_path) as pdf:
            text = "".join(page.extract_text() or "" for page in pdf.pages)
            logging.debug(f"Extracted text from {file_path}: {text[:100]}...")
            return text
    except Exception as e:
        logging.error(f"Error extracting text from {file_path}: {e}", exc_info=True)
        return ""

def token_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token or token != f'Bearer {FIXED_TOKEN}':
            logging.warning("Access denied: Invalid token")
            return jsonify({"error": "Access denied: Invalid token"}), 403
        return f(*args, **kwargs)
    return decorated_function

def initialise_llama3():
    try:
        logging.debug("Starting chatbot initialization...")

        # Prompt per l'esame SQL
        create_prompt_sql = ChatPromptTemplate.from_messages(
            [
                ("system", "Sei un insegnante universitario di database."),
                ("user", "Ecco un esempio di esami di query SQL:\n\n{sql_text}\n\n"
                         "Genera un esame finale simile con 11 esercizi SQL, "
                         "ma usa un tema diverso ogni volta. "
                         "Il tema scelto è: {theme}. "
                         "Non scrivere le query, procedure o trigger, ma limitati solo alle richiesta da porre allo studente senza commenti iniziali o finali. "
                         "Inserisci nel testo anche dati tramite insert per testare le query. "
                         "Includi almeno un trigger come ultima domanda."
                         "Non mettere note"
                         "Assicurati che il testo dell'esame sia coerente con il tema scelto."
                )
            ]
        )
        logging.debug("SQL Prompt template created successfully.")

        # Prompt per l'esame ERM
        create_prompt_erm = ChatPromptTemplate.from_messages(
            [
                ("system", "Sei un insegnante universitario di database."),
                ("user", "Ecco un esempio di esami di progettazione ERM:\n\n{erm_text}\n\n"
                         "Genera un esame finale simile, "
                         "ma usa un tema diverso ogni volta. "
                         "Il tema scelto è: {theme}. "
                         "limitati a scrivere solo il testo dell'esame e le richiesta da porre allo studente senza commenti iniziali o finali. "
                         "Non svolgere gli esercizi. "
                         "L'esame deve sempre avere: Le operazioni, la tabella delle operazioni e la tabella dei volumi. Queste due tabelle devono essere separate tra loro."
                         "Non mettere note"
                         "Assicurati che il testo dell'esame sia coerente con il tema scelto."
                )
            ]
        )
        
        create_prompt_sql_solution = ChatPromptTemplate.from_messages(
            [
                ("system", "Sei un insegnante universitario di database."),
                ("user", "Questo è l'esame SQL:\n\n{sql_text}\n\n"
                         "Genera la soluzione completa per ogni esercizio dell'esame."
                         "Assicurati che la soluzione sia dettagliata e corretta."
                         "Assicurati di scrivere la soluzione di 11 esercizi"
                         "Usa la sintassi di MYSQL"
                )
            ]
        )
        
        logging.debug("ERM Prompt template created successfully.")

        llama_model = Ollama(model="llama3.1:8b")
        logging.debug("Llama model initialized.")
        output_parser = StrOutputParser()
        logging.debug("Output parser initialized.")

        # Creazione delle pipeline per SQL e ERM
        chatbot_pipeline_sql = create_prompt_sql | llama_model | output_parser
        chatbot_pipeline_erm = create_prompt_erm | llama_model | output_parser 
        chatbot_pipeline_sql_solution = create_prompt_sql_solution | llama_model | output_parser
        logging.debug("Chatbot pipelines created successfully.")

        return chatbot_pipeline_sql, chatbot_pipeline_erm, chatbot_pipeline_sql_solution

    except Exception as e:
        logging.error("Failed to initialize chatbot:", exc_info=True)
        raise

chatbot_pipeline_sql, chatbot_pipeline_erm, chatbot_pipeline_sql_solution = initialise_llama3()

def generate_pdf_exam(output_text):
    pdf_buffer = BytesIO()
    pdf = SimpleDocTemplate(pdf_buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    normal_style = ParagraphStyle(
        'NormalWithSymbols',
        parent=styles['Normal'],
        fontName='DejaVuSans',
        encoding='UTF-8'
    )

    title_style = styles['Title']

    elements = []

    # Ottieni la data corrente e formatta il titolo per metterlo all'inizio dell'esame
    current_date = datetime.now().strftime("%d/%m/%Y")
    title_text = f"Esame di Database - {current_date}"
    title = Paragraph(title_text, title_style)

    elements.append(title)
    elements.append(Spacer(1, 12))

    #*fields_style = styles['Normal']
    #elements.append(Paragraph("Nome: _______________________", fields_style))
    #elements.append(Spacer(1, 12))
    #elements.append(Paragraph("Cognome: _______________________", fields_style))
    #elements.append(Spacer(1, 12))
    #elements.append(Paragraph("Matricola: _______________________", fields_style))
    #elements.append(Spacer(1, 12))
    
    output_text = output_text.replace("->", "→").replace("<-", "←")

    for paragraph in output_text.split("\n"):
        if paragraph.strip():
            elements.append(Paragraph(paragraph, normal_style))
            elements.append(Spacer(1, 12))

    pdf.build(elements)
    pdf_buffer.seek(0)
    return pdf_buffer

# Route per generare l'esame SQL e convertirlo in PDF

@app.route('/genera-esame-sql', methods=['POST'])
@token_required
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

        # Crea un nuovo buffer per ogni chiamata
        pdf_buffer = generate_pdf_exam(output)
        current_date = datetime.now().strftime("%Y%m%d")
        filename = f"Esame_SQL{current_date}.pdf"

        return send_file(pdf_buffer, as_attachment=True, download_name=filename, mimetype='application/pdf')

    except Exception as e:
        logging.error(f"Errore durante la generazione dell'esame SQL: {e}", exc_info=True)
        return jsonify({"error": "Errore durante la generazione dell'esame SQL"}), 500

@app.route('/genera-esame-erm', methods=['POST'])
@token_required
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

        response = chatbot_pipeline_erm.invoke({'erm_text': erm_text, 'theme': tema_casuale})
        output = format_output(response)
        logging.debug(f"Esame ERM generato con successo: {output}")

        # Crea un nuovo buffer per ogni chiamata
        pdf_buffer = generate_pdf_exam(output)

        # Nome dinamico basato sulla data
        current_date = datetime.now().strftime("%Y%m%d")
        filename = f"Esame_ERM{current_date}.pdf"

        return send_file(pdf_buffer, as_attachment=True, download_name=filename, mimetype='application/pdf')

    except Exception as e:
        logging.error(f"Errore durante la generazione dell'esame ERM: {e}", exc_info=True)
        return jsonify({"error": "Errore durante la generazione dell'esame ERM"}), 500

@app.route('/genera-soluzione-sql', methods=['POST'])
@token_required
def genera_soluzione_sql():
    logging.debug("Received a POST request to /genera-soluzione-sql")
    sql_directory = 'uploads/sql'

    try:
        # Crea la directory se non esiste
        if not os.path.exists(sql_directory):
            os.makedirs(sql_directory)

        # Controlla se il file è stato caricato
        if 'file' not in request.files:
            return jsonify({"error": "Nessun file caricato"}), 400

        file = request.files['file']  # Ottiene il file caricato

        if file.filename == '':
            return jsonify({"error": "Nome del file non valido"}), 400

        # Salva il file caricato
        file_path = os.path.join(sql_directory, file.filename)
        file.save(file_path)
        logging.debug(f"File salvato con successo: {file_path}")

        # Estrai il testo dall'esame SQL PDF
        sql_text = pdf_to_text(file_path)
        logging.debug(f"Testo estratto dall'esame SQL: {sql_text[:100]}...")

        logging.debug("Generazione della soluzione SQL in corso...")

        # Invoca il chatbot per generare la soluzione SQL
        response = chatbot_pipeline_sql_solution.invoke({'sql_text': sql_text})
        output = format_output(response)
        logging.debug(f"Soluzione SQL generata con successo: {output}")

        # Crea un nuovo buffer per ogni chiamata
        pdf_buffer = generate_pdf_exam(output)

        # Nome dinamico basato sulla data
        current_date = datetime.now().strftime("%Y%m%d")
        filename = f"Soluzione_SQL{current_date}.pdf"

        return send_file(pdf_buffer, as_attachment=True, download_name=filename, mimetype='application/pdf')

    except Exception as e:
        logging.error(f"Errore durante la generazione della soluzione SQL: {e}", exc_info=True)
        return jsonify({"error": "Errore durante la generazione della soluzione SQL"}), 500


def format_output(response):
    formatted_output = response.strip()
    logging.debug(f"Formatted output: {formatted_output}")
    return formatted_output

if __name__ == '__main__':
    os.makedirs('uploads/sql', exist_ok=True)
    os.makedirs('uploads/erm', exist_ok=True)
    app.run(debug=True)
