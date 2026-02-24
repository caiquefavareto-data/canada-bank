import streamlit as st
import pandas as pd
import yfinance as yf
import datetime
import plotly.express as px
import plotly.graph_objects as go
import os
import feedparser
import calendar
import smtplib
from email.message import EmailMessage
import random
import string
import gspread
from google.oauth2.service_account import Credentials
import requests

# --- CONFIGURAÇÕES GERAIS ---
st.set_page_config(page_title="Canada Bank - Login", layout="wide")

# ==========================================
# ☁️ CONEXÃO COM O GOOGLE SHEETS
# ==========================================
# 👇 COLE O LINK DA SUA PLANILHA AQUI 👇
URL_PLANILHA = "https://docs.google.com/spreadsheets/d/1UpxDZA4Bfio0kzfmcFuyAzhPIrRoOQBMA7B5a2soHOo/edit?gid=0#gid=0"

scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
client = gspread.authorize(creds)

@st.cache_resource
def get_planilha():
    try:
        return client.open_by_url(URL_PLANILHA)
    except Exception as e:
        st.error(f"Erro ao acessar a planilha. Verifique o link e se você a compartilhou com o bot! Erro: {e}")
        st.stop()

sh = get_planilha()

def get_df(aba, colunas_padrao):
    try:
        ws = sh.worksheet(aba)
    except gspread.exceptions.WorksheetNotFound:
        ws = sh.add_worksheet(title=aba, rows=100, cols=20)
        ws.append_row(colunas_padrao)
    
    data = ws.get_all_records()
    if not data:
        return pd.DataFrame(columns=colunas_padrao)
    return pd.DataFrame(data)

def save_df(aba, df):
    ws = sh.worksheet(aba)
    ws.clear()
    df = df.fillna("")
    df_str = df.astype(str)
    data_to_update = [df_str.columns.values.tolist()] + df_str.values.tolist()
    ws.update(values=data_to_update, range_name="A1")

# ==========================================
# 📧 ENVIO DE E-MAIL (Usando os Segredos)
# ==========================================
def enviar_email_recuperacao(destinatario, nova_senha, nome_usuario):
    email_remetente = st.secrets["email_config"]["email_remetente"]
    senha_app = st.secrets["email_config"]["senha_app"]
    try:
        msg = EmailMessage()
        msg['Subject'] = 'Canada Bank - Recuperação de Senha'
        msg['From'] = email_remetente
        msg['To'] = destinatario
        msg.set_content(f"Olá {nome_usuario},\n\nSua senha do Canada Bank foi redefinida com sucesso!\n\nSua nova senha é: {nova_senha}\n\nRecomendamos que você acesse o sistema e mude esta senha na aba 'Meu Perfil'.")

        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(email_remetente, senha_app)
            smtp.send_message(msg)
        return True
    except Exception as e:
        return False

# ==========================================
# 🌄 CONFIGURAÇÃO DE IMAGENS DE FUNDO
# ==========================================
imagens_canada = [
    "https://images.unsplash.com/photo-1517935703635-27c736827a7e?q=80&w=2000", # Moraine Lake
    "https://images.unsplash.com/photo-1503614472-8c93d56e92ce?q=80&w=2000", # Montanhas Rochosas
    "https://images.unsplash.com/photo-1534067783941-51c9c236306c?q=80&w=2000", # Vancouver Skyline
    "https://images.unsplash.com/photo-1580060839134-75a5edca2e27?q=80&w=2000", # Toronto CN Tower
    "https://images.unsplash.com/photo-1523633589114-88eaf4b4f1a8?q=80&w=2000"  # Estrada no Outono
]
# Escolhe uma imagem aleatória a cada carregamento
imagem_fundo = random.choice(imagens_canada)

