#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Sep 24 15:54:36 2020

@author: gabrielesavoia
"""

from whoosh.qparser import MultifieldParser
from whoosh.searching import Searcher as WhooshSearcher
from whoosh import scoring, qparser

from .queryExpansion import Expander


class WikiSearcher:

    weighting = {'TF_IDF' : scoring.TF_IDF,
                 'BM25F' : scoring.BM25F,
                 'FREQUENCY' : scoring.Frequency,
                }

    group = {'OR' : qparser.OrGroup,
             'AND' : qparser.AndGroup,
            }

    base_url = 'https://en.wikipedia.org/wiki/'
    
    def __init__(self, index, page_ranker):
        """
        Creazione del QueryParser relativo al testo della query.
        Aggiungo il plugin 'MultifieldPlugin' al 'QueryParser' perchè mi permette poi nella funzione di 
        'search' di poter modificare il filed boost (cosa che non siamo riusciti a fare se avessimo
        definito direttamente un 'MultifieldParser').

        - MULTIFIELD così effettuo ricerca sia nel titolo che nel testo.
                    Il parser utilizza l'analizzatore definito nell'index, riferito al field corrispondente.
                    Se ho definito 2 analyzer diversi per titolo e testo, questi vengono
                    usati rispettivamente per parsare la query per il titolo e per il testo.
                    ES: testo con stemmer e titolo senza stemmer:
                        query: 'fortified' --> query parsata :'(text:fortifi OR title:fortified)'
                             
        - GROUP default concatena i token con 'AND'. Specificando 'OrGroup' concatena con OR.
                Utilizzando il FACTORY, do un punteggio maggiore ai documenti in cui un certo termine
                ha una frequenza più alta. Senza FACTORY non ho questo effetto.     
        """
        self.index = index

        self.page_ranker = page_ranker

        self.expand = Expander(disambiguate_fn='noun_sense')

        self.parser = qparser.QueryParser(None, index.schema)
        self.multifield_plugin = qparser.MultifieldPlugin(['text', 'title'])
        self.parser.add_plugin(self.multifield_plugin)

        self.weighting = 'BM25F'
        self.searcher = WhooshSearcher(reader=self.index.reader(), weighting=WikiSearcher.weighting[self.weighting])
        
    
    def search(self, text, limit=10, exp=True, page_rank=True, text_boost=1.0, title_boost=1.0,
                weighting='BM25F', group='AND'):
        """
        Funzione che esegue la ricerca con i parametri passati in input.
        Se il pagerank è specificato, lo score finale del documento viene calcolato sia in funzione
        dello score fornito dalla ricerca che al valore di pagerank.

        Per prima cosa avviene la fase di settaggio del parser e del weighting con i valori passati in 
        input.
        Dopo di chè avviene il query expansion.
        Poi, avviene il parsing del testo, che viene passato al searcher che ottiene 
        i documenti rilevanti.

        :param self
        :param text: testo che verrà convertito in query dal parser
        :param limit: numero max di documenti ritornati
        :param exp: boolean se abilitare o meno il query expansion
        :param page_rank: boolean se abilitare o meno il pagerank
        :param text_boost: boosting del campo testo
        :param title_boost: boosting del campo titolo
        :param weighting: metodo di weighting
        :param group: come vengono concatenati i token della query

        return dict con i risultati.
        """
        self.multifield_plugin.boosts = {'text': text_boost, 'title': title_boost}
        self.parser.group = WikiSearcher.group.get(group, 'AND')

        text, list_token_expanded = self.expand(text) if exp else (text, None)
        query = self.parser.parse(text)
        
        if weighting != self.weighting:
            print('Imposto il searcher con il weighting : '+weighting+' Può impiegare tempo ...')
            self.searcher = WhooshSearcher(reader=self.index.reader(), 
                                           weighting=WikiSearcher.weighting.get(weighting, 'BM25F'))
            self.weighting = weighting
            print('Weighting impostato correttamente')

        #print('Query : '+str(query))

        res = {}
        results = self.searcher.search(query, limit=limit)

        res['time_second'] = results.runtime 
        res['expanded'] = list_token_expanded if exp else []
        res['n_res'] = results.estimated_length()

        final_score_fn, values_page_rank = self.__combinedScore(page_rank, results)
        if page_rank:
            results = sorted(results, key=final_score_fn, reverse=True)   

        res['docs'] = [{'link': WikiSearcher.base_url+result['title'].replace(" ", "_"),
                        'title': result['title'], 
                        'highlight': result.highlights("text", top=2),
                        'final_score': final_score_fn(result),
                        'score': result.score,
                        'page_rank': values_page_rank.get(result['id_page'], -1)
                        } for result in results]

        return res


    def __combinedScore(self, page_rank, results):
        """
        Ritorna il riferimento alla funzione usata per il calcolo dello score finale combinato con 
        il valore di pagerank. In questa funzione ricavo, tramite il 'getRank' del 'pageRanker', 
        i valori di pagerank che ho calcolato in precedenza.

        :param self
        :param page_rank: boolean per capire se serve usare il pagerank per la query corrente
        :param results: risultati della query 
        """
        values_page_rank = {}
        if page_rank:
            values_page_rank = self.page_ranker.getRank([res['id_page'] for res in results], 5)

        def final_score_fn(result):
            if page_rank:
                return result.score * values_page_rank.get(result['id_page'], 1)
            return result.score

        return final_score_fn, values_page_rank


    def getFieldInfo(self, field):
        """
        Ottengo le informazioni riferite al field.
        Funzione utile in fase di debug.
        
        :param field: field di cui voglio le informazioni
        return dict con le info del field specificato
        """
        return {'length': self.searcher.field_length(field)}


    def getGeneralInfo(self):
        """
        Ottengo le informazioni generali riferite all'indice.
        Funzione utile in fase di debug.
        
        :param self:
        return dict con le info
        """
        return {'doc_count': self.searcher.doc_count()}