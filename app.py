"""
Fofoqueiro – Interface Principal Compacta (Streamlit)
"""
import streamlit as st
import database
import config
import re

st.set_page_config(
    page_title=config.STREAMLIT_PAGE_TITLE,
    page_icon=config.STREAMLIT_PAGE_ICON,
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilo CSS customizado para layout de cards compactos com preview de texto
st.markdown("""
<style>
    .block-container { padding-top: 1rem; padding-bottom: 1rem; }
    .news-card {
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 8px;
        padding: 12px 14px;
        margin-bottom: 12px;
        background-color: rgba(255, 255, 255, 0.02);
    }
    .news-title {
        font-size: 15px;
        font-weight: 600;
        margin-bottom: 4px;
        line-height: 1.3;
    }
    .news-summary {
        font-size: 13px;
        color: #b0b0b0;
        margin-top: 6px;
        margin-bottom: 6px;
        line-height: 1.4;
    }
    .news-meta {
        font-size: 11px;
        color: #888;
    }
</style>
""", unsafe_allow_html=True)

def clean_html(raw_html: str) -> str:
    """Remove tags HTML brutas que às vezes vêm nos feeds RSS/Reddit."""
    if not raw_html:
        return ""
    clean = re.sub(r'<[^<]+?>', '', raw_html)
    return clean.replace('&quot;', '"').replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>').strip()

# Conexão DB
@st.cache_resource
def get_db():
    conn = database.get_connection()
    database.init_db(conn)
    return conn

conn = get_db()

# ── Header Compacto ───────────────────────────────────────────────────
col_head1, col_head2 = st.columns([0.7, 0.3])
with col_head1:
    st.title("🤖 Fofoqueiro")
    st.caption("Inteligência & Notícias Tech/Sec em formato conciso.")
with col_head2:
    if st.button("🔄 Atualizar Feed", use_container_width=True):
        st.rerun()

# ── Sidebar ─────────────────────────────────────────────────────────────
st.sidebar.header("🔍 Filtros")
source_filter = st.sidebar.selectbox(
    "Fonte de Notícias",
    ["Todas", "hackernews", "reddit", "cve"],
    format_func=lambda x: {
        "Todas": "🌐 Todas as Fontes",
        "hackernews": "🧡 Hacker News",
        "reddit": "🤖 Reddit",
        "cve": "🛡️ Linux CVEs",
    }.get(x, x),
)

search_term = st.sidebar.text_input("🔎 Buscar palavra-chave", "")

st.sidebar.divider()
st.sidebar.subheader("⚙️ Subreddits")

current_subs = config.get_all_subreddits()
st.sidebar.caption("Ativos: " + ", ".join([f"`r/{s}`" for s in current_subs]))

new_sub = st.sidebar.text_input("Adicionar Subreddit", placeholder="ex: cybersecurity")
if st.sidebar.button("➕ Adicionar Subreddit"):
    if new_sub.strip():
        clean_sub = new_sub.strip().replace("r/", "")
        user_subs = config.load_user_subreddits()
        if clean_sub not in user_subs:
            user_subs.append(clean_sub)
            config.save_user_subreddits(user_subs)
            st.sidebar.success(f"Adicionado: r/{clean_sub}!")
            st.rerun()

st.sidebar.divider()

# Status do Worker colapsável na sidebar
with st.sidebar.expander("📊 Status do Worker"):
    runs = database.get_recent_runs(conn, limit=5)
    if runs:
        for r in runs:
            st.caption(f"**{r['source']}**: {r['items_new']} novos ({r['started_at'][11:16]})")
    else:
        st.caption("Nenhum log gravado.")

# ── Exibição das Notícias (Layout de 2 Colunas com Preview de Resumo) ──
selected_source = None if source_filter == "Todas" else source_filter
news_list = database.get_news(conn, source=selected_source, search=search_term if search_term else None)

st.write(f"Mostrando **{len(news_list)}** notícias")

if not news_list:
    st.info("Nenhuma notícia encontrada.")
else:
    col_left, col_right = st.columns(2)
    
    for idx, item in enumerate(news_list):
        target_col = col_left if idx % 2 == 0 else col_right
        
        with target_col:
            category_val = item["category"] if "category" in item.keys() and item["category"] else "Security"
            source_icon = {
                "hackernews": "🧡 HN",
                "reddit": f"🤖 {category_val}",
                "cve": "🛡️ Sec/CVE",
            }.get(item["source"], item["source"])
            
            score_info = f" • 🔥 {item['tabcoins']}" if "tabcoins" in item.keys() and item["tabcoins"] else ""
            comments_info = f" • 💬 {item['comment_count']}" if "comment_count" in item.keys() and item["comment_count"] else ""
            date_info = f" • 🕒 {item['published_at'][:10]}" if "published_at" in item.keys() and item["published_at"] else ""
            
            summary_raw = item["summary"] if item["summary"] else ""
            summary_text = clean_html(summary_raw)
            if len(summary_text) > 280:
                summary_text = summary_text[:280] + "..."

            with st.container(border=True):
                st.markdown(f"**{source_icon}** [{item['title']}]({item['link']})")
                
                if summary_text:
                    st.caption(summary_text)
                else:
                    st.caption("*(Sem descrição / resumo disponível)*")
                
                st.markdown(
                    f"<div class='news-meta'><b>Origem:</b> {item['source'].upper()}{score_info}{comments_info}{date_info}</div>",
                    unsafe_allow_html=True
                )
