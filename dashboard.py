import streamlit as st
import pandas as pd
import requests

API_URL = "https://eval-os.onrender.com"

st.set_page_config(page_title="EvalOS Dashboard", page_icon="⚖️", layout="wide")

st.title("⚖️ EvalOS Dashboard")
st.markdown("Reproducible Evaluation Infrastructure for AI Systems")

# Fetch experiments
try:
    response = requests.get(f"{API_URL}/api/experiments")
    response.raise_for_status()
    experiments = response.json()
except Exception as e:
    st.error(f"Failed to connect to EvalOS API: {e}")
    st.stop()

if not experiments:
    st.warning("No experiments found. Run a benchmark first.")
    st.stop()

# Sidebar: Experiment Selector
st.sidebar.header("Experiments")
exp_options = {e['id']: e['name'] for e in experiments}
selected_exp_id = st.sidebar.selectbox("Select an Experiment", list(exp_options.keys()), format_func=lambda x: exp_options[x])

if selected_exp_id:
    # Fetch experiment details
    exp_res = requests.get(f"{API_URL}/api/experiments/{selected_exp_id}")
    exp_data = exp_res.json()
    
    st.header(f"Experiment: {exp_data['name']}")
    st.write(exp_data['description'])
    
    runs = exp_data['runs']
    if not runs:
        st.info("No runs in this experiment yet.")
        st.stop()
        
    st.subheader("Runs in this Experiment")
    df_runs = pd.DataFrame(runs)
    st.dataframe(df_runs, use_container_width=True)
    
    # Sidebar: Run Selector
    st.sidebar.header("Run Analysis")
    run_options = {r['run_id']: f"{r['config_name']}" for r in runs}
    selected_run_id = st.sidebar.selectbox("Select a Run to Inspect", list(run_options.keys()), format_func=lambda x: run_options[x])
    
    if selected_run_id:
        st.markdown("---")
        st.subheader(f"Run Analysis: {run_options[selected_run_id]}")
        
        # Fetch run metrics
        run_data = requests.get(f"{API_URL}/api/runs/{selected_run_id}").json()
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Examples", run_data.get('total_examples', 0))
        col2.metric("Successes", run_data.get('successes', 0))
        col3.metric("Total Cost", f"${run_data.get('total_cost', 0):.4f}")
        col4.metric("Avg Latency (s)", f"{run_data.get('latency_ms', {}).get('avg', 0) / 1000:.2f}s")
        
        st.markdown("### Metrics")
        metrics = run_data.get('metrics', {})
        if metrics:
            df_metrics = pd.DataFrame(list(metrics.items()), columns=['Metric', 'Score'])
            # Convert scores to percentages where applicable
            df_metrics['Display Score'] = df_metrics['Score'].apply(lambda x: f"{x*100:.1f}%" if x <= 1.0 else f"{x:.4f}")
            st.table(df_metrics[['Metric', 'Display Score']])
            
        # Failure Diagnosis
        st.markdown("### Failure Diagnosis")
        try:
            diag_data = requests.get(f"{API_URL}/api/runs/{selected_run_id}/diagnose").json()
            diag_counts = {k: len(v) for k, v in diag_data.items()}
            df_diag = pd.DataFrame(list(diag_counts.items()), columns=['Failure Type', 'Count'])
            st.dataframe(df_diag, use_container_width=True)
        except:
            st.info("Could not load failure diagnosis.")
            
        # Slicing
        st.markdown("### Domain Slicing")
        try:
            slice_data = requests.get(f"{API_URL}/api/runs/{selected_run_id}/slice/domain").json()
            slice_rows = []
            for domain, metrics in slice_data.items():
                row = {"Domain": domain}
                row.update(metrics)
                slice_rows.append(row)
            df_slice = pd.DataFrame(slice_rows)
            st.dataframe(df_slice, use_container_width=True)
        except:
            st.info("Could not load domain slices.")
