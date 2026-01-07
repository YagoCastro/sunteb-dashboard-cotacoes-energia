import streamlit as st
import pandas as pd
import plotly.express as px
import os
import calendar

# =====================================
# CONFIGURAÇÕES DA PÁGINA
# =====================================
st.set_page_config(
    page_title="Cotações - Mercado de Energia",
    page_icon="⚡",
    layout="wide"
)

# CSS para melhorar visualização das métricas
st.markdown("""
<style>
    div[data-testid="stMetric"] {
        background-color: #f0f2f6;
        border: 1px solid #dce0e6;
        padding: 10px;
        border-radius: 8px;
    }
    /* Centralizar imagem na sidebar */
    [data-testid="stSidebar"] img {
        display: block;
        margin-left: auto;
        margin-right: auto;
    }
</style>
""", unsafe_allow_html=True)

# =====================================
# FUNÇÃO DE CARREGAMENTO E TRATAMENTO
# =====================================
def load_data(file_buffer_or_path):
    try:
        # Verifica se é string (caminho local) ou buffer (upload)
        if isinstance(file_buffer_or_path, str):
            if file_buffer_or_path.endswith('.xlsx'):
                df = pd.read_excel(file_buffer_or_path)
            else:
                df = pd.read_csv(file_buffer_or_path, sep=';', encoding='latin1')
        else:
            if file_buffer_or_path.name.endswith('.xlsx'):
                df = pd.read_excel(file_buffer_or_path)
            else:
                df = pd.read_csv(file_buffer_or_path, sep=';', encoding='latin1')

        # --- TRATAMENTO DE DADOS ---
        
        # 1. Padronizar Colunas
        df.columns = df.columns.str.strip()

        # 2. Renomear Tipo de Energia
        df['tipo_energia'] = df['tipo_energia'].astype(str).str.strip()
        df['tipo_energia'] = df['tipo_energia'].replace({
            '50': 'I50', 
            '100': 'I100',
            '50.0': 'I50',
            '100.0': 'I100'
        })

        # 3. Converter Valor Financeiro
        if df['valor_cotacao'].dtype == object:
            df['valor_cotacao'] = df['valor_cotacao'].astype(str).str.replace('R$', '', regex=False)
            df['valor_cotacao'] = df['valor_cotacao'].str.replace('.', '', regex=False) # Tira ponto milhar
            df['valor_cotacao'] = df['valor_cotacao'].str.replace(',', '.') # Vírgula decimal
            df['valor_cotacao'] = pd.to_numeric(df['valor_cotacao'])

        # 4. Tratamento de Datas
        if 'data_cotacao' in df.columns:
            df['data_cotacao'] = pd.to_datetime(df['data_cotacao'], dayfirst=True, errors='coerce')
        
        # 5. Tratamento de Mês (Preenche NaN com 0)
        if 'mes_suprimento' in df.columns:
            df['mes_suprimento'] = df['mes_suprimento'].fillna(0).astype(int)

        return df

    except Exception as e:
        st.error(f"Erro ao processar dados: {e}")
        return None

# =====================================
# INICIALIZAÇÃO E SIDEBAR
# =====================================
# --- LOGO NA SIDEBAR ---
with st.sidebar:
    if os.path.exists("logo.png"):
        st.image("logo.png", width=180)
    else:
        st.caption("📷 (logo.png não encontrada)")
    
    st.divider()
    st.header("📁 Fonte de Dados")
    uploaded_file = st.file_uploader("Upload Planilha", type=["xlsx", "csv"])

# Lógica de carga do DF
df = None
if uploaded_file is not None:
    df = load_data(uploaded_file)
elif os.path.exists("cotacoes_energia.csv"):
    df = load_data("cotacoes_energia.csv")
else:
    st.info("👋 Olá! Faça o upload da sua planilha na barra lateral ou adicione 'cotacoes_energia.csv' na pasta.")
    st.stop()

