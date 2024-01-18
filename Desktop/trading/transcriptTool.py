
import os, glob, dash, nltk, spacy, PyPDF2, string
from dash import html, dcc
from nltk.stem import WordNetLemmatizer, PorterStemmer
from nltk.corpus import stopwords
from collections import Counter

nlp = spacy.load("en_core_web_sm")
stopWords = set(stopwords.words('english') + list(string.punctuation))

class FileAnalyzer:
    def __init__(self, folderPath, format='lemmatized'):
        self.folderPath = folderPath
        self.format = format
        self.latestFile = max(glob.glob(f"{self.folderPath}\\*"), key=os.path.getctime, default=None)
        self.content = (self.readFile() or "").lower()

    def readFile(self):
        if not self.latestFile: 
            return None
        try:
            with open(self.latestFile, 'rb' if self.latestFile.endswith('.pdf') else 'r', encoding=None if self.latestFile.endswith('.pdf') else 'utf-8') as file:
                if self.latestFile.endswith('.pdf'):
                    reader = PyPDF2.PdfReader(file)
                    content = ''.join([page.extract_text() for page in reader.pages])
                else:
                    content = file.read()
                return self.cleanText(content)
        except Exception as e:
            print(f"Error reading file: {e}")
            return None

    def cleanText(self, text):
        text = text.translate(str.maketrans('', '', string.punctuation)).lower()
        if self.format == 'lemmatized': return ' '.join([WordNetLemmatizer().lemmatize(word) for word in nltk.word_tokenize(text)])
        if self.format == 'stemmed': return ' '.join([PorterStemmer().stem(word) for word in nltk.word_tokenize(text)])
        return text

    def analyzeWords(self, wordList):
        return {word: Counter(nltk.word_tokenize(self.content))[word] for word in wordList}

    def extractKeywords(self, numKeywords=10):
        filteredWords = [word for word in nltk.word_tokenize(self.content) if word.lower() not in stopWords and word.isalpha()]
        return [word for word, _ in Counter(filteredWords).most_common(numKeywords)]

    def performNER(self):
        topEntities = {"ORG": [], "GPE": [], "PERSON": []}
        for entity, _ in Counter([(entity.text, entity.label_) for entity in nlp(self.content).ents if entity.label_ in topEntities]).most_common():
            if len(topEntities[entity[1]]) < 5: topEntities[entity[1]].append(entity[0])
        return topEntities
    
    def findCoOccurrences(self, wordList, windowSize=2):
        tokens = nltk.word_tokenize(self.content)
        coOccurrences = Counter()
        for i in range(len(tokens) - windowSize + 1):
            window = tokens[i:i + windowSize]
            for word1 in window:
                for word2 in window:
                    if word1 in wordList and word2 in wordList and word1 != word2:
                        coOccurrences[(word1, word2)] += 1
        return coOccurrences

    def detectPhrases(self, threshold=5):
        tokens = [word.lower() for word in nltk.word_tokenize(self.content) if word.isalpha()]
        bigramFinder = nltk.collocations.BigramCollocationFinder.from_words(tokens)
        bigramFinder.apply_freq_filter(threshold)
        bigramMeasures = nltk.collocations.BigramAssocMeasures()
        phrases = bigramFinder.nbest(bigramMeasures.pmi, 10)
        return [' '.join(phrase) for phrase in phrases]
    def summarizeWithGPT(self):
        summarizer = pipeline("text-generation", model="gpt-3.5-turbo")
        prompt = "Summarize this text: " + self.content
        summarized_text = summarizer(prompt, max_length=150, num_return_sequences=1)[0]['generated_text']
        return summarized_text
    
def createDashboard(analyzer, positiveCount, negativeCount, keywords, namedEntities, coOccurrences, phrases):
    app = dash.Dash(__name__)
    colors = {'background': '#F5F5F5', 'text': '#333333', 'positiveBar': '#2ca02c', 'negativeBar': '#d62728'}
    entitySections = ['ORG', 'GPE', 'PERSON']

    # Format co-occurrences for display
    formattedCoOccurrences = [f"{pair[0]} & {pair[1]}: {count}" for pair, count in coOccurrences.items()]

    return html.Div(style={'backgroundColor': colors['background']}, children=[
        html.H1("Financial Report Analysis", style={'textAlign': 'center', 'color': colors['text']}),
        *[
            dcc.Graph(id=f'{sentiment}-words-chart', figure={'data': [{'x': sorted(count, key=count.get, reverse=True), 'y': sorted(count.values(), reverse=True), 'type': 'bar', 'name': sentiment.title(), 'marker': {'color': colors[f'{sentiment}Bar']}}], 'layout': {'title': f'{sentiment.title()} Financial Words', 'plot_bgcolor': colors['background'], 'paper_bgcolor': colors['background'], 'font': {'color': colors['text']}}})
            for sentiment, count in [('positive', positiveCount), ('negative', negativeCount)]],
        html.H2("Top Keywords", style={'color': colors['text']}), html.Ul([html.Li(keyword, style={'color': colors['text']}) for keyword in keywords]),
        html.H2("Named Entities", style={'color': colors['text']}), html.Div([html.Div([html.H3(f"{entityType} ({entityType[0]})", style={'color': colors['text']}), html.Ul([html.Li(entity, style={'color': colors['text']}) for entity in namedEntities[entityType]])], className='four columns') for entityType in entitySections], className='row'),
        html.H2("Word Co-Occurrences", style={'color': colors['text']}), html.Ul([html.Li(coOccurrence, style={'color': colors['text']}) for coOccurrence in formattedCoOccurrences]),
        html.H2("Detected Phrases", style={'color': colors['text']}), html.Ul([html.Li(phrase, style={'color': colors['text']}) for phrase in phrases])])

if __name__ == "__main__":
    folderPath = 'W:\\Praktikanten und Werkstudenten\\Benjamin Suermann\\conferenceCalls'
    analyzer = FileAnalyzer(folderPath, format='normal')
    positiveWords = ['profit', 'gain', 'growth', 'bullish', 'upswing', 'improvement', 'increase', 'advantage', 'yield', 'success', 'revenue', 'surge', 'boom', 'upturn', 'prosperity']
    negativeWords = ['loss', 'decline', 'fall', 'bearish', 'downturn', 'decrease', 'disadvantage', 'drop', 'risk', 'failure', 'debt', 'slump', 'recession', 'dip', 'volatility']
    coOccurrences = analyzer.findCoOccurrences(positiveWords + negativeWords)
    phrases = analyzer.detectPhrases()

    app_layout = createDashboard(analyzer, analyzer.analyzeWords(positiveWords), analyzer.analyzeWords(negativeWords), analyzer.extractKeywords(), analyzer.performNER(), coOccurrences, phrases)
    app = dash.Dash(__name__)
    app.layout = app_layout
    app.run_server(debug=True)
