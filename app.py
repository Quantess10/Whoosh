from flask import Flask, request, render_template
from whoosh.index import create_in
from whoosh.fields import Schema, TEXT
from whoosh.qparser import QueryParser
import os

# Konfiguracja Whoosh
if not os.path.exists("index"):
    os.mkdir("index")
schema = Schema(title=TEXT(stored=True), content=TEXT(stored=True))
ix = create_in("index", schema)

def add_documents_from_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as file:
        docs = file.read().strip().split('---')  # Usunięcie zbędnych białych znaków na początku i końcu oraz podział dokumentów
    writer = ix.writer()
    for doc in docs:
        if doc.strip():  # Upewnij się, że dokument nie jest pusty
            lines = doc.strip().split('\n')
            title = lines[0].strip()
            content = '\n'.join(line.strip() for line in lines[1:] if line.strip())  # Usunięcie zbędnych białych znaków z każdej linii treści
            writer.add_document(title=title, content=content)
            print(f"Added: {title}")  # Sprawdź, co zostało dodane
    writer.commit()

# Załaduj dokumenty
add_documents_from_file('documents.txt')

app = Flask(__name__)

@app.route('/<name>.html')
def serve_html(name):
    return app.send_static_file(f'{name}.html')

@app.route('/')
def home():     
    return render_template('index.html')

# Endpoint do obsługi wyszukiwania
@app.route('/search')
def search():
    query_str = request.args.get('query')
    with ix.searcher() as searcher:
        query = QueryParser("content", ix.schema).parse(query_str)
        results = searcher.search(query)
        results_html = '<ul>' + ''.join(f"<li>{result['title']}: {result.highlights('content')}</li>" for result in results) + '</ul>'
    return results_html

if __name__ == "__main__":
    app.run(debug=True)
