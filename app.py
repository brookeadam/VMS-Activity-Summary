import streamlit as st
import pandas as pd
import google.generativeai as genai
from datetime import date
import time

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

# --- 2. AI CONFIGURATION ---
# Access the secret from Streamlit Cloud Settings
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    # Using 1.5-flash for the best Free Tier reliability
    model = genai.GenerativeModel('gemini-1.5-flash')
else:
    st.warning("⚠️ AI Suggestion is offline. Add GEMINI_API_KEY to Streamlit Secrets.")

def get_ai_suggestion(user_notes, reference_df):
    """Feeds the CSV context to the AI to get a categorization suggestion."""
    # We provide a condensed version of the CSV so the AI knows the options
    context_list = reference_df[['vms_category_name', 'vms_subcategory', 'keywords']].to_string(index=False)
    
    prompt = f"""
    You are an expert assistant for the Texas Master Naturalist program. 
    Your goal is to categorize a volunteer's activity based on their notes.
    
    HERE IS THE OFFICIAL LIST OF CATEGORIES AND SUBCATEGORIES:
    {context_list}
    
    USER NOTES: "{user_notes}"
    
    TASK:
    1. Find the best matching 'vms_category_name' and 'vms_subcategory'.
    2. If no exact match exists, pick the closest one or 'Other'.
    3. Return your response in this EXACT format:
    CATEGORY: [Name]
    SUBCATEGORY: [Subname]
    REASON: [Short explanation]
    """
    
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        if "429" in str(e):
            return "ERROR: Rate limit exceeded. Please wait 10 seconds and try again."
        return f"ERROR: {str(e)}"

# --- 3. USER INTERFACE ---
st.title("🌿 VMS Smart Summary")
st.caption("Categorize and generate formatted blurbs for the Volunteer Management System.")

if not df.empty:
    # STEP 1: AI ASSISTANCE
    with st.container(border=True):
        st.subheader("1. What did you do?")
        raw_description = st.text_area(
            "Describe your activity in plain English:",
            placeholder="e.g., I spent 3 hours pulling Chinaberry trees at the park and then talked to a group about native plants.",
            help="The AI will use this to suggest a category from your CSV file."
        )
        
        if st.button("🔍 Analyze with AI"):
            if raw_description:
                with st.spinner("Consulting the VMS handbook..."):
                    suggestion = get_ai_suggestion(raw_description, df)
                    st.info(suggestion)
            else:
                st.warning("Please enter a description first.")

    st.divider()

    # STEP 2: CATEGORIZATION
    st.subheader("2. Confirm Categorization")
    
    col_a, col_b = st.columns(2)
    
    with col_a:
        categories = sorted(df['vms_category_name'].unique())
        cat_selection = st.selectbox("VMS Category", categories)
    
    with col_b:
        sub_df = df[df['vms_category_name'] == cat_selection]
        sub_selection = st.selectbox("Subcategory", sorted(sub_df['vms_subcategory'].unique()))

    # Show rules for the selected item
    current_row = sub_df[sub_df['vms_subcategory'] == sub_selection].iloc[0]
    if pd.notna(current_row['rules']):
        st.caption(f"**VMS Rule for this item:** {current_row['rules']}")

    # STEP 3: LOGISTICS
    st.subheader("3. Log Details")
    c1, c2, c3 = st.columns([2, 2, 1])
    with c1:
        org = st.text_input("Organization", value="Alamo Area Master Naturalists")
    with c2:
        loc = st.text_input("Location", placeholder="Where were you?")
    with c3:
        hrs = st.number_input("Hours", min_value=0.25, step=0.25)
    
    log_date = st.date_input("Activity Date", value=date.today())

    # --- 4. BLURB GENERATION ---
    if st.button("✨ Generate Final Blurb"):
        # Map activity types to verbs
        verb_map = {
            'training': "participated in training on",
            'field_research': "conducted research regarding",
            'habitat restoration': "performed habitat restoration for",
            'outreach': "provided public outreach for",
            'administration': "assisted with chapter business for",
            'invasive removal': "removed invasive species for",
            'education': "provided environmental education via"
        }
        
        act_type = current_row['activity_type']
        verb = verb_map.get(act_type, "completed work on")
        
        final_summary = (
            f"On {log_date.strftime('%B %d, %Y')}, I {verb} {sub_selection} "
            f"with {org} at {loc}. {raw_description} "
            f"Logged {hrs} hours."
        )
        
        st.success("Summary Generated!")
        st.text_area("Copy/Paste into VMS:", final_summary, height=150)
        
        st.download_button("📥 Download .txt", final_summary, file_name="vms_log.txt")

else:
    st.error("Missing CSV file. Please upload 'VMS_Code_Reference_FULL_100pct.csv' to your GitHub repo.")
