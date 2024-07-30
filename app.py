from flask import Flask, request, render_template, render_template_string, jsonify
from whoosh.index import create_in, open_dir
from whoosh.fields import Schema, TEXT
from whoosh.qparser import QueryParser
from whoosh.highlight import HtmlFormatter, WholeFragmenter, UppercaseFormatter
from bs4 import BeautifulSoup
import os
import re

# Konfiguracja Whoosh
if not os.path.exists("index"):
    os.mkdir("index")
schema = Schema(title=TEXT(stored=True), content=TEXT(stored=True))
ix = create_in("index", schema)

ix = open_dir("index")

def add_documents_from_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as file:
        title = file.readline().strip()  # Pierwsza linia jako tytuł
        content = file.read().strip()  # Reszta pliku jako treść
    writer = ix.writer()
    writer.add_document(title=title, content=content)
    writer.commit()
    print(f"Added: {title}")  # Informacja o dodanym dokumencie

# Załaduj dokumenty
add_documents_from_file('dokument.html')

app = Flask(__name__)

@app.route('/<name>.html')
def serve_html(name):
    return app.send_static_file(f'{name}.html')

@app.route('/')
def home():     
    return render_template('index.html')

def clean_html(html_content):
    """ Usuwa znaczniki HTML, zwracając czysty tekst. """
    soup = BeautifulSoup(html_content, "html.parser")
    return soup.get_text()

def extract_context(text, phrase, window=2):
    """
    Zwraca fragmenty tekstu zawierające frazę, otoczone zadaną liczbą słów (okno).
    Fraza jest wyróżniona poprzez pogrubienie.
    
    :param text: tekst źródłowy
    :param phrase: fraza do wyszukiwania
    :param window: liczba słów wokół frazy do zwrócenia
    """
    # Tworzenie regexa obejmującego 'window' słów przed i po frazie
    regex_pattern = r'\b(?:\S+\s+){0,%d}(\S*%s\S*)(?:\s+\S+){0,%d}\b' % (window, re.escape(phrase), window)
    matches = re.finditer(regex_pattern, text, re.IGNORECASE)
    context_snippets = []
    
    for match in matches:
        # Oznaczanie wyszukiwanej frazy tagami <strong>
        snippet = match.group(0)
        highlighted_phrase = match.group(1)
        highlighted_snippet = snippet.replace(highlighted_phrase, f"<strong>{highlighted_phrase}</strong>")
        context_snippets.append(highlighted_snippet)
    
    # Zwróć jako lista fragmentów
    return context_snippets

@app.route('/search')
def search():
    query_str = request.args.get('query')
    with ix.searcher() as searcher:
        query = QueryParser("content", ix.schema).parse(query_str)
        results = searcher.search(query)
        if results:
            result = results[0]  # Zakładamy, że interesuje nas tylko pierwszy wynik
            content = result['content']
            # Funkcja do podświetlenia terminów
            def highlight_terms(text, terms):
                for term in terms:
                    regex = re.compile(re.escape(term), re.IGNORECASE)
                    text = regex.sub(f"<span class='highlight'>{term}</span>", text)
                return text
            # Pobieranie wszystkich terminów z zapytania
            terms = set([word.lower() for word in query_str.split()])
            highlighted_content = highlight_terms(content, terms)
            return render_template_string('<h1>Wyniki dla: {{ query }}</h1>' +
                                          '<p>{{ content | safe }}</p>',
                                          query=query_str, content=highlighted_content)
        else:
            return f"Brak wyników dla: {query_str}"
        
@app.route('/autocomplete', methods=['GET'])
def autocomplete():
    query_prefix = request.args.get('prefix', '')
    suggestions = []
    with ix.searcher() as searcher:
        parser = QueryParser("content", ix.schema)
        query = parser.parse(f"{query_prefix}*")
        results = searcher.search(query, limit=5)
        for result in results:
            clean_text = clean_html(result['content'])
            context_snippet = extract_context(clean_text, query_prefix, window=2)
            suggestions.append({'title': result['title'], 'content': context_snippet})
    return jsonify(suggestions)


if __name__ == "__main__":
    app.run(debug=True)
