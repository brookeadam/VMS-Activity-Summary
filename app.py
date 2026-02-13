import streamlit as st
import pandas as pd
import google.generativeai as genai
from datetime import date

# --- 1. SETUP & DATA LOADING ---
st.set_page_config(page_title="Smart VMS Generator", layout="centered", page_icon="🌿")

@st.cache_data
def load_data():
    return pd.read_csv('VMS_Code_Reference_FULL_100pct.csv')

df = load_data()

# Initialize Gemini API (using Streamlit Secrets)
# You will need to add your API Key to Streamlit's settings
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel('gemini-2.0-flash')
else:
    st.warning("⚠️ AI Features disabled. Add GEMINI_API_KEY to your Streamlit Secrets to enable.")

# --- 2. THE AI BRAIN ---
def get_ai_suggestion(user_notes):
    # Prepare the list of categories for the AI to choose from
    category_context = df[['vms_category_name', 'vms_subcategory', 'keywords']].to_string()
    
    prompt = f"""
    You are a Texas Master Naturalist assistant. Based on the user's activity notes, 
    pick the BEST matching 'vms_category_name' and 'vms_subcategory' from the list below.
    
    Valid Categories and Keywords:
    {category_context}
    
    User Activity Notes: "{user_notes}"
    
    Return your answer EXACTLY in this format:
    Category: [Name]
    Subcategory: [Subname]
    Reasoning: [1 sentence why]
    """
    
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Error: {str(e)}"

# --- 3. UI LAYOUT ---
st.title("🌿 Smart VMS Activity Generator")

# Section A: AI Suggestion
with st.expander("🤖 Need help categorizing? (AI Suggestion)", expanded=True):
    user_input_raw = st.text_area("Briefly describe what you did:", placeholder="e.g., I helped count migratory birds at the park.")
    if st.button("🔍 Analyze with AI"):
        if "GEMINI_API_KEY" not in st.secrets:
            st.error("Please configure your API key first.")
        elif user_input_raw:
            with st.spinner("AI is thinking..."):
                suggestion = get_ai_suggestion(user_input_raw)
                st.markdown(f"**AI Recommendation:**\n{suggestion}")
        else:
            st.warning("Please enter some notes first.")

st.divider()

# Section B: Manual Selection (Pre-filled if AI is used)
categories = sorted(df['vms_category_name'].unique())
selected_category = st.selectbox("1. Select VMS Category", categories)

sub_df = df[df['vms_category_name'] == selected_category]
subcategories = sorted(sub_df['vms_subcategory'].unique())
selected_subcategory = st.selectbox("2. Select Subcategory", subcategories)

# Section C: Details
row = sub_df[sub_df['vms_subcategory'] == selected_subcategory].iloc[0]
st.info(f"📌 **VMS Rule:** {row['rules']}")

col1, col2 = st.columns(2)
with col1:
    org = st.text_input("Organization", value="Alamo Area Master Naturalists")
    act_date = st.date_input("Date", value=date.today())
with col2:
    loc = st.text_input("Location", placeholder="Where did this happen?")
    hrs = st.number_input("Hours", min_value=0.25, step=0.25)

# Section D: Summary Generation
if st.button("🚀 Generate Final Summary"):
    summary = f"On {act_date.strftime('%B %d, %Y')}, I worked on {selected_subcategory} with {org} at {loc}. Activities included: {user_input_raw}. Total: {hrs} hours."
    st.subheader("Copy to VMS:")
    st.code(summary, language=None)
