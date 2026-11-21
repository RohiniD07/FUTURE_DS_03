import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(
    page_title="Marketing Funnel & Conversion Dashboard | Task 3",
    page_icon="📉",
    layout="wide",
)


@st.cache_data
def generate_sample_data() -> pd.DataFrame:
    np.random.seed(42)
    channels = ["Organic Search", "Paid Search", "Paid Social", "Email", "Referral"]
    months = ["2026-06", "2026-07", "2026-08"]

    profiles = {
        "Organic Search": (14000, 0.065, 0.28, 0.42),
        "Paid Search": (12000, 0.055, 0.24, 0.35),
        "Paid Social": (18000, 0.032, 0.16, 0.25),
        "Email": (5000, 0.110, 0.36, 0.48),
        "Referral": (4000, 0.085, 0.32, 0.45),
    }

    rows = []
    for idx_m, m in enumerate(months):
        growth = 1.0 + idx_m * 0.06
        for ch, (base_vis, v2l, l2q, q2c) in profiles.items():
            visitors = int(base_vis * growth * np.random.uniform(0.92, 1.08))
            leads = int(visitors * v2l * np.random.uniform(0.90, 1.10))
            mqls = int(leads * l2q * np.random.uniform(0.90, 1.10))
            customers = int(mqls * q2c * np.random.uniform(0.88, 1.12))
            avg_order_val = np.random.uniform(120, 260)
            revenue = round(customers * avg_order_val, 2)
            rows.append({
                "Month": m,
                "Channel": ch,
                "Visitors": visitors,
                "Leads": leads,
                "Qualified_Leads": mqls,
                "Customers": customers,
                "Revenue": revenue,
            })
    return pd.DataFrame(rows)


def prepare_funnel_df(raw_df: pd.DataFrame) -> pd.DataFrame:
    required_cols = ["Month", "Channel", "Visitors", "Leads", "Qualified_Leads", "Customers", "Revenue"]
    df = raw_df.copy()
    for col in required_cols:
        if col not in df.columns:
            st.error(f"Missing required column: '{col}'. Using sample dataset instead.")
            return prepare_funnel_df(generate_sample_data())

    df = df.dropna(subset=["Month", "Channel", "Visitors", "Leads", "Qualified_Leads", "Customers"])
    for col in ["Visitors", "Leads", "Qualified_Leads", "Customers"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)
    df["Revenue"] = pd.to_numeric(df["Revenue"], errors="coerce").fillna(0.0)
    df["Month"] = df["Month"].astype(str)
    df["Channel"] = df["Channel"].astype(str)

    df["Visitor_to_Lead_%"] = np.where(df["Visitors"] > 0, df["Leads"] / df["Visitors"] * 100, 0.0)
    df["Lead_to_Customer_%"] = np.where(df["Leads"] > 0, df["Customers"] / df["Leads"] * 100, 0.0)
    df["Overall_Conv_%"] = np.where(df["Visitors"] > 0, df["Customers"] / df["Visitors"] * 100, 0.0)
    df["Revenue_per_Visitor"] = np.where(df["Visitors"] > 0, df["Revenue"] / df["Visitors"], 0.0)
    return df


# ---------------------------------------------------------
# SIDEBAR CONTROLS
# ---------------------------------------------------------
st.sidebar.title("Funnel Filters")
uploaded_file = st.sidebar.file_uploader("Upload Funnel CSV (optional)", type=["csv"])

if uploaded_file is not None:
    df = prepare_funnel_df(pd.read_csv(uploaded_file))
else:
    df = prepare_funnel_df(generate_sample_data())

all_months = sorted(df["Month"].unique())
all_channels = sorted(df["Channel"].unique())

selected_months = st.sidebar.multiselect("Month", options=all_months, default=all_months)
selected_channels = st.sidebar.multiselect("Channel", options=all_channels, default=all_channels)
rev_metric = st.sidebar.radio("Channel Value Metric", ["Revenue", "Revenue_per_Visitor"])

