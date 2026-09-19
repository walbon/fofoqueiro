"""
Fofoqueiro – Cliente 9router via HTTP (OpenAI-compatible)
"""
import httpx, json, re, time
from config import NINEROUTER_BASE_URL, NINEROUTER_API_KEY, NINEROUTER_MODEL

_headers = {
    "Authorization": f"Bearer {NINEROUTER_API_KEY}",
    "Content-Type": "application/json",
}

MAX_RETRIES = 5
TIMEOUT_SECONDS = 120.0  # Timeout expandido para 120 segundos

def _call_llm(messages: list[dict], temperature: float = 0.2) -> str:
    """Chama 9router com até 5 tentativas (retries) e timeout estendido de 120s."""
    payload = {
        "model": NINEROUTER_MODEL,
        "messages": messages,
        "temperature": temperature,
        "stream": False,          # pede resposta não-streaming
    }
    url = f"{NINEROUTER_BASE_URL.rstrip('/')}/chat/completions"

    last_exception = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            with httpx.Client(timeout=TIMEOUT_SECONDS) as client:
                resp = client.post(url, headers=_headers, json=payload)
                resp.raise_for_status()
                body = resp.text.strip()

                # Resposta JSON normal (não-streaming)
                if body.startswith("{"):
                    data = json.loads(body)
                    return data["choices"][0]["message"]["content"].strip()

                # Fallback: resposta em modo SSE (data: {...}\n)
                full_content = ""
                for line in body.splitlines():
                    line = line.strip()
                    if not line.startswith("data: "):
                        continue
                    chunk_str = line[6:]
                    if chunk_str == "[DONE]":
                        break
                    try:
                        chunk = json.loads(chunk_str)
                        delta = chunk["choices"][0].get("delta", {})
                        full_content += delta.get("content", "")
                    except (json.JSONDecodeError, KeyError, IndexError):
                        continue
                
                if full_content.strip():
                    return full_content.strip()

                raise ValueError("Resposta vazia da API do 9router")

        except Exception as e:
            last_exception = e
            print(f"[AIService] Tentativa {attempt}/{MAX_RETRIES} falhou ({e})... Retentando em {attempt * 2}s")
            if attempt < MAX_RETRIES:
                time.sleep(attempt * 2)  # Backoff exponencial simples (2s, 4s, 6s, 8s...)

    # Se todas as 5 tentativas falharem, relança a última exceção
    raise last_exception

def summarize(title: str, body: str = "", source: str = "") -> tuple[str, str]:
    """Gera resumo objetivo e conciso no mesmo idioma do conteúdo original."""
    
    prompt = f"""You are an objective and neutral technology news summarizer.
Extract the essence without opinions or sensationalist terms. Keep technical accuracy.
IMPORTANT: Keep the SAME LANGUAGE as the original content. Do NOT translate.

Source: {source}
Original title: {title}
Content/Description: {body[:1500]}

Respond STRICTLY in valid JSON:
{{
  "title": "Original title as-is (do not translate or modify)",
  "summary": "Concise summary in the SAME language (2-4 sentences, factual)."
}}
"""

    try:
        text = _call_llm([
            {"role": "system", "content": "Respond only in valid JSON without markdown markers."},
            {"role": "user", "content": prompt}
        ])

        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if json_match:
            text = json_match.group(0)
        
        parsed = json.loads(text)
        return parsed.get("title", title), parsed.get("summary", "Sem resumo gerado.")

    except Exception as err:
        print(f"[AIService] Erro após {MAX_RETRIES} tentativas no 9router: {err}")
        return title, (body[:250] + "...") if body else "Sem resumo disponível."
