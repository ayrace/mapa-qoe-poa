import json, math
from pathlib import Path
import pandas as pd
import streamlit as st
import pydeck as pdk

ROOT=Path(__file__).parent
st.set_page_config(page_title="Mapa QOE – Porto Alegre", page_icon="📡", layout="wide")

@st.cache_data
def load_data():
    seed=json.loads((ROOT/"data/qoe_seed.json").read_text(encoding="utf-8"))
    meta=json.loads((ROOT/"data/node_meta.json").read_text(encoding="utf-8"))
    rows=[]
    for key,p in seed.get("ports",{}).items():
        node=str(p.get("node","")).upper().strip()
        if not node: continue
        m=meta.get(node,{})
        last=pd.to_numeric(p.get("lastScore"),errors="coerce")
        months=p.get("months",{}) or {}
        monthly=[float(v) for v in months.values() if isinstance(v,(int,float))]
        rows.append({
            "Node":node,"Porta":str(p.get("port","")),
            "QOE":float(last) if pd.notna(last) else None,
            "Meses_porta_lt80":sum(v<80 for v in monthly),
            "Regiao":m.get("region") or "A DEFINIR",
            "Bairro":m.get("bairro") or "NÃO INFORMADO",
            "Latitude":m.get("lat"),"Longitude":m.get("lon"),
            "months":months
        })
    ports=pd.DataFrame(rows)
    if ports.empty: return ports,pd.DataFrame()
    def node_months(g):
        labels=["Jan","Fev","Mar","Abr","Mai","Jun","Jul","Ago","Set","Out","Nov","Dez"]
        n=0; available=0
        for mo in labels:
            vals=[r.get(mo) for r in g["months"] if isinstance(r.get(mo),(int,float))]
            if vals:
                available+=1
                if sum(vals)/len(vals)<80: n+=1
        return n,available
    out=[]
    for node,g in ports.groupby("Node"):
        q=g["QOE"].dropna()
        persistence,total_months=node_months(g)
        out.append({
            "Node":node,"Media_atual":q.mean() if len(q) else None,
            "Portas_lt80":int((q<80).sum()),"Portas_validas":int(len(q)),
            "Portas_lt50":int((q<50).sum()),
            "Persistencia":persistence,"Meses_disponiveis":total_months,
            "Regiao":g["Regiao"].iloc[0],"Bairro":g["Bairro"].iloc[0],
            "Latitude":pd.to_numeric(g["Latitude"],errors="coerce").dropna().iloc[0] if pd.to_numeric(g["Latitude"],errors="coerce").notna().any() else None,
            "Longitude":pd.to_numeric(g["Longitude"],errors="coerce").dropna().iloc[0] if pd.to_numeric(g["Longitude"],errors="coerce").notna().any() else None,
        })
    nodes=pd.DataFrame(out)
    return ports,nodes

ports,nodes=load_data()

st.markdown("""
<style>
.block-container{padding-top:.8rem;padding-bottom:2rem;max-width:1500px}
h1{margin-bottom:.1rem}
.qoe-sub{color:#667085;margin-bottom:.65rem}
div[data-testid="stMetric"]{border:1px solid rgba(128,128,128,.18);border-radius:12px;padding:10px}
@media(max-width:700px){.block-container{padding-left:.55rem;padding-right:.55rem;padding-top:.45rem} h1{font-size:1.55rem!important}}
</style>
""",unsafe_allow_html=True)

st.title("MAPA QOE – PORTO ALEGRE")
st.markdown('<div class="qoe-sub">Tratamento preventivo e proativo • leitura geográfica → região → bairro → node → persistência</div>',unsafe_allow_html=True)

if nodes.empty:
    st.error("Base QOE vazia.")
    st.stop()

tabs=st.tabs(["🗺️ Mapa","📉 Radar de Queda","👷 Força de Trabalho","🔄 Atualizar Base"])

