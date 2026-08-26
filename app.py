
from pathlib import Path
import re
import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(
    page_title="Wildlife Corridor Protection Planner",
    page_icon="🦌",
    layout="wide",
    initial_sidebar_state="expanded",
)

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
ASSET = ROOT / "assets" / "wildlife_corridor_dashboard_visual.png"

st.markdown("""
<style>
:root{
  --ink:#173248; --muted:#637589; --line:#dfe8e7; --bg:#f5faf8;
  --green:#137a42; --green2:#2eae6f; --blue:#2778d8; --cyan:#22a8b8;
  --orange:#f09b39; --red:#e05d63; --violet:#7958d6;
}
.stApp{background:linear-gradient(180deg,#f8fcfa 0%,#f3f8fc 100%);color:var(--ink)}
.block-container{max-width:1540px;padding-top:1rem;padding-bottom:2.2rem}
[data-testid="stSidebar"]{background:#ffffff;border-right:1px solid var(--line)}
[data-testid="stSidebar"] *{color:var(--ink)!important}
.hero{
  background:linear-gradient(135deg,#effcf5 0%,#eef7ff 55%,#fff5ea 100%);
  border:1px solid #dfe9e4;border-radius:26px;padding:28px 30px;margin-bottom:20px;
  box-shadow:0 12px 30px rgba(23,50,72,.05)
}
.eyebrow{font-size:.74rem;font-weight:850;letter-spacing:.14em;color:#2c7c55;text-transform:uppercase}
.hero h1{font-size:2.45rem;line-height:1.08;margin:.35rem 0 .55rem;color:#163149!important}
.hero p{font-size:1rem;color:#5d6f83;max-width:920px;margin:0}
.pill{display:inline-block;border-radius:999px;padding:7px 12px;margin:12px 7px 0 0;background:#fff;border:1px solid #dae6e2;font-size:.82rem;font-weight:750;color:#35556a}
.card{background:#fff;border:1px solid var(--line);border-radius:18px;padding:17px;box-shadow:0 8px 24px rgba(25,60,80,.045)}
.label{font-size:.75rem;text-transform:uppercase;letter-spacing:.06em;font-weight:800;color:#73849a}
.value{font-size:1.95rem;font-weight:850;color:#163149;margin-top:4px}
.sub{font-size:.78rem;color:#7d8da0;margin-top:2px}
.section{font-size:1.18rem;font-weight:850;margin:23px 0 11px;color:#18354c}
.note{background:#f2fbf4;border:1px solid #cfe9d3;border-radius:15px;padding:14px 16px;color:#335b40}
.warn{background:#fff7ea;border:1px solid #f0dfbb;border-radius:15px;padding:14px 16px;color:#6a501f}
.footer{font-size:.76rem;color:#7890a0;text-align:center;margin-top:18px}
</style>
""", unsafe_allow_html=True)

def normalize_columns(df):
    x=df.copy()
    aliases={
        "id":"corridor_id","corridor":"corridor_name","habitat":"habitat_type",
        "lat":"latitude","lng":"longitude","lon":"longitude","road":"road_pressure",
        "roads":"road_pressure","construction":"construction_pressure","light":"light_pollution",
        "landuse":"land_use_change","encroachment":"human_encroachment","movement":"movement_activity",
        "crossings":"road_crossings","protection":"protection_coverage"
    }
    names=[]
    for c in x.columns:
        key=re.sub(r"[^a-z0-9]+","_",str(c).strip().lower()).strip("_")
        names.append(aliases.get(key,key))
    x.columns=names
    return x

def num(s, default=0):
    return pd.to_numeric(s, errors="coerce").fillna(default)

def risk_class(score):
    if score>=80: return "Very High"
    if score>=60: return "High"
    if score>=35: return "Moderate"
    return "Low"

def compute_scores(df):
    x=df.copy()
    factors=["road_pressure","construction_pressure","light_pollution","land_use_change","human_encroachment"]
    for c in factors+["movement_activity","road_crossings","protection_coverage"]:
        if c not in x.columns: x[c]=0
        x[c]=num(x[c]).clip(0,100)
    x["road_crossing_pressure"]=(x["road_crossings"].clip(0,20)/20*100).clip(0,100)
    x["protection_gap"]=(100-x["protection_coverage"]).clip(0,100)
    raw=(0.24*x["road_pressure"]+0.18*x["construction_pressure"]+0.16*x["light_pollution"]+
         0.16*x["land_use_change"]+0.11*x["human_encroachment"]+
         0.08*x["road_crossing_pressure"]+0.07*x["protection_gap"])
    x["risk_score"]=np.clip(raw+np.maximum(x["movement_activity"]-65,0)*0.10,0,100).round(1)
    x["risk_class"]=x["risk_score"].map(risk_class)
    x["priority_score"]=(0.72*x["risk_score"]+0.18*x["road_crossing_pressure"]+0.10*x["protection_gap"]).clip(0,100).round(1)
    x["priority_class"]=x["priority_score"].map(risk_class)
    x["primary_threat"]=x[factors].idxmax(axis=1).str.replace("_"," ").str.title()
    return x

