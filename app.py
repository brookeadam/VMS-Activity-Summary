import streamlit as st
import pandas as pd
import google.generativeai as genai
import json
import re

# --- 1. PAGE CONFIG & DATA LOADING ---
st.set_page_config(page_title="VMS Smart Summary", layout="centered", page_icon="🌿")

@st.cache_data
def load_data():
    try:
        return pd.read_csv('VMS_Code_Reference_FULL_100pct.csv')
    except Exception as e:
        st.error(f"Could not load CSV: {e}")
        return pd.DataFrame()

df = load_data()

# Initialize Session State for dropdowns if they don't exist
if 'suggested_cat' not in st.session_state:
    st.session_state.suggested_cat = df['vms_category_name'].unique()[0] if not df.empty else ""
if 'suggested_sub' not in st.session_state:
    st.session_state.suggested_sub = ""

# --- 2. AI CONFIGURATION ---
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    try:
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        primary_model = next((m for m in available_models if 'gemini-1.5-flash' in m), available_models[0])
        model = genai.GenerativeModel(primary_model)
    except Exception as e:
        st.error(f"AI Setup Error: {e}")
        model = None
else:
    st.warning("⚠️ AI Offline. Add GEMINI_API_KEY to Secrets.")
    model = None

def get_ai_suggestion(user_notes, reference_df):
    if not model: return None
    
    # Create a simplified reference for the AI
    ref_text = reference_df[['vms_category_name', 'vms_subcategory']].to_string(index=False)
    
    prompt = f"""
    You are a Texas Master Naturalist assistant. Based on these notes: "{user_notes}"
    Pick the best Category and Subcategory from this list:
    {ref_text}
    
    Return ONLY a JSON object like this:
    {{"category": "Category Name", "subcategory": "Subcategory Name", "reason": "why"}}
    """
    
    try:
        response = model.generate_content(prompt)
        # Clean the response to ensure it's just JSON
        clean_json = re.search(r'\{.*\}', response.text, re.DOTALL).group()
        return json.loads(clean_json)
    except:
        return None

# --- 3. USER INTERFACE ---
st.title("🌿 VMS Smart Summary")
st.caption("AI-powered categorization for Master Naturalist activities.")

if not df.empty:
    # STEP 1: DESCRIPTION
    with st.container(border=True):
        st.subheader("1. Describe Your Activity")
        raw_description = st.text_area(
            "What did you do?", 
            placeholder="e.g., Pulling invasive plants at the river...",
            height=100
        )
        
        if st.button("🔍 Analyze & Auto-Fill"):
            if raw_description:
                with st.spinner("AI is categorizing..."):
                    result = get_ai_suggestion(raw_description, df)
                    if result:
                        # Update Session State
                        st.session_state.suggested_cat = result['category']
                        st.session_state.suggested_sub = result['subcategory']
                        st.toast(f"AI suggests: {result['category']}", icon="🤖")
                    else:
                        st.error("AI couldn't determine a category. Please select manually.")
            else:
                st.warning("Please enter a description.")

    st.divider()

    # STEP 2: CATEGORIZATION (With Auto-Fill Logic)
    st.subheader("2. Confirm Categorization")
    
    categories = sorted(df['vms_category_name'].unique())
    
    # Category Selectbox
    if st.session_state.suggested_cat in categories:
        cat_index = categories.index(st.session_state.suggested_cat)
    else:
        cat_index = 0
        
    selected_category = st.selectbox("VMS Category", categories, index=cat_index)

    # Subcategory Selectbox (filtered by category)
    sub_df = df[df['vms_category_name'] == selected_category]
    subcategories = sorted(sub_df['vms_subcategory'].unique())
    
    # Determine default subcategory index
    if st.session_state.suggested_sub in subcategories:
        sub_index = subcategories.index(st.session_state.suggested_sub)
    else:
        sub_index = 0
        
    selected_subcategory = st.selectbox("Subcategory", subcategories, index=sub_index)

    # STEP 3: LOGISTICS
    st.subheader("3. Organization & Location")
    col1, col2 = st.columns(2)
    with col1:
        org = st.text_input("Organization", value="Alamo Area Master Naturalists")
    with col2:
        loc = st.text_input("Location", placeholder="Where did this happen?")

    # --- 4. BLURB GENERATION ---
    if st.button("✨ Generate Summary Blurb"):
        # Get the activity type for verb selection
        row = sub_df[sub_df['vms_subcategory'] == selected_subcategory].iloc[0]
        act_type = row['activity_type']
        
        verb_map = {
            'training': "participated in training on",
            'field_research': "conducted research regarding",
            'habitat restoration': "performed habitat restoration for",
            'outreach': "provided public outreach for",
            'administration': "assisted with chapter business for",
            'invasive removal': "removed invasive species for",
            'education': "provided environmental education via"
        }
        verb = verb_map.get(act_type, "completed work on")
        
        final_summary = (
            f"I {verb} {selected_subcategory} with {org} at {loc}. "
            f"Activity details: {raw_description}"
        )
        
        st.success("Summary Ready for VMS!")
        st.text_area("Copy/Paste:", final_summary, height=120)
        
