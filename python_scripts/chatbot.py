from PyPDF2 import PdfReader
import cohere

# Function to extract text from PDF
def extract_text_from_pdf(pdf_path):
    text = ""
    with open(pdf_path, "rb") as file:
        reader = PdfReader(file)
        for page in reader.pages:
            text += page.extract_text()
    return text

# Split text into chunks
def split_text_into_chunks(text, max_tokens=1000):
    words = text.split()
    chunks = []
    for i in range(0, len(words), max_tokens):
        chunks.append(' '.join(words[i:i + max_tokens]))
    return chunks

# Initialize Cohere API client
def initialize_cohere(api_key):
    return cohere.Client(api_key)

# Function to query Cohere with the extracted text and user question
def query_cohere(client, chunks, question, max_tokens=1000):
    answers = []
    for chunk in chunks:
        response = client.generate(
            prompt=f"{chunk}\n\nQ: {question}\nA:",
            max_tokens=100,  # Adjust based on your needs
            temperature=0.5,
            k=0,
            stop_sequences=["\n"]
        )
        answers.append(response.generations[0].text.strip())
    return ' '.join(answers)