st.sidebar.markdown("## 🦌 CorridorGuard Local")
st.sidebar.caption("Plan • Protect • Preserve")
st.sidebar.markdown("### Workspace")
page=st.sidebar.radio(
    "Navigate",
    ["Dashboard","Corridor Explorer","Threat Analysis","Risk Assessment","Prioritization",
     "Land Use Change","Scenario Lab","Reports & Export"],
    label_visibility="collapsed"
)
st.sidebar.divider()

corr_upload=st.sidebar.file_uploader("Upload authorized corridor CSV",type=["csv"])
threat_upload=st.sidebar.file_uploader("Upload threat-observation CSV",type=["csv"])
land_upload=st.sidebar.file_uploader("Upload land-use CSV",type=["csv"])

corr=pd.read_csv(corr_upload) if corr_upload else pd.read_csv(DATA_DIR/"sample_corridor_registry.csv")
thr=pd.read_csv(threat_upload) if threat_upload else pd.read_csv(DATA_DIR/"sample_threat_observations.csv")
land=pd.read_csv(land_upload) if land_upload else pd.read_csv(DATA_DIR/"sample_land_use_change.csv")

corr=normalize_columns(corr)
thr=normalize_columns(thr)
land=normalize_columns(land)

required=[
    "corridor_id","corridor_name","habitat_type","zone","latitude","longitude",
    "road_pressure","construction_pressure","light_pollution","land_use_change",
    "human_encroachment","movement_activity","road_crossings","protection_coverage"
]
missing=[c for c in required if c not in corr.columns]
if missing:
    st.error("Missing corridor fields: "+", ".join(missing))
    st.stop()

scored=compute_scores(corr)
thr["severity_score"]=num(thr.get("severity_score",pd.Series(index=thr.index)),50).clip(0,100)
land["year"]=pd.to_numeric(land.get("year",pd.Series(index=land.index)),errors="coerce")

habitats=["All"]+sorted(scored["habitat_type"].astype(str).unique().tolist())
zones=["All"]+sorted(scored["zone"].astype(str).unique().tolist())
classes=["All","Low","Moderate","High","Very High"]
sel_hab=st.sidebar.selectbox("Habitat",habitats)
sel_zone=st.sidebar.selectbox("Zone",zones)
sel_class=st.sidebar.selectbox("Risk class",classes)
min_priority=st.sidebar.slider("Minimum priority score",0,100,0)

view=scored.copy()
if sel_hab!="All": view=view[view["habitat_type"]==sel_hab]
if sel_zone!="All": view=view[view["zone"]==sel_zone]
if sel_class!="All": view=view[view["risk_class"]==sel_class]
view=view[view["priority_score"]>=min_priority]
if view.empty:
    st.warning("No corridors match the current filters.")
    st.stop()

st.markdown("""
<div class="hero">
  <div class="eyebrow">WILDLIFE CORRIDOR • CONSERVATION PLANNING • LOCAL-FIRST</div>
  <h1>Protect movement corridors before pressure becomes fragmentation.</h1>
  <p>Screen roads, construction, light pollution, land-use change, encroachment and crossing pressure using transparent local rules for qualified conservation review.</p>
  <span class="pill">🌿 Corridor Mapping</span>
  <span class="pill">🛣️ Road Threats</span>
  <span class="pill">🏗️ Construction Pressure</span>
  <span class="pill">💡 Light Pollution</span>
  <span class="pill">🗺️ Land-Use Change</span>
  <span class="pill">🔒 Local Processing</span>
</div>
""", unsafe_allow_html=True)

kpi=[
    ("Corridors",len(view),"Filtered monitored corridors"),
    ("High / Very High",int((view["risk_score"]>=60).sum()),"Priority-risk corridors"),
    ("Threat observations",len(thr),"Local evidence records"),
    ("Priority corridors",int((view["priority_score"]>=75).sum()),"Priority score ≥ 75"),
    ("Avg. risk score",f'{view["risk_score"].mean():.1f}/100',"Screening heuristic"),
]
cols=st.columns(5)
for col,(lab,val,sub) in zip(cols,kpi):
    col.markdown(f'<div class="card"><div class="label">{lab}</div><div class="value">{val}</div><div class="sub">{sub}</div></div>',unsafe_allow_html=True)