# Se DF carregado, exibe Filtros e Dashboard
if df is not None:
    
    # =====================================
    # FILTROS NA BARRA LATERAL
    # =====================================
    st.sidebar.header("🎯 Filtros")

    # 1. Filtro de Período (Calendário)
    min_date = df['data_cotacao'].min().date()
    max_date = df['data_cotacao'].max().date()
    
    periodo_analise = st.sidebar.date_input(
        "Período de Análise",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
        format="DD/MM/YYYY"
    )

    # 2. Filtro Ano Suprimento
    anos_disp = sorted(df['ano_suprimento'].dropna().unique())
    anos_sel = st.sidebar.multiselect("Ano Suprimento", anos_disp, default=anos_disp)

    # 3. Filtro Mês Suprimento (Mapeamento de Nomes)
    meses_disp = sorted(df['mes_suprimento'].dropna().unique())
    
    # Dicionário para traduzir números em nomes
    def traduzir_mes(m):
        if m == 0:
            return "Anual (Não Mensal)"
        elif 1 <= m <= 12:
            return calendar.month_name[m].capitalize() 
        return str(m)
    
    # Mapeamento manual para garantir PT-BR
    nomes_meses_pt = {
        0: "Anual / Não Mensal", 1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril",
        5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto",
        9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"
    }

    meses_sel = st.sidebar.multiselect(
        "Mês Suprimento",
        options=meses_disp,
        default=meses_disp,
        format_func=lambda x: nomes_meses_pt.get(x, str(x))
    )

    # 4. Filtro Submercado
    subs_disp = df['submercado'].unique()
    subs_sel = st.sidebar.multiselect("Submercado", subs_disp, default=subs_disp)

    # 5. Filtro Tipo Energia
    tipos_disp = df['tipo_energia'].unique()
    tipos_sel = st.sidebar.multiselect("Tipo Energia", tipos_disp, default=tipos_disp)

    # 6. Filtro Comercializadora (NOVO)
    # ---------------------------------------------------------
    comerc_disp = sorted(df['comercializadora'].dropna().unique())
    comerc_sel = st.sidebar.multiselect("Comercializadora", comerc_disp, default=comerc_disp)
    # ---------------------------------------------------------

    # =====================================
    # APLICAÇÃO DOS FILTROS
    # =====================================
    # Tratamento para o date_input (garantir que temos start e end)
    if isinstance(periodo_analise, tuple) and len(periodo_analise) == 2:
        start_date, end_date = periodo_analise
        mask_data = (df['data_cotacao'].dt.date >= start_date) & (df['data_cotacao'].dt.date <= end_date)
    else:
        # [CORREÇÃO PANDAS] Substituindo lista por pd.Series para evitar FutureWarning
        mask_data = pd.Series(True, index=df.index)

    df_filtered = df[
        mask_data &
        (df['ano_suprimento'].isin(anos_sel)) &
        (df['mes_suprimento'].isin(meses_sel)) &
        (df['submercado'].isin(subs_sel)) &
        (df['tipo_energia'].isin(tipos_sel)) &
        (df['comercializadora'].isin(comerc_sel)) # Filtro aplicado aqui
    ]

    if df_filtered.empty:
        st.warning("Nenhum dado encontrado com os filtros selecionados.")
        st.stop()

    # =====================================
    # DASHBOARD PRINCIPAL
    # =====================================
    st.title("📊 Painel de Cotações - Mercado Livre")
    
    # --- KPI DESTAQUE: MELHOR PREÇO POR ANO (TOP 5) ---
    st.subheader("🏆 Melhores Oportunidades (Menor Preço)")
    
    cols = st.columns(len(anos_sel) if len(anos_sel) <= 5 else 5)
    
    # Ajuste para evitar erro se a lista estiver vazia ou menor que o esperado
    limit_anos = min(len(anos_sel), 5)
    
    for i in range(limit_anos):
        ano = anos_sel[i]
        with cols[i]:
            df_ano = df_filtered[df_filtered['ano_suprimento'] == ano]
            if not df_ano.empty:
                idx_min = df_ano['valor_cotacao'].idxmin()
                row_min = df_ano.loc[idx_min]
                
                st.metric(
                    label=f"Ano {int(ano)}",
                    value=f"R$ {row_min['valor_cotacao']:.2f}",
                    delta=f"{row_min['comercializadora']} | {row_min['tipo_energia']}",
                    delta_color="off" 
                )
            else:
                st.metric(label=f"Ano {ano}", value="--")

    st.divider()

    # =====================================
    # ABAS DO DASHBOARD
    # =====================================
    tab1, tab2, tab3, tab4 = st.tabs(["⚡ Matriz de Calor & Tendências", "📈 Dispersão de Preços", "📋 Tabela Detalhada", "📅 Análise Anual Detalhada"])

    # --- ABA 1: MATRIZ HEATMAP ---
    with tab1:
        col_heat, col_line = st.columns([1, 1])

        with col_heat:
            st.subheader("Matriz de Competitividade")
            st.caption("Melhor preço ofertado por Comercializadora vs Ano (Verde = Mais Barato)")

            if not df_filtered.empty:
                pivot_heat = df_filtered.pivot_table(
                    index='comercializadora', 
                    columns='ano_suprimento', 
                    values='valor_cotacao', 
                    aggfunc='min'
                )

                fig_heat = px.imshow(
                    pivot_heat,
                    text_auto=".2f",
                    aspect="auto",
                    color_continuous_scale="RdYlGn_r", 
                    labels=dict(x="Ano", y="Comercializadora", color="Preço (R$)")
                )
                fig_heat.update_xaxes(type='category')
                # ALTERADO: use_container_width=True -> width="stretch"
                st.plotly_chart(fig_heat, width="stretch")

        with col_line:
            st.subheader("Curva Forward Média")
            st.caption("Evolução do preço médio por Tipo de Energia")
            
            df_line = df_filtered.groupby(['ano_suprimento', 'tipo_energia'])['valor_cotacao'].mean().reset_index()
            
            fig_line = px.line(
                df_line,
                x='ano_suprimento',
                y='valor_cotacao',
                color='tipo_energia',
                markers=True,
                symbol='tipo_energia'
            )
            fig_line.update_xaxes(type='category')
            # ALTERADO: use_container_width=True -> width="stretch"
            st.plotly_chart(fig_line, width="stretch")

    # --- ABA 2: COMPARATIVO TEMPORAL DO MENOR PREÇO ---
    with tab2:
        st.subheader("📉 Comparativo Temporal do Melhor Preço")
        st.caption("Evolução do preço ao longo das datas de cotação para o melhor produto selecionado")

        # 1. Encontrar o menor preço dentro do filtro atual
        idx_min_global = df_filtered['valor_cotacao'].idxmin()
        base_row = df_filtered.loc[idx_min_global]

        base_comerc = base_row['comercializadora']
        base_tipo = base_row['tipo_energia']
        base_sub = base_row['submercado']
        base_ano = base_row['ano_suprimento']
        preco_base = base_row['valor_cotacao']
        data_base = base_row['data_cotacao']

        st.markdown(
            f"""
            **Produto base selecionado automaticamente**
            - 🏢 Comercializadora: **{base_comerc}**
            - ⚡ Tipo de Energia: **{base_tipo}**
            - 🌎 Submercado: **{base_sub}**
            - 📅 Ano Suprimento: **{int(base_ano)}**
            - 💰 Menor Preço Atual: **R$ {preco_base:.2f}**
            """
        )

        # 2. Buscar histórico completo desse mesmo produto (antes e depois)
        df_hist = df[
            (df['comercializadora'] == base_comerc) &
            (df['tipo_energia'] == base_tipo) &
            (df['submercado'] == base_sub) &
            (df['ano_suprimento'] == base_ano)
        ].sort_values('data_cotacao')

        # 3. Verificar se existem preços menores em outras datas
        df_menores = df_hist[df_hist['valor_cotacao'] < preco_base]

        if not df_menores.empty:
            st.warning(
                f"⚠️ Foram encontrados **{len(df_menores)} preços MENORES** do que o selecionado em outras datas."
            )
        else:
            st.success("✅ O menor preço selecionado é o MENOR de todo o histórico disponível.")

        # 4. Gráfico de linha temporal
        fig_line_hist = px.line(
            df_hist,
            x='data_cotacao',
            y='valor_cotacao',
            markers=True,
            title="Histórico de Preço por Data de Cotação"
        )

        # 5. Destaque do menor preço atual
        fig_line_hist.add_scatter(
            x=[data_base],
            y=[preco_base],
            mode='markers',
            marker=dict(size=14, symbol='star'),
            name='Menor Preço Selecionado'
        )

        # 6. Destaque de preços menores (se existirem)
        if not df_menores.empty:
            fig_line_hist.add_scatter(
                x=df_menores['data_cotacao'],
                y=df_menores['valor_cotacao'],
                mode='markers',
                marker=dict(size=10),
                name='Preços Menores Encontrados'
            )

        # ALTERADO: use_container_width=True -> width="stretch"
        st.plotly_chart(fig_line_hist, width="stretch")

        # 7. Tabela auxiliar
        with st.expander("📋 Ver histórico detalhado"):
            # ALTERADO: use_container_width=True -> width="stretch"
            st.dataframe(
                df_hist[['data_cotacao', 'valor_cotacao']].sort_values('data_cotacao'),
                width="stretch",
                hide_index=True
            )


    # --- ABA 3: TABELA DETALHADA ---
    with tab3:
        st.subheader("Base de Dados Completa")
        
        col_config = {
            "valor_cotacao": st.column_config.NumberColumn("Preço (R$/MWh)", format="R$ %.2f"),
            "ano_suprimento": st.column_config.NumberColumn("Ano", format="%d"),
            "mes_suprimento": st.column_config.NumberColumn("Mês", format="%d"),
            "data_cotacao": st.column_config.DateColumn("Data Cotação", format="DD/MM/YYYY")
        }
        
        # ALTERADO: use_container_width=True -> width="stretch"
        st.dataframe(
            df_filtered.sort_values(['ano_suprimento', 'mes_suprimento', 'valor_cotacao']),
            width="stretch",
            column_config=col_config,
            hide_index=True
        )

    # --- ABA 4: ANÁLISE ANUAL DETALHADA ---
    with tab4:
        st.subheader("Análise Detalhada por Ano (2026-2030)")

        # Lista de anos fixos para o relatório ou baseada no filtro
        anos_analise = [2026, 2027, 2028, 2029, 2030]
        tipos_analise = ['I50', 'Convencional', 'I100']

        for ano in anos_analise:
            # Verifica se o ano está na seleção atual do filtro
            if ano in anos_sel:
                st.markdown(f"### 📅 Ano {ano}")
                
                # Filtra dados do ano específico
                df_ano_detalhe = df_filtered[df_filtered['ano_suprimento'] == ano]

                if df_ano_detalhe.empty:
                    st.info(
                        f"Sem dados para o ano {ano} com os filtros atuais "
                        "(verifique filtro de Comercializadora)."
                    )
                else:
                    # Cria 3 colunas para os tipos de energia
                    c1, c2, c3 = st.columns(3)
                    colunas_tipos = [c1, c2, c3]

                    for i, tipo in enumerate(tipos_analise):
                        with colunas_tipos[i]:
                            st.markdown(f"**⚡ {tipo}**")
                            
                            # Filtra pelo tipo de energia
                            df_tipo = df_ano_detalhe[df_ano_detalhe['tipo_energia'] == tipo]

                            if not df_tipo.empty:
                                # Preço médio
                                preco_medio = df_tipo['valor_cotacao'].mean()

                                # Melhor preço
                                idx_min = df_tipo['valor_cotacao'].idxmin()
                                melhor_preco = df_tipo.loc[idx_min, 'valor_cotacao']
                                melhor_comerc = df_tipo.loc[idx_min, 'comercializadora']

                                # Maior preço
                                idx_max = df_tipo['valor_cotacao'].idxmax()
                                maior_preco = df_tipo.loc[idx_max, 'valor_cotacao']
                                maior_comerc = df_tipo.loc[idx_max, 'comercializadora']

                                # Volatilidade
                                volatilidade = df_tipo['valor_cotacao'].std()

                                # Exibição das métricas
                                st.metric("Preço Médio", f"R$ {preco_medio:.2f}")
                                st.metric(
                                    "Melhor Preço",
                                    f"R$ {melhor_preco:.2f}",
                                    f"{melhor_comerc}",
                                    delta_color="off"
                                )
                                st.metric(
                                    "Maior Preço",
                                    f"R$ {maior_preco:.2f}",
                                    f"{maior_comerc}",
                                    delta_color="off"
                                )

                                # Tratamento para volatilidade NaN
                                vol_str = f"R$ {volatilidade:.2f}" if not pd.isna(volatilidade) else "--"
                                st.metric("Volatilidade", vol_str)

                            else:
                                st.caption("Sem cotações para este tipo de energia")

                st.divider()