import spacy
from spacy.matcher import Matcher
import re
from typing import List, Dict, Tuple, Optional

# Tenta carregar o modelo spaCy para português
try:
    nlp = spacy.load("pt_core_news_md") # Tenta carregar modelo médio
    print("Modelo spaCy 'pt_core_news_md' carregado.")
except OSError:
    print("Modelo 'pt_core_news_md' não encontrado. Tentando 'pt_core_news_sm'...")
    try:
        nlp = spacy.load("pt_core_news_sm")
        print("Modelo spaCy 'pt_core_news_sm' carregado.")
    except OSError:
        print("ERRO CRÍTICO: Nenhum modelo de português do spaCy encontrado (sm ou md). Instale um: python -m spacy download pt_core_news_sm")
        nlp = None 

# Dicionário expandido para quantidades
text_to_num = {
    "um": 1, "uma": 1, "meio": 0.5, "meia": 0.5, # Adicionado meio/meia
    "dois": 2, "duas": 2,
    "três": 3, "quatro": 4, "cinco": 5,
    "seis": 6, "sete": 7, "oito": 8, "nove": 9, "dez": 10,
    "onze": 11, "doze": 12, "dúzia": 12, "duzia": 12, # Adicionado dúzia
    "treze": 13, "catorze": 14, "quatorze": 14, "quinze": 15,
    # Adicionar mais se necessário...
}

# Regex para tentar pegar números antes ou depois de palavras-chave
# Ex: "2 cafés", "cafés 2", "1 duzia", "duzia 1" (após normalize_text)
NUM_KEYWORD_PATTERN = re.compile(r"(\d+(?:\.\d+)?)\s+(.+)") # Ex: 1.5 pao de queijo
KEYWORD_NUM_PATTERN = re.compile(r"(.+)\s+(\d+(?:\.\d+)?)") # Ex: pao de queijo 1.5

def normalize_text(text: str) -> str:
    """ Limpa texto, converte numerais por extenso e 'meia duzia'. """
    text = text.lower()
    # Remove pontuação básica
    text = re.sub(r'[.,!?]', '', text)
    # Trata "meia duzia" antes da conversão de números
    text = re.sub(r'meia\s+(?:dúzia|duzia)', '6', text)

    words = text.split()
    normalized_words = []
    for word in words:
        normalized_words.append(str(text_to_num.get(word, word))) # Converte ou mantém original
    return " ".join(normalized_words)

def find_keyword_match(text_fragment: str, product_keywords: List[str]) -> Optional[str]:
    text_fragment_lower = text_fragment.lower().strip()
    possible_matches = []
    for kw in product_keywords:
        if text_fragment_lower in kw.lower():
            possible_matches.append(kw)
    
    if not possible_matches:
        return None
    
    return max(possible_matches, key=len)


def parse_order_text(text: str, product_keywords: List[str]) -> List[Dict]:
    if nlp is None:
        print("Erro: Modelo spaCy não carregado.")
        return []

    processed_text = normalize_text(text)
    doc = nlp(processed_text)
    found_items_map = {} 
    processed_indices = set()

    matcher = Matcher(nlp.vocab)
    
    for keyword in product_keywords:
        kw_lower_parts = keyword.lower().split()
        
        num_pattern = [{"LIKE_NUM": True}] + [{"LOWER": part} for part in kw_lower_parts]
        matcher.add(keyword, [num_pattern]) 

        keyword_pattern = [{"LOWER": part} for part in kw_lower_parts] + [{"LIKE_NUM": True}]
        matcher.add(keyword + "_NUM_AFTER", [keyword_pattern])

        matcher.add(keyword + "_SOLO", [[{"LOWER": part} for part in kw_lower_parts]])

    matches = matcher(doc)
    
    matches.sort(key=lambda x: (x[1], -(x[2] - x[1]))) 

    for match_id, start, end in matches:
        if any(i in processed_indices for i in range(start, end)):
            continue 

        rule_id_str = nlp.vocab.strings[match_id]
        span = doc[start:end]
        
        quantity = 1.0
        keyword_match = rule_id_str.replace("_NUM_AFTER", "").replace("_SOLO", "") 

        try:
            if "_NUM_AFTER" in rule_id_str:
                 quantity = float(span[-1].text) 
            elif "_SOLO" in rule_id_str:
                 quantity = 1.0
            else:
                 quantity = float(span[0].text)
        except ValueError:
            quantity = 1.0 # Fallback

        processed_indices.update(range(start, end))

        final_quantity = int(quantity) if quantity == int(quantity) else quantity
        existing_quantity = found_items_map.get(keyword_match, 0)
        found_items_map[keyword_match] = existing_quantity + final_quantity
        print(f"Matcher processou: {final_quantity} x '{keyword_match}' (Índices: {start}-{end-1})")



    if not found_items_map:
        remaining_tokens = [token for i, token in enumerate(doc) if i not in processed_indices]

        current_phrase = []
        for token in remaining_tokens:
             current_phrase.append(token.lower_)
             phrase_str = " ".join(current_phrase)
             
             found_kw = None
             for kw in sorted(product_keywords, key=len, reverse=True):
                  if phrase_str == kw.lower():
                      found_kw = kw
                      break 

             if found_kw:
                 if found_kw not in found_items_map: 
                      found_items_map[found_kw] = 1 
                      processed_indices.update(range(token.i - len(current_phrase) + 1, token.i + 1))
                      print(f"Fallback (exato) encontrou: 1 x '{found_kw}'")
                 current_phrase = [] # Reseta a frase
             elif not any(kw.lower().startswith(phrase_str) for kw in product_keywords):
                  current_phrase = []

    # Converte o mapa para o formato de lista esperado
    final_list = [{"product_guess": kw, "quantity": qty} for kw, qty in found_items_map.items()]

    print(f"IA 1 (NLU) - Final items para '{text}': {final_list}") 

    if not final_list:
        print("Nenhum item do cardápio identificado no pedido.")
    
    return final_list