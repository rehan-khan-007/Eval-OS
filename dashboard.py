import streamlit as st
import pandas as pd
import requests

API_URL = "https://eval-os.onrender.com"

st.set_page_config(page_title="EvalOS Dashboard", page_icon="⚖️", layout="wide")

# Sidebar Navigation
st.sidebar.title("⚖️ EvalOS")
page = st.sidebar.radio("Navigation", ["View Experiments", "Interactive Playground"])

# =================== VIEW EXPERIMENTS PAGE ===================
if page == "View Experiments":
    st.title("EvalOS Benchmark Experiments")
    st.markdown("Reproducible Evaluation Infrastructure for AI Systems")

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

    exp_options = {e['id']: e['name'] for e in experiments}
    selected_exp_id = st.sidebar.selectbox("Select an Experiment", list(exp_options.keys()), format_func=lambda x: exp_options[x])

    if selected_exp_id:
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
        
        st.sidebar.header("Run Analysis")
        run_options = {r['run_id']: f"{r['config_name']}" for r in runs}
        selected_run_id = st.sidebar.selectbox("Select a Run to Inspect", list(run_options.keys()), format_func=lambda x: run_options[x])
        
        if selected_run_id:
            st.markdown("---")
            st.subheader(f"Run Analysis: {run_options[selected_run_id]}")
            
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
                df_metrics['Display Score'] = df_metrics['Score'].apply(lambda x: f"{x*100:.1f}%" if x <= 1.0 else f"{x:.4f}")
                st.table(df_metrics[['Metric', 'Display Score']])
                
            st.markdown("### Failure Diagnosis")
            try:
                diag_data = requests.get(f"{API_URL}/api/runs/{selected_run_id}/diagnose").json()
                diag_counts = {k: len(v) for k, v in diag_data.items()}
                df_diag = pd.DataFrame(list(diag_counts.items()), columns=['Failure Type', 'Count'])
                st.dataframe(df_diag, use_container_width=True)
            except:
                st.info("Could not load failure diagnosis.")
                
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

# =================== INTERACTIVE PLAYGROUND PAGE ===================
elif page == "Interactive Playground":
    st.title("⚡ Interactive Playground (BYOK)")
    st.markdown("Run a live RAG evaluation using your own OpenRouter API key. Your key is never stored and only used for this request.")
    
    with st.form("playground_form"):
        user_api_key = st.text_input("OpenRouter API Key", type="password", help="Get a key from openrouter.ai/keys")
        user_question = st.text_area("Question", "What is GRAPE and what problem does it solve in quantum control?")
        col1, col2 = st.columns(2)
        model = col1.selectbox("Generation Model", ["openai/gpt-4o-mini", "openai/gpt-4o", "anthropic/claude-haiku-4.5", "google/gemini-3.7-flash"])
        judge_model = col2.selectbox("Judge Model", ["openai/gpt-4o-mini", "openai/gpt-4o"])
        
        submitted = st.form_submit_button("Run Live Evaluation")
        
        if submitted:
            if not user_api_key:
                st.error("Please provide an OpenRouter API key.")
            elif not user_question:
                st.error("Please provide a question.")
            else:
                with st.spinner("Running RAG pipeline and LLM Judge..."):
                    try:
                        res = requests.post(f"{API_URL}/api/playground", json={
                            "api_key": user_api_key,
                            "question": user_question,
                            "model": model,
                            "judge_model": judge_model
                        })
                        res.raise_for_status()
                        data = res.json()
                        
                        if "error" in data:
                            st.error(f"Error: {data['error']}")
                        else:
                            st.success("Evaluation Complete!")
                            
                            st.markdown("### Retrieved Context")
                            for i, ev in enumerate(data.get("retrieved_evidence", [])):
                                st.info(f"**{ev['source']}**: {ev['text'][:300]}...")
                                
                            st.markdown("### Generated Answer")
                            st.write(data.get("answer", "No answer generated."))
                            
                            st.markdown("### LLM Judge Verdict (Faithfulness)")
                            judge = data.get("judge", {})
                            st.metric("Faithfulness Score", f"{judge.get('score', 0)*100:.1f}%")
                            st.write(judge.get("explanation", ""))
                            
                            st.markdown("#### Claim Breakdown")
                            for c in judge.get("evidence_breakdown", {}).get("claims", []):
                                status = c.get("status", "unknown")
                                symbol = "✅" if status == "supported" else ("❌" if status == "contradicted" else "⚠️")
                                st.write(f"{symbol} **{c.get('claim', '')}** [{status}]")
                                
                            st.markdown("---")
                            st.caption(f"Latency: {data.get('latency_ms', 0)/1000:.2f}s | Est Cost: ${data.get('cost', 0):.6f}")
                    except requests.exceptions.HTTPError as e:
                        st.error(f"API Error: {e.response.text}")
                    except Exception as e:
                        st.error(f"Failed to connect to API: {e}")