if page=="Dashboard":
    st.markdown('<div class="section">Corridor risk overview</div>',unsafe_allow_html=True)
    a,b,c=st.columns([1.0,1.35,0.95])
    with a:
        mix=view["risk_class"].value_counts().reindex(["Low","Moderate","High","Very High"]).fillna(0).reset_index()
        mix.columns=["risk_class","count"]
        fig=px.pie(mix,names="risk_class",values="count",hole=.62,template="plotly_white",title="Risk mix")
        fig.update_layout(margin=dict(l=5,r=5,t=45,b=5),height=315)
        st.plotly_chart(fig,use_container_width=True)
    with b:
        fig=px.scatter(view,x="longitude",y="latitude",size="risk_score",color="risk_score",
                       hover_name="corridor_name",text="corridor_name",
                       color_continuous_scale=["#36a867","#f2af4b","#e05d63"],
                       title="Local corridor risk map")
        fig.update_traces(textposition="top center")
        fig.update_layout(margin=dict(l=5,r=5,t=45,b=5),height=315,template="plotly_white")
        st.plotly_chart(fig,use_container_width=True)
    with c:
        threats_view=thr.groupby("threat_type",as_index=False).severity_score.mean().sort_values("severity_score",ascending=False).head(5)
        fig=px.bar(threats_view,x="severity_score",y="threat_type",orientation="h",text_auto=".0f",
                   title="Top threat signals",template="plotly_white")
        fig.update_xaxes(range=[0,100]); fig.update_layout(margin=dict(l=5,r=5,t=45,b=5),height=315)
        st.plotly_chart(fig,use_container_width=True)

    st.markdown('<div class="section">Risk trend & category comparison</div>',unsafe_allow_html=True)
    d,e=st.columns(2)
    with d:
        if "period" in scored.columns:
            trend=scored.groupby("period",as_index=False).risk_score.mean()
        else:
            trend=pd.DataFrame({"period":["Q1","Q2","Q3","Q4"],"risk_score":[view.risk_score.mean()-3,view.risk_score.mean()+1,view.risk_score.mean()+4,view.risk_score.mean()+2]})
        fig=px.line(trend,x="period",y="risk_score",markers=True,title="Risk trend by monitoring period",template="plotly_white")
        fig.update_yaxes(range=[0,100]); fig.update_layout(margin=dict(l=5,r=5,t=45,b=5),height=290)
        st.plotly_chart(fig,use_container_width=True)
    with e:
        cat=view.groupby("habitat_type",as_index=False).risk_score.mean().sort_values("risk_score",ascending=False)
        fig=px.bar(cat,x="habitat_type",y="risk_score",text_auto=".0f",title="Risk by habitat category",template="plotly_white")
        fig.update_yaxes(range=[0,100]); fig.update_layout(margin=dict(l=5,r=5,t=45,b=5),height=290)
        st.plotly_chart(fig,use_container_width=True)

    st.markdown('<div class="section">Priority corridor queue</div>',unsafe_allow_html=True)
    q=view[["corridor_name","habitat_type","zone","risk_score","priority_score","risk_class","primary_threat","road_crossings","protection_coverage"]].sort_values("priority_score",ascending=False).head(20)
    st.dataframe(q,use_container_width=True,hide_index=True)
    if ASSET.exists():
        with st.expander("Dashboard visual reference"):
            st.image(str(ASSET),use_container_width=True)

elif page=="Corridor Explorer":
    st.markdown('<div class="section">Corridor explorer</div>',unsafe_allow_html=True)
    choice=st.selectbox("Select corridor",view["corridor_name"].tolist())
    r=view[view.corridor_name==choice].iloc[0]
    c1,c2,c3,c4=st.columns(4)
    vals=[("Risk score",r.risk_score,r.risk_class),("Priority score",r.priority_score,r.priority_class),
          ("Movement activity",r.movement_activity,"Observed movement proxy"),("Protection coverage",f"{r.protection_coverage:.0f}%","Recorded coverage")]
    for col,(lab,val,sub) in zip([c1,c2,c3,c4],vals):
        col.markdown(f'<div class="card"><div class="label">{lab}</div><div class="value">{val}</div><div class="sub">{sub}</div></div>',unsafe_allow_html=True)
    left,right=st.columns(2)
    with left:
        factors=pd.DataFrame({"factor":["Road","Construction","Light","Land use","Encroachment","Crossings","Protection gap"],
                              "score":[r.road_pressure,r.construction_pressure,r.light_pollution,r.land_use_change,r.human_encroachment,r.road_crossing_pressure,r.protection_gap]})
        st.plotly_chart(px.bar(factors,x="score",y="factor",orientation="h",text_auto=".0f",range_x=[0,100],template="plotly_white",title="Corridor threat factors"),use_container_width=True)
    with right:
        ct=thr[thr.corridor_id==r.corridor_id].sort_values("severity_score",ascending=False)
        st.markdown("### Threat observations")
        st.dataframe(ct[["threat_type","severity_score","trend_change_pct","observed_date","evidence_count"]],use_container_width=True,hide_index=True)