with tabs[0]:
    located=nodes.dropna(subset=["Latitude","Longitude"]).copy()
    located["Status"]=pd.cut(located["Media_atual"],[-math.inf,79.999,84.999,math.inf],labels=["ATUAÇÃO <80","EM ANÁLISE 80–84,9","ESTÁVEL ≥85"])
    def color(v):
        if pd.isna(v): return [130,130,130,210]
        if v<80:return [235,70,82,235]
        if v<85:return [240,183,50,235]
        return [45,180,110,220]
    located["color"]=located["Media_atual"].map(color)
    located["line_color"]=located["Persistencia"].map(lambda x:[124,58,237,255] if x>=4 else [255,255,255,235])
    located["Resumo"]=located.apply(lambda r:f'{r.Portas_lt80}/{r.Portas_validas} portas <80 • {r.Persistencia}/{r.Meses_disponiveis} meses fora',axis=1)
    layer=pdk.Layer("ScatterplotLayer",data=located,id="nodes",get_position="[Longitude, Latitude]",
        get_radius=48,radius_min_pixels=5,radius_max_pixels=11,get_fill_color="color",get_line_color="line_color",
        line_width_min_pixels=2,stroked=True,pickable=True,auto_highlight=True)
    view=pdk.ViewState(latitude=float(located.Latitude.mean()),longitude=float(located.Longitude.mean()),zoom=10.65,pitch=0)
    tip={"html":"<b>{Node}</b><br>Média atual: {Media_atual}<br>{Resumo}<br>{Regiao} • {Bairro}",
         "style":{"backgroundColor":"rgba(9,26,51,.96)","color":"white","borderRadius":"10px"}}
    st.pydeck_chart(pdk.Deck(layers=[layer],initial_view_state=view,tooltip=tip,map_style="light"),
                    use_container_width=True,height=570)
    st.caption("Todos os nodes permanecem visíveis. O objetivo é enxergar concentrações geográficas de nodes ruins próximos.")

    bad_ports=ports[ports.QOE<80].copy()
    reg=bad_ports.groupby("Regiao").agg(Portas_lt80=("QOE","size"),Nodes_afetados=("Node","nunique")).reset_index().sort_values("Portas_lt80",ascending=False)
    bai=bad_ports.groupby(["Bairro","Regiao"]).agg(Portas_lt80=("QOE","size"),Nodes_afetados=("Node","nunique")).reset_index().sort_values("Portas_lt80",ascending=False)
    rank=nodes[nodes.Portas_lt80>0].sort_values(["Media_atual","Persistencia","Portas_lt80"],ascending=[True,False,False])
    c1,c2,c3=st.columns(3)
    with c1:
        st.subheader("Impacto por região")
        st.dataframe(reg,hide_index=True,use_container_width=True)
    with c2:
        st.subheader("Bairros mais impactados")
        st.dataframe(bai.head(15),hide_index=True,use_container_width=True)
    with c3:
        st.subheader("Nodes mais impactados")
        st.dataframe(rank[["Node","Media_atual","Portas_lt80","Persistencia","Bairro"]].head(15),
                     hide_index=True,use_container_width=True,column_config={"Media_atual":st.column_config.NumberColumn(format="%.1f")})

with tabs[1]:
    st.subheader("Distribuição por faixa QOE")
    bins=[-math.inf,50,60,70,80,85,math.inf]
    labels=["<50","50–59,9","60–69,9","70–79,9","80–84,9","≥85"]
    tmp=nodes.dropna(subset=["Media_atual"]).copy()
    tmp["Faixa"]=pd.cut(tmp.Media_atual,bins=bins,labels=labels,right=False)
    dist=tmp.groupby("Faixa",observed=False).size().reset_index(name="Nodes")
    st.bar_chart(dist.set_index("Faixa"))

    st.subheader("Persistência abaixo de 80")
    maxm=int(nodes.Meses_disponiveis.max() or 0)
    pers=nodes[nodes.Persistencia>0].groupby(["Persistencia","Meses_disponiveis"]).size().reset_index(name="Nodes")
    pers=pers.sort_values(["Persistencia","Meses_disponiveis"],ascending=False)
    pers["Classe"]=pers.apply(lambda r:f'{int(r.Persistencia)}/{int(r.Meses_disponiveis)} meses',axis=1)
    st.dataframe(pers[["Classe","Nodes"]],hide_index=True,use_container_width=True)

    st.subheader("Piores nodes agora")
    radar=nodes.sort_values(["Media_atual","Persistencia","Portas_lt80"],ascending=[True,False,False])
    st.dataframe(radar[["Node","Media_atual","Portas_lt80","Portas_validas","Persistencia","Meses_disponiveis","Regiao","Bairro"]].head(50),
                 hide_index=True,use_container_width=True,column_config={"Media_atual":st.column_config.NumberColumn(format="%.1f")})

with tabs[2]:
    st.subheader("Prioridade para direcionamento")
    st.caption("Combina gravidade atual, persistência e quantidade de portas abaixo de 80. A proximidade geográfica deve ser validada no mapa.")
    work=nodes[nodes.Portas_lt80>0].copy()
    work["Prioridade"]=((80-work.Media_atual).clip(lower=0)*2 + work.Persistencia*5 + work.Portas_lt80*4)
    work=work.sort_values(["Prioridade","Persistencia","Portas_lt80"],ascending=False)
    st.dataframe(work[["Node","Prioridade","Media_atual","Portas_lt80","Persistencia","Regiao","Bairro"]].head(60),
                 hide_index=True,use_container_width=True,
                 column_config={"Media_atual":st.column_config.NumberColumn(format="%.1f"),"Prioridade":st.column_config.NumberColumn(format="%.1f")})
    st.info("Nesta primeira versão, a pontuação é apenas um organizador operacional. Vamos equalizar os pesos com o uso real antes de tratá-la como regra definitiva.")

with tabs[3]:
    st.subheader("Atualização da base")
    st.write("Versão inicial online para validar a estrutura. A próxima etapa é ligar esta tela ao mesmo fluxo de atualização do repositório GitHub usado na operação, sem depender de HTML local.")
    st.code("data/qoe_seed.json\ndata/node_meta.json",language="text")

st.caption("Mapa QOE POA • GitHub/Streamlit V1 • Base histórica Jan–Set/2026")
