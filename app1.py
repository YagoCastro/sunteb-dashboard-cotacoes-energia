import streamlit as st
import pandas as pd
import plotly.express as px
import os
import calendar
import numpy as np 

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
        df.columns = df.columns.str.strip().str.lower()
        
        # Renomear colunas essenciais para garantir compatibilidade
        map_cols = {
            'tipo energia': 'tipo_energia',
            'valor cotacao': 'valor_cotacao',
            'data cotacao': 'data_cotacao',
            'mes suprimento': 'mes_suprimento',
            'ano suprimento': 'ano_suprimento'
        }
        df = df.rename(columns=map_cols)

        # 2. Renomear Tipo de Energia
        if 'tipo_energia' in df.columns:
            df['tipo_energia'] = df['tipo_energia'].astype(str).str.strip()
            df['tipo_energia'] = df['tipo_energia'].replace({
                '50': 'I50', 
                '100': 'I100',
                '50.0': 'I50',
                '100.0': 'I100'
            })

        # 3. Converter Valor Financeiro
        if 'valor_cotacao' in df.columns:
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

        # 6. Tratamento de Modalidade (NOVO)
        if 'modalidade' in df.columns:
            df['modalidade'] = df['modalidade'].astype(str).str.strip().str.title()
        else:
            # Cria coluna padrão caso não exista
            df['modalidade'] = 'Atacadista'

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
    elif os.path.exists("logo.PNG"):
        st.image("logo.PNG", width=180)
    elif os.path.exists("logo.jpg"):
        st.image("logo.jpg", width=180)
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

    # 2. Filtro Modalidade (NOVO)
    mod_disp = sorted(df['modalidade'].unique())
    default_mod = ['Atacadista'] if 'Atacadista' in mod_disp else mod_disp
    mod_sel = st.sidebar.multiselect("Modalidade", mod_disp, default=default_mod)

    # 3. Filtro Ano Suprimento
    anos_disp = sorted(df['ano_suprimento'].dropna().unique())
    anos_sel = st.sidebar.multiselect("Ano Suprimento", anos_disp, default=anos_disp)

    # 4. Filtro Mês Suprimento
    meses_disp = sorted(df['mes_suprimento'].dropna().unique())
    
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

    # 5. Filtro Submercado
    subs_disp = df['submercado'].unique()
    subs_sel = st.sidebar.multiselect("Submercado", subs_disp, default=subs_disp)

    # 6. Filtro Tipo Energia
    tipos_disp = df['tipo_energia'].unique()
    tipos_sel = st.sidebar.multiselect("Tipo Energia", tipos_disp, default=tipos_disp)

    # 7. Filtro Comercializadora
    comerc_disp = sorted(df['comercializadora'].dropna().unique())
    comerc_sel = st.sidebar.multiselect("Comercializadora", comerc_disp, default=comerc_disp)

    # =====================================
    # APLICAÇÃO DOS FILTROS
    # =====================================
    if isinstance(periodo_analise, tuple) and len(periodo_analise) == 2:
        start_date, end_date = periodo_analise
        mask_data = (df['data_cotacao'].dt.date >= start_date) & (df['data_cotacao'].dt.date <= end_date)
    else:
        start_date, end_date = min_date, max_date
        mask_data = pd.Series(True, index=df.index)

    df_filtered = df[
        mask_data &
        (df['ano_suprimento'].isin(anos_sel)) &
        (df['mes_suprimento'].isin(meses_sel)) &
        (df['submercado'].isin(subs_sel)) &
        (df['tipo_energia'].isin(tipos_sel)) &
        (df['comercializadora'].isin(comerc_sel)) &
        (df['modalidade'].isin(mod_sel))
    ]

    if df_filtered.empty:
        st.warning("Nenhum dado encontrado com os filtros selecionados.")
        st.stop()

    # =====================================
    # DASHBOARD PRINCIPAL
    # =====================================
    
    st.title("📊 Painel de Cotações - Mercado Livre")
    
    # --- CABEÇALHO: TOTAIS E DATAS ---
    # Colunas: Total | Período (Data Início até Fim)
    c_kpi1, c_kpi2, c_vazio = st.columns([1, 1.5, 2])
    
    with c_kpi1:
        st.metric("Total de Cotações", f"{len(df_filtered):,}".replace(",", "."))
        
    with c_kpi2:
        dt_ini = df_filtered['data_cotacao'].min().strftime('%d/%m/%Y')
        dt_fim = df_filtered['data_cotacao'].max().strftime('%d/%m/%Y')
        st.metric("Período das Cotações", f"{dt_ini} até {dt_fim}")

    st.divider()
    
    st.subheader("🏆 Melhores Oportunidades (Menor Preço)")

    limit_anos = min(len(anos_sel), 5)
    
    # Função auxiliar atualizada para incluir a Média no final se solicitado
    def gerar_linha_kpi(label_row, df_sub, anos_lista, mostrar_media=False):
        # Se mostrar_media for True, adiciona uma coluna extra
        cols_count = len(anos_lista) + 1 # +1 para o título
        if mostrar_media:
            cols_count += 1
            
        # Limita colunas para não quebrar visualmente
        cols_count = min(cols_count, 7)
        
        cols = st.columns(cols_count)
        
        # Primeira coluna: Título da Linha
        with cols[0]:
            st.markdown(f"### {label_row}")
        
        # Coletar preços para média
        precos_minimos_linha = []

        col_idx = 1
        for i in range(limit_anos):
            # Se exceder colunas, para
            if col_idx >= len(cols): break
            
            # Se for a última coluna e precisarmos mostrar a média, para o loop de anos
            if mostrar_media and col_idx == (len(cols) - 1):
                break

            ano = anos_lista[i]
            with cols[col_idx]:
                df_ano = df_sub[df_sub['ano_suprimento'] == ano]
                if not df_ano.empty:
                    idx_min = df_ano['valor_cotacao'].idxmin()
                    row_min = df_ano.loc[idx_min]
                    preco = row_min['valor_cotacao']
                    
                    precos_minimos_linha.append(preco)

                    st.metric(
                        label=f"Ano {int(ano)}",
                        value=f"R$ {preco:.2f}",
                        delta=f"{row_min['comercializadora']}",
                        delta_color="off" 
                    )
                else:
                    st.metric(label=f"Ano {ano}", value="--")
            col_idx += 1
            
        # Se solicitado, mostra a média na última coluna disponível
        if mostrar_media and col_idx < len(cols):
            with cols[col_idx]:
                if precos_minimos_linha:
                    media_val = sum(precos_minimos_linha) / len(precos_minimos_linha)
                    st.metric(
                        label="Média (Período)",
                        value=f"R$ {media_val:.2f}",
                        delta="Melhores Preços",
                        delta_color="off"
                    )
                else:
                    st.metric(label="Média", value="--")

    # LINHA 1: ATACADO (COM MÉDIA)
    df_atacado = df_filtered[df_filtered['modalidade'].astype(str).str.contains("Atacadi", case=False)]
    if not df_atacado.empty:
        gerar_linha_kpi("Atacado", df_atacado, anos_sel, mostrar_media=True)
    
    # LINHA 2: VAREJO (AGORA COM MÉDIA = TRUE)
    df_varejo = df_filtered[df_filtered['modalidade'].astype(str).str.contains("Varej", case=False)]
    if not df_varejo.empty:
        st.markdown("---")
        gerar_linha_kpi("Varejo", df_varejo, anos_sel, mostrar_media=True)

    # --- GRÁFICO DE DISTRIBUIÇÃO MODIFICADO ---
    st.divider()
    st.subheader("📅 Distribuição das Cotações (Datas x Anos)")
    
    # 1. Filtros Exclusivos para este gráfico
    st.markdown("##### 🔎 Filtros do Gráfico")
    c_g1, c_g2, c_g3 = st.columns(3)
    
    # Opções únicas do dataframe filtrado principal
    g_tipos = df_filtered['tipo_energia'].unique()
    g_mods = df_filtered['modalidade'].unique()
    g_comercs = sorted(df_filtered['comercializadora'].unique())

    with c_g1:
        sel_g_tipo = st.multiselect("Tipo de Energia (Gráfico)", g_tipos, default=g_tipos)
    with c_g2:
        sel_g_mod = st.multiselect("Modalidade (Gráfico)", g_mods, default=g_mods)
    with c_g3:
        sel_g_comerc = st.multiselect("Comercializadora (Gráfico)", g_comercs, default=g_comercs)

    # 2. Filtragem local para o gráfico
    df_graph = df_filtered[
        (df_filtered['tipo_energia'].isin(sel_g_tipo)) &
        (df_filtered['modalidade'].isin(sel_g_mod)) &
        (df_filtered['comercializadora'].isin(sel_g_comerc))
    ].copy()

    if df_graph.empty:
        st.warning("Sem dados para exibir no gráfico com os filtros selecionados.")
    else:
        # 3. TRATAMENTO DE DADOS DO GRÁFICO
        
        # Ordena por preço (para o drop_duplicates manter o menor)
        df_graph = df_graph.sort_values('valor_cotacao', ascending=True)
        # Remove duplicatas visuais (mantém apenas o menor preço do dia para aquele ano)
        df_graph = df_graph.drop_duplicates(subset=['ano_suprimento', 'data_cotacao'], keep='first')
        
        # IMPORTANTE: Ordena pelo ANO (Eixo X) do menor para o maior
        df_graph = df_graph.sort_values('ano_suprimento', ascending=True)

        # 4. Formatação do Texto (2 casas decimais)
        df_graph['texto_valor'] = df_graph['valor_cotacao'].apply(lambda x: f"{x:.2f}") 

        # 5. Criação do Gráfico
        fig_scatter = px.scatter(
            df_graph,
            x="ano_suprimento",
            y="data_cotacao",
            color="valor_cotacao",
            text="texto_valor",  # Define o texto que será usado
            color_continuous_scale="RdYlGn_r", 
            hover_data=['comercializadora', 'modalidade', 'valor_cotacao'],
            labels={
                "ano_suprimento": "Ano de Suprimento",
                "data_cotacao": "Data da Cotação",
                "valor_cotacao": "Preço (R$)"
            },
            title="Mapa de Calor de Preços (Valores em R$/MWh)"
        )
        
        # AJUSTE VISUAL: Fonte PRETA, Tamanho maior e Quadrado grande
        fig_scatter.update_traces(
            mode='markers+text',
            textposition='middle center',
            textfont=dict(
                family="Arial Black", 
                size=12,         
                color="black"    
            ),
            marker=dict(
                size=45,         # AUMENTADO PARA 55
                symbol='square', 
                opacity=1,
                line=dict(width=1, color='#333333')
            )
        )

        fig_scatter.update_yaxes(showgrid=True, gridwidth=1, gridcolor='#E5E5E5')
        fig_scatter.update_xaxes(type='category')
        
        st.plotly_chart(fig_scatter, width="stretch")


    st.divider()

    # =====================================
    # ABAS DO DASHBOARD
    # =====================================
    tab1, tab2, tab3, tab4 = st.tabs(["⚡ Matriz de Calor & Tendências", "📈 Histórico Detalhado", "📋 Tabela Detalhada", "📅 Análise Anual Detalhada"])

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
                st.plotly_chart(fig_heat, width="stretch")

        with col_line:
            st.subheader("Curva Forward (Menor Preço)")
            st.caption("Evolução do PREÇO MÍNIMO por Tipo de Energia (considerando filtros ativos)")
            
            df_line = df_filtered.groupby(['ano_suprimento', 'tipo_energia'])['valor_cotacao'].min().reset_index()
            
            fig_line = px.line(
                df_line,
                x='ano_suprimento',
                y='valor_cotacao',
                color='tipo_energia',
                markers=True,
                symbol='tipo_energia'
            )
            fig_line.update_xaxes(type='category')
            st.plotly_chart(fig_line, width="stretch")

    # --- ABA 2: COMPARATIVO TEMPORAL DO MENOR PREÇO ---
    with tab2:
        st.subheader("📉 Comparativo Temporal do Melhor Preço")
        st.caption("Evolução do preço ao longo das datas de cotação para o melhor produto selecionado")

        # 1. Encontrar o menor preço dentro do filtro atual
        idx_min_global = df_filtered['valor_cotacao'].idxmin()
        base_row = df_filtered.loc[idx_min_global]

        st.markdown(
            f"""
            **Produto Destaque (Menor Preço Global)**
            - 🏢 Comercializadora: **{base_row['comercializadora']}**
            - ⚡ Tipo: **{base_row['tipo_energia']}** | 🌎 Sub: **{base_row['submercado']}**
            - 📅 Ano: **{int(base_row['ano_suprimento'])}** | 💰 Preço: **R$ {base_row['valor_cotacao']:.2f}**
            """
        )

        # 2. Buscar histórico completo desse mesmo produto
        df_hist = df[
            (df['comercializadora'] == base_row['comercializadora']) &
            (df['tipo_energia'] == base_row['tipo_energia']) &
            (df['submercado'] == base_row['submercado']) &
            (df['ano_suprimento'] == base_row['ano_suprimento'])
        ].sort_values('data_cotacao')

        # 4. Gráfico de linha temporal
        fig_line_hist = px.line(
            df_hist,
            x='data_cotacao',
            y='valor_cotacao',
            markers=True,
            title="Histórico de Preço por Data de Cotação"
        )

        st.plotly_chart(fig_line_hist, width="stretch")

        # 7. Tabela auxiliar
        with st.expander("📋 Ver histórico detalhado"):
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
        
        st.dataframe(
            df_filtered.sort_values(['ano_suprimento', 'mes_suprimento', 'valor_cotacao']),
            width="stretch",
            column_config=col_config,
            hide_index=True
        )

    # --- ABA 4: ANÁLISE ANUAL DETALHADA ---
    with tab4:
        st.subheader("Análise Detalhada por Ano")

        for ano in anos_sel:
            st.markdown(f"### 📅 Ano {int(ano)}")
            df_ano_detalhe = df_filtered[df_filtered['ano_suprimento'] == ano]

            if df_ano_detalhe.empty:
                st.info(f"Sem dados para o ano {ano} com os filtros atuais.")
            else:
                tipos_neste_ano = df_ano_detalhe['tipo_energia'].unique()
                cols_tipos = st.columns(len(tipos_neste_ano) if len(tipos_neste_ano) > 0 else 1)

                for i, tipo in enumerate(tipos_neste_ano):
                    with cols_tipos[i]:
                        st.markdown(f"**⚡ {tipo}**")
                        df_tipo = df_ano_detalhe[df_ano_detalhe['tipo_energia'] == tipo]

                        if not df_tipo.empty:
                            preco_medio = df_tipo['valor_cotacao'].mean()
                            idx_min = df_tipo['valor_cotacao'].idxmin()
                            melhor_preco = df_tipo.loc[idx_min, 'valor_cotacao']
                            melhor_comerc = df_tipo.loc[idx_min, 'comercializadora']
                            idx_max = df_tipo['valor_cotacao'].idxmax()
                            maior_preco = df_tipo.loc[idx_max, 'valor_cotacao']
                            
                            volatilidade = df_tipo['valor_cotacao'].std()

                            st.metric("Preço Médio", f"R$ {preco_medio:.2f}")
                            st.metric("Melhor Preço", f"R$ {melhor_preco:.2f}", f"{melhor_comerc}", delta_color="off")
                            st.metric("Maior Preço", f"R$ {maior_preco:.2f}", delta_color="off")

                            vol_str = f"R$ {volatilidade:.2f}" if not pd.isna(volatilidade) else "--"
                            st.metric("Volatilidade", vol_str)
                        else:
                            st.caption("Sem cotações para este tipo")