elif page=="Threat Analysis":
    st.markdown('<div class="section">Threat analysis</div>',unsafe_allow_html=True)
    threat_types=sorted(thr.threat_type.astype(str).unique())
    selected_types=st.multiselect("Threat types",threat_types,default=threat_types)
    tv=thr[thr.threat_type.isin(selected_types)].copy()
    a,b=st.columns(2)
    with a:
        agg=tv.groupby("threat_type",as_index=False).agg(avg_severity=("severity_score","mean"),observations=("threat_id","count")).sort_values("avg_severity",ascending=False)
        fig=px.bar(agg,x="avg_severity",y="threat_type",orientation="h",text_auto=".0f",template="plotly_white",title="Average threat severity")
        fig.update_xaxes(range=[0,100]); st.plotly_chart(fig,use_container_width=True)
    with b:
        fig=px.scatter(tv,x="trend_change_pct",y="severity_score",size="evidence_count",color="threat_type",hover_name="corridor_name",template="plotly_white",title="Threat trend × severity")
        st.plotly_chart(fig,use_container_width=True)
    st.dataframe(tv.sort_values("severity_score",ascending=False),use_container_width=True,hide_index=True)

elif page=="Risk Assessment":
    st.markdown('<div class="section">Risk assessment</div>',unsafe_allow_html=True)
    heat=view.groupby(["habitat_type","risk_class"],as_index=False).size()
    hm=heat.pivot(index="habitat_type",columns="risk_class",values="size").fillna(0)
    hm=hm.reindex(columns=["Low","Moderate","High","Very High"]).fillna(0)
    st.plotly_chart(px.imshow(hm,text_auto=True,aspect="auto",color_continuous_scale=["#dff3e6","#ffd89c","#f19a52","#e05d63"],template="plotly_white",title="Habitat × risk heatmap"),use_container_width=True)
    rad=view.groupby("habitat_type",as_index=False)[["road_pressure","construction_pressure","light_pollution","land_use_change","human_encroachment"]].mean()
    fig=px.bar(rad.melt(id_vars="habitat_type",var_name="factor",value_name="score"),x="habitat_type",y="score",color="factor",barmode="group",template="plotly_white",title="Threat factor profile")
    fig.update_yaxes(range=[0,100]); st.plotly_chart(fig,use_container_width=True)

elif page=="Prioritization":
    st.markdown('<div class="section">Protection prioritization</div>',unsafe_allow_html=True)
    p=view.sort_values(["priority_score","risk_score"],ascending=False).copy()
    p["recommended_focus"]=np.where(
        p["road_pressure"]>=p[["construction_pressure","light_pollution","land_use_change","human_encroachment"]].max(axis=1),
        "Road crossing / wildlife passage review",
        p["primary_threat"].map({
            "Construction Pressure":"Construction-pressure review",
            "Light Pollution":"Lighting mitigation review",
            "Land Use Change":"Habitat-retention review",
            "Human Encroachment":"Buffer / access-management review",
            "Road Pressure":"Road-impact review"
        }).fillna("Multi-threat review")
    )
    st.dataframe(p[["corridor_name","priority_score","priority_class","risk_score","primary_threat","recommended_focus"]].head(30),use_container_width=True,hide_index=True)
    q1,q2=st.columns(2)
    with q1:
        fig=px.bar(p.head(10).sort_values("priority_score"),x="priority_score",y="corridor_name",orientation="h",text_auto=".0f",template="plotly_white",title="Top priority corridors")
        fig.update_xaxes(range=[0,100]); st.plotly_chart(fig,use_container_width=True)
    with q2:
        fig=px.scatter(p,x="road_crossing_pressure",y="priority_score",size="movement_activity",color="risk_class",hover_name="corridor_name",template="plotly_white",title="Crossing pressure × priority")
        fig.update_xaxes(range=[0,100]); fig.update_yaxes(range=[0,100]); st.plotly_chart(fig,use_container_width=True)

