#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Sep 26 15:21:04 2020

@author: gabrielesavoia
"""

import nltk    
from nltk.corpus import wordnet as wn  
from nltk.wsd import lesk

def nounSenseDisambiguate_original(tokens):
    """
    index_terms : sono i termini del contesto che devo disambiguare.
    
    Per ogni index_term Tx, devo assegnarli il proprio significato corretto in base 
    al contesto in cui si trova.
    Per ogni suo significato TSi, calcolo uno score :
        1) per ogni termine Ty != Tx mi ricavo il max_score ovvero il valore max 
           di similarità tra TSi e OGNI significato di Ty
        2) sommo il max_score di ogni Ty e ottengo lo score di TSi
    A questo punto ho che ogni significato Tsi ha un proprio score e quindi
    assegno come significato al termine Tx quello che ha score maggiore.

    :param tokens: ovvero il testo tokenizzato
    return: dict composto dalla parola di partenza, il suo senso e lo score associato
    """
    res = []
        
    for index_term in tokens:
        if len(wn.synsets(index_term, wn.NOUN)) == 0:  # se token non riconosciuto
            continue
        best_sense = wn.synsets(index_term, wn.NOUN)[0]
        best_score = 0.0
        for candidate_sense in wn.synsets(index_term, wn.NOUN):
            score = 0.0            
            for other_term in tokens:
                if other_term==index_term:
                    continue
                max_score = 0.0   
                for possible_sense in wn.synsets(other_term, wn.NOUN):
                    tmp_score = candidate_sense.wup_similarity(possible_sense)
                    if tmp_score > max_score:
                        max_score = tmp_score
                score += max_score
            if score > best_score:
                best_score = score
                best_sense = candidate_sense
        res.append({'word': index_term, 'sense': best_sense, 'score':best_score})
    return res

def expansion_(text, n=2):
    """
    Query expansion basata sui sinonimi dei nomi della query. 
    
    Ricavo i nomi dalla query, per poi effettuare una disambiguazione tra essi 
    e salvarmi i primi n sinonimi trovati per ogni nome.

    Per ogni sinonimo tolgo gli eventuali trattini (questo può portare al fatto che un singolo sinonimo
    abbia più token).
    Elimino inoltre i sinonimi che sono già presenti nella query.
    
    :param n: per ogni nome vengono salvati al più n sinonimi
    """
    tokens = nltk.word_tokenize(text)
    name_tokens = [token[0] for token in nltk.pos_tag(tokens)
                          if token[1][0:2] == 'NN']

    disambiguated_name = nounSenseDisambiguate(name_tokens)
    res = []
    for name in disambiguated_name:
        synonyms = name['sense'].lemma_names()
        n_added = 0
        
        for synonym in synonyms:
            
            synonym = synonym.lower().replace(name['word'].lower(), "")
            synonym = synonym.replace('_', " ")
            synonym = synonym.replace('-', " ")
            synonym = synonym.strip()
            
            # può capitare che ottenga ad esempio 'free_energy' che l'ha trovato come sinonimio di 'energy'.
            # Allora essendo che nelle righe prima ho sosituito '_' , con lo spazio, adesso ho 
            # 1 sinonimo ma con 2 token. Quindi eseguo lo split in modo da ottenre una lista di token
            # ['free', 'energy'] per poi eseguire i controlli di esistenza.
            splitted_syn = synonym.split() 
            
            # aggiungo all'expansion solo i token del sinonimo che:
            #   - non sono presenti nei token della query
            #   - non sono uguali ad altri token trovati durante l'espansione
            #   - non siano vuoti
            for s in splitted_syn:  
                to_add = s not in res and s not in [t['word'] for t in disambiguated_name]
                s = '' if len(s)==1 else s
                if s.strip() != '' and n_added<n and to_add:
                    res.append(s)
                    n_added += 1
    return res





















def nounSenseDisambiguate(tokens, index_term, **kwargs):
    """
    index_terms : sono i termini del contesto che devo disambiguare.
    
    Per ogni index_term Tx, devo assegnarli il proprio significato corretto in base 
    al contesto in cui si trova.
    Per ogni suo significato TxSi, calcolo uno score score_TxSi :
        1) per ogni termine Ty != Tx mi ricavo il max_score ovvero il valore max 
           di similarità tra TxSi e OGNI significato TySz di Ty
        2) sommo il max_score di ogni Ty e ottengo lo score score_TxSi di TxSi
    A questo punto ho che ogni significato Tsi ha un proprio score score_TxSi e quindi
    assegno come significato al termine Tx quello che ha score maggiore (best_score).

    :param tokens: ovvero il testo tokenizzato
    return: dict composto dalla parola di partenza, il suo senso e lo score associato
    """
    Tx = index_term

    if len(wn.synsets(Tx, wn.NOUN)) == 0:  # se token non riconosciuto
        return None
    best_sense = wn.synsets(Tx, wn.NOUN)[0]
    best_score = 0.0
    for TxSi in wn.synsets(Tx, wn.NOUN):
        score_TxSi = 0.0            
        for Ty in tokens:
            if Ty==Tx:
                continue
            max_score = 0.0   
            for TySz in wn.synsets(Ty, wn.NOUN):
                tmp_score = TxSi.wup_similarity(TySz)
                if tmp_score > max_score:
                    max_score = tmp_score
            score_TxSi += max_score
        if score_TxSi > best_score:
            best_score = score_TxSi
            best_sense = TxSi
    return best_sense


def stopwordRemove(tokens):
    stopword = nltk.corpus.stopwords.words('english')
    return [token for token in tokens if token not in stopword]

def getSynonyms(synset):
    if synset is not None:
        return synset.lemma_names()
    return []


def expansion(text, disambiguate_fn, n=2):
    """
    Query expansion basata sui sinonimi dei nomi della query. 
    
    Ricavo i nomi dalla query, per poi effettuare una disambiguazione tra essi 
    e salvarmi i primi n sinonimi trovati per ogni nome.

    Per ogni sinonimo tolgo gli eventuali trattini (questo può portare al fatto che un singolo sinonimo
    abbia più token).
    Elimino inoltre i sinonimi che sono già presenti nella query.
    
    :param n: per ogni nome vengono salvati al più n sinonimi
    """
    tokens = stopwordRemove(nltk.word_tokenize(text))

    res=[]
    for token in tokens:
        best_sense = disambiguate_fn(tokens, token)

        synonyms = getSynonyms(best_sense)

        for synonym in synonyms:
            synonym = synonym.lower().replace(token, "")
            synonym = synonym.replace('_', " ")
            synonym = synonym.replace('-', " ")
            synonym = synonym.strip()

            splitted_syn = synonym.split()

            for s in splitted_syn:  
                if s not in res and len(s)>2 and s.strip()!='':
                    res.append(s)
    return res


def expand_query(text):
    list_token_expanded = expansion(text, nounSenseDisambiguate)
    expandend = ' OR ( '+' OR '.join(list_token_expanded)+' )'
    return ('( '+text+' )'+expandend, list_token_expanded)

"""
queries = set(('DNA', 'apple', 'Epigenetics', 'Hollywood', 'Maya',
                   'Microsoft', 'Precision', 'Tuscany', '99 balloons',
                   'Computer Programming', 'Financial meltdown',
                   'Justin Timberlake', 'Least Squares', 'Mars robots',
                   'Page six', 'Roman Empire', 'Solar energy', 'Statistical Significance',
                   'Steve Jobs', 'The Maya', 'Triple Cross', 'US Constitution',
                   'Eye of Horus', 'Madam I’m Adam', 'Mean Average Precision', 
                   'Physics Nobel Prizes', 'Read the manual', 'Spanish Civil War',
                   'Do geese see god', 'Much ado about nothing'))

for query in queries:
    print('query : '+ query)
    print('res 1 : ',expansion(query, nounSenseDisambiguate))
    print('res 2 : ',expansion(query, lesk)) 

"""