st.markdown(f"""
    <style>
    .stApp {{ 
        background: linear-gradient(rgba(0,0,0,0.85), rgba(0,0,0,0.85)), 
                    url("{imagem_fundo}"); 
        background-size: cover; background-attachment: fixed; background-position: center;
    }}
    h1, h2, h3, p, label {{ color: white !important; }}
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 🛡️ TELA DE LOGIN E CARREGAMENTO DE BANCO
# ==========================================
df_users = get_df("Usuarios", ["Usuario", "Senha", "Email"])

if df_users.empty:
    df_users = pd.DataFrame([
        {"Usuario": "caique", "Senha": "123", "Email": "caiqueviniciustf@gmail.com"},
        {"Usuario": "regiane", "Senha": "123", "Email": "regianevdevieira@gmail.com"}
    ])
    save_df("Usuarios", df_users)

df_users['Senha'] = df_users['Senha'].astype(str)

if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False
    st.session_state["usuario_logado"] = ""

if not st.session_state["autenticado"]:
    st.markdown("<h1 style='text-align: center; color: white; margin-top: 50px;'>🇨🇦 Canada Bank</h1>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        tab_login, tab_recuperar = st.tabs(["🔐 Entrar", "✉️ Esqueci a Senha"])
        
        with tab_login:
            st.markdown("<h4 style='color: white;'>Acesse sua conta</h4>", unsafe_allow_html=True)
            user_input = st.text_input("Usuário").strip().lower()
            pass_input = st.text_input("Senha", type="password")
            
            if st.button("Entrar", type="primary", use_container_width=True):
                usuario_existe = df_users[(df_users['Usuario'].str.lower() == user_input) & (df_users['Senha'] == pass_input)]
                if not usuario_existe.empty:
                    st.session_state["autenticado"] = True
                    st.session_state["usuario_logado"] = usuario_existe.iloc[0]['Usuario'].capitalize()
                    st.rerun()
                else:
                    st.error("Usuário ou senha incorretos.")

        with tab_recuperar:
            st.markdown("<h4 style='color: white;'>Recuperar Acesso</h4>", unsafe_allow_html=True)
            st.info("Digite seu usuário. Uma nova senha será gerada e enviada para o seu e-mail cadastrado.")
            rec_user_input = st.text_input("Seu Usuário (caique ou regiane)").strip().lower()
            
            if st.button("Enviar nova senha", use_container_width=True):
                user_match = df_users[df_users['Usuario'].str.lower() == rec_user_input]
                
                if not user_match.empty:
                    email_destino = user_match.iloc[0]['Email']
                    nova_senha_gerada = ''.join(random.choices(string.ascii_letters + string.digits, k=6))
                    
                    df_users.loc[df_users['Usuario'].str.lower() == rec_user_input, 'Senha'] = nova_senha_gerada
                    save_df("Usuarios", df_users)
                    
                    sucesso = enviar_email_recuperacao(email_destino, nova_senha_gerada, rec_user_input.capitalize())
                    if sucesso:
                        st.success(f"Nova senha enviada para: {email_destino}")
                    else:
                        st.error("Erro no envio do email. Verifique a senha de app do Gmail no secrets.toml.")
                else:
                    st.error("Usuário não encontrado no banco de dados.")
    st.stop()

# ==========================================
# 🍁 APLICATIVO PRINCIPAL (LOGADO)
# ==========================================
df_t = get_df("Transacoes", ["ID", "Data", "User", "Tipo", "Cat", "Desc", "Valor", "Origem", "Metodo"])
if not df_t.empty:
    df_t['ID'] = pd.to_numeric(df_t['ID'], errors='coerce').fillna(0).astype(int)
    df_t['Valor'] = pd.to_numeric(df_t['Valor'], errors='coerce').fillna(0.0).astype(float)
    df_t['Data'] = pd.to_datetime(df_t['Data'], errors='coerce')

df_c = get_df("Cartoes", ["Nome", "Titular", "Ultimos_Digitos", "Limite_Total"])
if not df_c.empty:
    df_c['Limite_Total'] = pd.to_numeric(df_c['Limite_Total'], errors='coerce').fillna(0.0).astype(float)

df_a = get_df("Contas", ["Nome", "Titular"])

df_goal = get_df("Metas", ["Meta_CAD", "Data_Viagem", "Poupanca_Mensal"])
if df_goal.empty:
    df_goal = pd.DataFrame([{"Meta_CAD": 20000.0, "Data_Viagem": "2026-07-01", "Poupanca_Mensal": 1000.0}])
    save_df("Metas", df_goal)
else:
    df_goal['Meta_CAD'] = pd.to_numeric(df_goal['Meta_CAD'], errors='coerce').fillna(20000.0).astype(float)
    df_goal['Poupanca_Mensal'] = pd.to_numeric(df_goal['Poupanca_Mensal'], errors='coerce').fillna(1000.0).astype(float)
config_canada = df_goal.iloc[0]

def obter_cotacao_viva():
    try:
        ticker = yf.Ticker("CADBRL=X")
        hist = ticker.history(period="1d")
        return hist['Close'].iloc[-1] if not hist.empty else 3.75
    except: return 3.75

def buscar_noticias_canada():
    try:
        # Disfarça o navegador para evitar bloqueio
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
        resposta = requests.get("https://www.cbc.ca/cmlink/rss-canada", headers=headers, timeout=5)
        feed = feedparser.parse(resposta.content)
        return feed.entries[:5]
    except: 
        return []

def gerar_calendario_html(ano, mes, data_viagem):
    meses_pt = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
    cal_matrix = calendar.monthcalendar(ano, mes)
    hoje = datetime.date.today()
    html = f"""<div style="background: rgba(255, 255, 255, 0.05); padding: 20px; border-radius: 15px; max-width: 300px; margin: 0 auto 15px auto; box-shadow: 0 4px 10px rgba(0,0,0,0.3); font-family: sans-serif;"><div style="text-align: center; font-size: 1.2rem; font-weight: bold; margin-bottom: 15px; color: #fff;">{meses_pt[mes-1]} {ano}</div><div style="display: grid; grid-template-columns: repeat(7, 1fr); gap: 5px; text-align: center; margin-bottom: 10px;">"""
    for d in ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]: html += f'<div style="font-size: 0.75rem; color: #aaa; font-weight: bold;">{d}</div>'
    html += "</div><div style='display: grid; grid-template-columns: repeat(7, 1fr); gap: 5px; text-align: center;'>"
    for semana in cal_matrix:
        for dia in semana:
            if dia == 0: html += "<div></div>"
            else:
                bg_color, text_color, font_weight = "transparent", "#ddd", "normal"
                if data_viagem.year == ano and data_viagem.month == mes and data_viagem.day == dia: bg_color, text_color, font_weight = "#d13639", "white", "bold"
                elif hoje.year == ano and hoje.month == mes and hoje.day == dia: bg_color, text_color, font_weight = "rgba(255,255,255,0.2)", "white", "bold"
                html += f'<div style="background-color: {bg_color}; color: {text_color}; font-weight: {font_weight}; border-radius: 50%; width: 30px; height: 30px; display: flex; align-items: center; justify-content: center; margin: auto; font-size: 0.9rem;">{dia}</div>'
    html += "</div></div>"
    return html

cotacao_cad_brl = obter_cotacao_viva()

col_t1, col_t2 = st.columns([5, 1])
with col_t1: st.title(f"🇨🇦 Canada Bank | Olá, {st.session_state['usuario_logado']}!")
with col_t2:
    if st.button("🚪 Sair", use_container_width=True):
        st.session_state["autenticado"] = False; st.rerun()

entradas = df_t[df_t['Tipo'].isin(['Entrada', 'Juros / Rendimento', 'Aporte Poupança'])]['Valor'].sum() if not df_t.empty else 0
saidas = df_t[df_t['Tipo'] == 'Saída']['Valor'].sum() if not df_t.empty else 0
saldo_brl = entradas - saidas
saldo_projeto_brl = df_t[df_t['Origem'] == 'Projeto Canadá']['Valor'].sum() if not df_t.empty else 0
saldo_projeto_cad = saldo_projeto_brl / cotacao_cad_brl if cotacao_cad_brl > 0 else 0

m1, m2, m3, m4 = st.columns(4)
m1.metric("🇧🇷 Saldo Atual", f"R$ {saldo_brl:,.2f}")
m2.metric("🇨🇦 Fundo Canadá", f"CAD$ {saldo_projeto_cad:,.2f}")
m3.metric("🎯 Meta", f"CAD$ {config_canada['Meta_CAD']:,.2f}")
m4.metric("📈 1 CAD hoje", f"R$ {cotacao_cad_brl:.2f}")

tabs = st.tabs(["📊 Saúde Financeira", "💰 Lançar", "🍁 Planejamento", "💳 Cartões", "🏦 Contas", "👤 Perfil / Extrato"])

with tabs[0]:
    st.subheader("Tendência do Patrimônio")
    if not df_t.empty:
        df_hist = df_t.sort_values('Data').dropna(subset=['Data'])
        df_hist['Sinal'] = df_hist.apply(lambda x: x['Valor'] if x['Tipo'] in ['Entrada', 'Juros / Rendimento', 'Aporte Poupança'] else -x['Valor'], axis=1)
        df_hist['Saldo_Acumulado'] = df_hist['Sinal'].cumsum()
        fig_trend = go.Figure(go.Scatter(x=df_hist['Data'], y=df_hist['Saldo_Acumulado'], fill='tozeroy', line=dict(color='#d13639')))
        fig_trend.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color="white"))
        st.plotly_chart(fig_trend, use_container_width=True)

with tabs[1]:
    with st.form("form_lan"):
        st.subheader("Lançamento Mensal")
        c1, c2, c3 = st.columns(3)
        u = c1.selectbox("Responsável", ["Caique", "Regiane"], index=0 if st.session_state['usuario_logado'] == 'Caique' else 1)
        tp = c2.selectbox("Tipo", ["Entrada", "Saída"])
        ori = c3.selectbox("Origem/Destino", df_a['Nome'].tolist() + df_c['Nome'].tolist() + ["Dinheiro Vivo"]) if not df_a.empty else c3.selectbox("Origem/Destino", ["Dinheiro Vivo"])
        cat = st.selectbox("Categoria", ["Salário", "Mercado", "Lazer", "Internet", "Moradia", "Saúde", "Outros"])
        ds = st.text_input("Descrição")
        vl = st.number_input("Valor R$", min_value=0.0)
        if st.form_submit_button("Confirmar"):
            novo_id = df_t['ID'].max() + 1 if not df_t.empty else 1
            novo_d = pd.DataFrame([{"ID": int(novo_id), "Data": datetime.date.today(), "User": u, "Tipo": tp, "Cat": cat, "Desc": ds, "Valor": vl, "Origem": ori, "Metodo": "Direto"}])
            df_atualizado = pd.concat([df_t, novo_d], ignore_index=True)
            save_df("Transacoes", df_atualizado)
            st.rerun()

with tabs[2]:
    st.header("🇨🇦 Planejamento")
    col_lan, col_cal = st.columns([2, 1])
    with col_lan:
        with st.expander("➕ Novo Item de Planejamento", expanded=True):
            with st.form("form_can"):
                c1, c2 = st.columns(2)
                u_c = c1.selectbox("Responsável", ["Caique", "Regiane"], key="resp_canada", index=0 if st.session_state['usuario_logado'] == 'Caique' else 1)
                tp_c = c2.selectbox("Tipo", ["Aporte Poupança", "Juros / Rendimento", "Saída (Gasto Viagem)"])
                cat_c = st.selectbox("Item", ["POF (Comprovação)", "Passagem", "Hospedagem", "Alimentação", "Passeios", "Turismo", "Vistos", "Outros"])
                vl_c = st.number_input("Valor R$", min_value=0.0)
                if st.form_submit_button("Registrar"):
                    real_val = -vl_c if "Saída" in tp_c else vl_c
                    novo_id = df_t['ID'].max() + 1 if not df_t.empty else 1
                    novo_d = pd.DataFrame([{"ID": int(novo_id), "Data": datetime.date.today(), "User": u_c, "Tipo": tp_c, "Cat": cat_c, "Desc": "Projeto Canada", "Valor": real_val, "Origem": "Projeto Canadá", "Metodo": "Planejamento"}])
                    df_atualizado = pd.concat([df_t, novo_d], ignore_index=True)
                    save_df("Transacoes", df_atualizado)
                    st.rerun()

    with col_cal:
        st.subheader("Contagem Regressiva")
        data_atual = pd.to_datetime(config_canada['Data_Viagem']).date()
        dias_faltam = (data_atual - datetime.date.today()).days
        st.markdown(f"<div style='background:rgba(209, 54, 57, 0.2); padding:10px; border-radius:8px; text-align:center; border:1px solid #d13639; margin-bottom:10px;'><b>⏳ Faltam {max(0, dias_faltam)} dias</b></div>", unsafe_allow_html=True)
        
        mes_visualizar = st.selectbox("Visualizar calendário:", ["Mês da Viagem", "Mês Atual"], index=0)
        ano_cal = data_atual.year if mes_visualizar == "Mês da Viagem" else datetime.date.today().year
        mes_cal = data_atual.month if mes_visualizar == "Mês da Viagem" else datetime.date.today().month
        st.markdown(gerar_calendario_html(ano_cal, mes_cal, data_atual), unsafe_allow_html=True)
        st.caption("🔴 Vermelho: Dia da Viagem | 🔘 Cinza: Hoje")

        with st.expander("✏️ Alterar Data da Viagem"):
            nova_data = st.date_input("Nova data:", value=data_atual)
            if st.button("Atualizar Data"):
                df_goal.loc[0, 'Data_Viagem'] = str(nova_data)
                save_df("Metas", df_goal)
                st.rerun()

    st.divider()
    prog_p = min(1.0, max(0.0, saldo_projeto_cad / config_canada['Meta_CAD']))
    st.subheader(f"Progresso: {prog_p*100:.1f}%")
    st.progress(prog_p)

with tabs[3]:
    st.subheader("Cartões")
    with st.expander("➕ Adicionar"):
        with st.form("c_f"):
            nc = st.text_input("Nome"); tc = st.selectbox("Titular", ["Caique", "Regiane"]); dc = st.text_input("4 Últimos dígitos", max_chars=4); lc = st.number_input("Limite", 0.0)
            if st.form_submit_button("Gravar"):
                novo_c = pd.DataFrame([{"Nome": nc, "Titular": tc, "Ultimos_Digitos": dc, "Limite_Total": lc}])
                df_c_atualizado = pd.concat([df_c, novo_c], ignore_index=True)
                save_df("Cartoes", df_c_atualizado)
                st.rerun()
    for i, r in df_c.iterrows():
        c1, c2 = st.columns([4,1]); c1.write(f"💳 **{r['Nome']}** ({r.get('Ultimos_Digitos', '0000')}) - {r.get('Titular', 'N/A')}")
        if c2.button("Excluir", key=f"c_{i}"):
            df_c_atualizado = df_c.drop(i)
            save_df("Cartoes", df_c_atualizado)
            st.rerun()

with tabs[4]: 
    st.subheader("Contas")
    with st.expander("➕ Adicionar"):
        with st.form("a_f"):
            na = st.text_input("Banco"); ta = st.selectbox("Titular", ["Caique", "Regiane"])
            if st.form_submit_button("Gravar"):
                novo_a = pd.DataFrame([{"Nome": na, "Titular": ta}])
                df_a_atualizado = pd.concat([df_a, novo_a], ignore_index=True)
                save_df("Contas", df_a_atualizado)
                st.rerun()
    for i, r in df_a.iterrows():
        c1, c2 = st.columns([4,1]); c1.write(f"🏦 **{r['Nome']}** - {r.get('Titular', 'N/A')}")
        if c2.button("Excluir", key=f"a_{i}"): 
            df_a_atualizado = df_a.drop(i)
            save_df("Contas", df_a_atualizado)
            st.rerun()

with tabs[5]: 
    st.subheader("Meu Perfil")
    meu_perfil = df_users[df_users['Usuario'] == st.session_state['usuario_logado'].lower()]
    
    with st.expander("⚙️ Alterar minha Senha ou E-mail"):
        with st.form("att_perfil"):
            novo_email = st.text_input("Meu E-mail", value=meu_perfil.iloc[0]['Email'] if not meu_perfil.empty else "")
            nova_senha = st.text_input("Nova Senha", type="password")
            if st.form_submit_button("Salvar Alterações"):
                df_users.loc[df_users['Usuario'] == st.session_state['usuario_logado'].lower(), 'Email'] = novo_email
                if nova_senha: df_users.loc[df_users['Usuario'] == st.session_state['usuario_logado'].lower(), 'Senha'] = nova_senha
                save_df("Usuarios", df_users)
                st.success("Dados atualizados!")
                st.rerun()
    
    st.divider()
    st.subheader("Extrato")
    col_ext1, col_ext2 = st.columns([4,1])
    with col_ext1:
        df_extrato = df_t.copy()
        if not df_extrato.empty:
            df_extrato.insert(0, 'Excluir', False)
            df_ed = st.data_editor(df_extrato, use_container_width=True, column_config={"Excluir": st.column_config.CheckboxColumn("Apagar?", default=False)}, disabled=["ID"])
        else:
            st.write("Sem transações registradas.")
            df_ed = pd.DataFrame()
    
    with col_ext2:
        if not df_ed.empty:
            if st.button("🗑️ Apagar Selecionados", type="primary"):
                df_salvar = df_ed[df_ed['Excluir'] == False].drop(columns=['Excluir'])
                save_df("Transacoes", df_salvar)
                st.rerun()
        
        st.divider()
        if st.button("Zerar Histórico"):
            save_df("Transacoes", pd.DataFrame(columns=["ID", "Data", "User", "Tipo", "Cat", "Desc", "Valor", "Origem", "Metodo"]))
            st.rerun()

# --- NOTÍCIAS NO FINAL ---
st.divider()
st.subheader("📰 Últimas Notícias do Canadá (CBC)")

noticias = buscar_noticias_canada()

if noticias:
    for n in noticias:
        data_pub = n.get('published', '')[0:16]
        
        # 👇 ADICIONADO O referrerpolicy='no-referrer' 👇
        st.markdown(f"""
        <div style='background: rgba(255,255,255,0.05); padding: 15px; border-radius: 8px; margin-bottom: 10px; border-left: 4px solid #d13639;'>
            <a href='{n.link}' target='_blank' rel='noopener noreferrer' referrerpolicy='no-referrer' style='color: white; text-decoration: none; font-size: 1.1rem; font-weight: bold;'>
                {n.title}
            </a>
            <br>
            <span style='color: #aaa; font-size: 0.85rem;'>📅 {data_pub}</span>
        </div>
        """, unsafe_allow_html=True)
else:
    st.info("Buscando notícias... Se não aparecerem, o site da emissora pode estar temporariamente indisponível.")
