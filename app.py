import streamlit as st
import pandas as pd
import google.generativeai as genai
from datetime import date

# --- 1. PAGE CONFIG & DATA LOADING ---
st.set_page_config(page_title="VMS Smart Summary", layout="centered", page_icon="🌿")

@st.cache_data
def load_data():
    try:
        # Adjust filename if necessary
        return pd.read_csv('VMS_Code_Reference_FULL_100pct.csv')
    except Exception as e:
        st.error(f"Could not load CSV: {e}")
        return pd.DataFrame()

df = load_data()

# --- 2. AI CONFIGURATION ---
# Access the secret from Streamlit Cloud Settings
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    
    # NEW: Dynamic Model Selection to avoid 404 errors
    try:
        # We try to find the best available 'flash' model assigned to your key
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        # Prefer 1.5-flash as it is most stable for free tier
        primary_model = next((m for m in available_models if 'gemini-1.5-flash' in m), None)
        
        if primary_model:
            model = genai.GenerativeModel(primary_model)
        else:
            # Fallback to whatever first model is available
            model = genai.GenerativeModel(available_models[0])
    except Exception as e:
        st.error(f"AI Setup Error: {e}")
        model = None
else:
    st.warning("⚠️ AI Suggestion is offline. Add GEMINI_API_KEY to Streamlit Secrets.")
    model = None

def get_ai_suggestion(user_notes, reference_df):
    """Feeds the CSV context to the AI to get a categorization suggestion."""
    if not model:
        return "ERROR: AI Model not initialized."

    # Condensed CSV context
    context_list = reference_df[['vms_category_name', 'vms_subcategory', 'keywords']].to_string(index=False)
    
    prompt = f"""
    You are an expert assistant for the Texas Master Naturalist program. 
    Categorize the following activity based on the provided list.
    
    OFFICIAL LIST:
    {context_list}
    
    USER NOTES: "{user_notes}"
    
    Return EXACTLY this format:
    CATEGORY: [Name]
    SUBCATEGORY: [Subname]
    REASON: [Short explanation]
    """
    
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        if "429" in str(e):
            return "ERROR: Rate limit exceeded. Please wait 30 seconds."
        return f"ERROR: {str(e)}"

# --- 3. USER INTERFACE ---
st.title("🌿 VMS Smart Summary")
st.caption("Automatically categorize your Master Naturalist hours using AI.")

if not df.empty:
    # STEP 1: AI ASSISTANCE
    with st.container(border=True):
        st.subheader("1. What did you do?")
        raw_description = st.text_area(
            "Describe your activity:",
            placeholder="e.g., I spent the morning at the river pulling invasive elephant ear plants.",
            help="The AI will match this against your CSV file."
        )
        
        if st.button("🔍 Analyze with AI"):
            if raw_description:
                with st.spinner("Analyzing rules..."):
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
        st.caption(f"**VMS Rule:** {current_row['rules']}")

    # STEP 3: LOGISTICS
    st.subheader("3. Log Details")
    c1, c2, c3 = st.columns([2, 2, 1])
    with c1:
        org = st.text_input("Organization", value="Alamo Area Master Naturalists")
    with c2:
        loc = st.text_input("Location", placeholder="e.g., Mission Espada")
    with c3:
        hrs = st.number_input("Hours", min_value=0.25, step=0.25)
    
    log_date = st.date_input("Activity Date", value=date.today())

    # --- 4. BLURB GENERATION ---
    if st.button("✨ Generate Final Blurb"):
        # Map activity types to natural verbs
        verb_map = {
            'training': "participated in training on",
            'field_research': "conducted research regarding",
            'habitat restoration': "performed habitat restoration for",
            'outreach': "provided public outreach for",
            'administration': "assisted with chapter business for",
            'invasive removal': "removed invasive species for"
        }
        
        act_type = current_row['activity_type']
        verb = verb_map.get(act_type, "completed work on")
        
        final_summary = (
            f"On {log_date.strftime('%B %d, %Y')}, I {verb} {sub_selection} "
            f"with {org} at {loc}. {raw_description} "
            f"A total of {hrs} hours were logged."
        )
        
        st.success("Summary Generated!")
        st.text_area("Copy into VMS:", final_summary, height=150)
        st.download_button("📥 Download Summary", final_summary, file_name=f"vms_{log_date}.txt")

else:
    st.error("CSV file not found. Ensure 'VMS_Code_Reference_FULL_100pct.csv' is in your GitHub folder.")
    