filtered = df[
    df["Month"].isin(selected_months if selected_months else all_months)
    & df["Channel"].isin(selected_channels if selected_channels else all_channels)
]

if filtered.empty:
    st.warning("No rows match the selected filters. Showing all data.")
    filtered = df

# ---------------------------------------------------------
# HEADER & KPI METRICS
# ---------------------------------------------------------
st.title("Marketing Funnel & Conversion Performance")
st.caption("Future Interns — Data Science & Analytics | Task 3 Interactive Dashboard")

tot_visitors = int(filtered["Visitors"].sum())
tot_leads = int(filtered["Leads"].sum())
tot_mqls = int(filtered["Qualified_Leads"].sum())
tot_customers = int(filtered["Customers"].sum())
tot_revenue = float(filtered["Revenue"].sum())
overall_conv = (tot_customers / tot_visitors * 100) if tot_visitors > 0 else 0.0
v2l_conv = (tot_leads / tot_visitors * 100) if tot_visitors > 0 else 0.0

k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Visitors", f"{tot_visitors:,}")
k2.metric("Leads", f"{tot_leads:,}", f"{v2l_conv:.2f}% of visitors")
k3.metric("Qualified Leads", f"{tot_mqls:,}")
k4.metric("Customers", f"{tot_customers:,}", f"{overall_conv:.2f}% overall conv.")
k5.metric("Revenue", f"${tot_revenue:,.2f}")

# ---------------------------------------------------------
# STAGE FUNNEL & DROP-OFF TABLE
# ---------------------------------------------------------
stage_counts = pd.DataFrame({
    "Stage": ["Visitors", "Leads", "Qualified Leads", "Customers"],
    "Users": [tot_visitors, tot_leads, tot_mqls, tot_customers],
})
stage_counts["Prev_Users"] = stage_counts["Users"].shift(1)
stage_counts["Stage_Conv_%"] = np.where(
    stage_counts["Prev_Users"].notna() & (stage_counts["Prev_Users"] > 0),
    stage_counts["Users"] / stage_counts["Prev_Users"] * 100,
    100.0,
).round(2)
stage_counts["Drop_Off_Users"] = np.where(
    stage_counts["Prev_Users"].notna(),
    (stage_counts["Prev_Users"] - stage_counts["Users"]).clip(lower=0),
    0,
).astype(int)
stage_counts["Drop_Off_%"] = np.where(
    stage_counts["Stage"] == "Visitors",
    0.0,
    (100.0 - stage_counts["Stage_Conv_%"]).clip(lower=0.0),
).round(2)

col_left, col_right = st.columns([1.2, 1])

with col_left:
    st.subheader("Conversion Funnel by Stage")
    fig_funnel = go.Figure(
        go.Funnel(
            y=stage_counts["Stage"],
            x=stage_counts["Users"],
            textinfo="value+percent initial+percent previous",
            marker={"color": ["#2563EB", "#3B82F6", "#60A5FA", "#10B981"]},
        )
    )
    fig_funnel.update_layout(margin=dict(l=10, r=10, t=20, b=10), height=360)
    st.plotly_chart(fig_funnel, use_container_width=True)

with col_right:
    st.subheader("Stage Drop-Off Breakdown")
    display_stages = stage_counts[["Stage", "Users", "Stage_Conv_%", "Drop_Off_Users", "Drop_Off_%"]]
    st.dataframe(display_stages, use_container_width=True, hide_index=True)

    # Identify worst drop-off stage after Visitors
    dropoff_only = stage_counts[stage_counts["Stage"] != "Visitors"]
    if not dropoff_only.empty:
        worst_row = dropoff_only.loc[dropoff_only["Drop_Off_Users"].idxmax()]
        st.info(
            f"Largest volume loss occurs at **{worst_row['Stage']}** "
            f"({worst_row['Drop_Off_Users']:,} users lost, {worst_row['Drop_Off_%']:.1f}% drop from prior stage)."
        )