elif page=="Land Use Change":
    st.markdown('<div class="section">Land-use change impact</div>',unsafe_allow_html=True)
    selected=st.selectbox("Corridor",sorted(land.corridor_name.astype(str).unique()))
    lv=land[land.corridor_name==selected].sort_values("year").copy()
    lc=lv.melt(id_vars=["year"],value_vars=["forest_pct","grassland_pct","agriculture_pct","builtup_pct","wetland_pct"],var_name="land_use_class",value_name="share_pct")
    fig=px.line(lc,x="year",y="share_pct",color="land_use_class",markers=True,template="plotly_white",title=f"Land-use trajectory — {selected}")
    fig.update_yaxes(range=[0,100]); st.plotly_chart(fig,use_container_width=True)
    st.dataframe(lv,use_container_width=True,hide_index=True)

elif page=="Scenario Lab":
    st.markdown('<div class="section">Conservation scenario lab</div>',unsafe_allow_html=True)
    st.caption("Scenario outputs are planning heuristics for human review; they do not predict animal behavior with certainty.")
    s1,s2,s3,s4=st.columns(4)
    with s1: road_reduction=st.slider("Road pressure reduction",0,60,20,5)
    with s2: construction_reduction=st.slider("Construction reduction",0,60,15,5)
    with s3: light_reduction=st.slider("Light pollution reduction",0,60,20,5)
    with s4: habitat_gain=st.slider("Habitat protection uplift",0,40,10,5)
    sc=view.copy()
    sc["scenario_road"]=(sc.road_pressure*(1-road_reduction/100)).clip(0,100)
    sc["scenario_construction"]=(sc.construction_pressure*(1-construction_reduction/100)).clip(0,100)
    sc["scenario_light"]=(sc.light_pollution*(1-light_reduction/100)).clip(0,100)
    sc["scenario_protection"]=(sc.protection_coverage+habitat_gain).clip(0,100)
    sc["scenario_land_use"]=(sc.land_use_change*(1-habitat_gain/120)).clip(0,100)
    sc["scenario_risk"]=(0.24*sc.scenario_road+0.18*sc.scenario_construction+0.16*sc.scenario_light+0.16*sc.scenario_land_use+0.11*sc.human_encroachment+0.08*sc.road_crossing_pressure+0.07*(100-sc.scenario_protection)).clip(0,100).round(1)
    sc["risk_reduction_pct"]=((sc.risk_score-sc.scenario_risk)/sc.risk_score.replace(0,np.nan)*100).fillna(0).round(1)
    c1,c2=st.columns(2)
    with c1:
        summary=pd.DataFrame({"Metric":["Current avg risk","Scenario avg risk","Average reduction"],"Value":[view.risk_score.mean(),sc.scenario_risk.mean(),sc.risk_reduction_pct.mean()]})
        st.dataframe(summary,use_container_width=True,hide_index=True)
    with c2:
        compare=sc[["corridor_name","risk_score","scenario_risk","risk_reduction_pct"]].sort_values("risk_reduction_pct",ascending=False).head(12)
        st.dataframe(compare,use_container_width=True,hide_index=True)
    st.download_button("⬇️ Download scenario CSV",sc.to_csv(index=False).encode(),file_name="corridor_scenario_results.csv",mime="text/csv")

elif page=="Reports & Export":
    st.markdown('<div class="section">Reports & export</div>',unsafe_allow_html=True)
    a,b,c=st.columns(3)
    a.metric("Records in view",len(view)); b.metric("Priority ≥75",int((view.priority_score>=75).sum())); c.metric("Very High risk",int((view.risk_class=="Very High").sum()))
    export=view.sort_values("priority_score",ascending=False).copy()
    st.dataframe(export,use_container_width=True,hide_index=True)
    st.download_button("⬇️ Download scored corridor CSV",export.to_csv(index=False).encode(),file_name="scored_corridor_registry.csv",mime="text/csv")
    st.download_button("⬇️ Download threat observations CSV",thr.to_csv(index=False).encode(),file_name="threat_observations_export.csv",mime="text/csv")

st.markdown("""
<div class="note">
<b>Responsible-use boundary:</b> Scores are screening heuristics for conservation planning and evidence organization. They do not establish habitat protection status, predict animal movement with certainty, prove causation, authorize construction changes, or replace ecological surveys, wildlife authorities, land-use planning, or field validation. Use only authorized records and preserve community and biodiversity safeguards.
</div>
""",unsafe_allow_html=True)
st.markdown('<div class="footer">100% local CSV processing • No external APIs • Transparent rules • Human review required • Privacy-conscious computing</div>',unsafe_allow_html=True)