# ---------------------------------------------------------
# CHANNEL & MONTHLY PERFORMANCE
# ---------------------------------------------------------
st.subheader("Channel & Time Performance")

ch_grp = (
    filtered.groupby("Channel", as_index=False)[["Visitors", "Leads", "Qualified_Leads", "Customers", "Revenue"]]
    .sum()
)
ch_grp["Visitor_to_Lead_%"] = np.where(ch_grp["Visitors"] > 0, ch_grp["Leads"] / ch_grp["Visitors"] * 100, 0.0).round(2)
ch_grp["Lead_to_Customer_%"] = np.where(ch_grp["Leads"] > 0, ch_grp["Customers"] / ch_grp["Leads"] * 100, 0.0).round(2)
ch_grp["Overall_Conv_%"] = np.where(ch_grp["Visitors"] > 0, ch_grp["Customers"] / ch_grp["Visitors"] * 100, 0.0).round(2)
ch_grp["Revenue_per_Visitor"] = np.where(ch_grp["Visitors"] > 0, ch_grp["Revenue"] / ch_grp["Visitors"], 0.0).round(2)
ch_grp = ch_grp.sort_values(rev_metric, ascending=False)

c1, c2 = st.columns(2)

with c1:
    metric_label = "Revenue ($)" if rev_metric == "Revenue" else "Revenue per Visitor ($)"
    fig_ch = px.bar(
        ch_grp,
        x="Channel",
        y=rev_metric,
        color="Overall_Conv_%",
        text_auto=".2f",
        labels={rev_metric: metric_label, "Overall_Conv_%": "Overall Conv. (%)"},
        title=f"{metric_label} by Channel (Colored by Overall Conv. %)",
        color_continuous_scale="Tealgrn",
    )
    fig_ch.update_layout(height=360, margin=dict(l=10, r=10, t=40, b=10))
    st.plotly_chart(fig_ch, use_container_width=True)

with c2:
    monthly_grp = (
        filtered.groupby("Month", as_index=False)[["Visitors", "Leads", "Customers", "Revenue"]]
        .sum()
        .sort_values("Month")
    )
    monthly_grp["Overall_Conv_%"] = np.where(
        monthly_grp["Visitors"] > 0, monthly_grp["Customers"] / monthly_grp["Visitors"] * 100, 0.0
    ).round(2)

    fig_trend = px.line(
        monthly_grp,
        x="Month",
        y="Overall_Conv_%",
        markers=True,
        labels={"Overall_Conv_%": "Overall Conversion Rate (%)"},
        title="Monthly Overall Conversion Rate Trend",
    )
    fig_trend.update_traces(line=dict(width=3, color="#2563EB"), marker=dict(size=9))
    fig_trend.update_layout(height=360, margin=dict(l=10, r=10, t=40, b=10))
    st.plotly_chart(fig_trend, use_container_width=True)

st.dataframe(ch_grp, use_container_width=True, hide_index=True)

# ---------------------------------------------------------
# ACTIONABLE RECOMMENDATIONS
# ---------------------------------------------------------
st.subheader("Actionable Optimization Recommendations")
recs = pd.DataFrame({
    "Focus Area": [
        "Top-of-Funnel Capture",
        "Lead Qualification Speed",
        "Channel Budget Allocation",
    ],
    "Target Bottleneck": [
        "High visitor-to-lead drop-off on broad/paid traffic",
        "Leads stalling before reaching Qualified Lead status",
        "Low-converting volume channels vs. high-return channels",
    ],
    "Recommended Action": [
        "Align ad messaging with dedicated landing pages and A/B test high-intent lead magnets.",
        "Add lead-scoring rules and automated follow-up sequences to prioritize high-intent prospects.",
        "Shift spend incrementally toward channels with stronger lead-to-customer conversion and revenue/visitor.",
    ],
})
st.dataframe(recs, use_container_width=True, hide_index=True)