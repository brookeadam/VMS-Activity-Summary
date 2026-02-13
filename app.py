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
        # Load the provided CSV
        return pd.read_csv('VMS_Code_Reference_FULL_100pct.csv')
    except Exception as e:
        st.error(f"Could not load CSV: {e}")
        return pd.DataFrame()

df = load_data()

# --- SESSION STATE INITIALIZATION ---
# We use session state to keep track of the current selection so AI can update it
if 'suggested_cat' not in st.session_state:
    st.session_state.suggested_cat = None
if 'suggested_sub' not in st.session_state:
    st.session_state.suggested_sub = None
if 'ai_reasoning' not in st.session_state:
    st.session_state.ai_reasoning = None

# --- 2. AI CONFIGURATION ---
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    try:
        # Dynamically find the best model
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
    
    # Create a reference string for the AI including keywords/rules for better matching
    ref_text = reference_df[['vms_category_name', 'vms_subcategory', 'keywords', 'rules']].to_string(index=False)
    
    prompt = f"""
    You are a Texas Master Naturalist VMS (Volunteer Management System) assistant.
    Your job is to map user activity notes to the correct Category and Subcategory.
    
    OFFICIAL REFERENCE LIST:
    {ref_text}
    
    USER NOTES: "{user_notes}"
    
    INSTRUCTIONS:
    1. Identify the 'vms_category_name' and 'vms_subcategory' that best fit the notes.
    2. Look at the 'keywords' and 'rules' in the reference to ensure accuracy.
    3. Return ONLY a valid JSON object with the following keys: "category", "subcategory", and "reasoning".
    4. The 'reasoning' should explain why this category/subcategory pair was chosen based on specific keywords or rules.
    
    FORMAT EXAMPLE:
    {{"category": "Field Research", "subcategory": "Bird Counts", "reasoning": "User mentioned monitoring hawks, which falls under 'bird counts' keywords."}}
    """
    
    try:
        response = model.generate_content(prompt)
        # Extract JSON from the response text
        match = re.search(r'\{.*\}', response.text, re.DOTALL)
        if match:
            return json.loads(match.group())
        return None
    except Exception as e:
        st.error(f"AI Processing Error: {e}")
        return None

# --- 3. UI LAYOUT ---
st.title("🌿 VMS Smart Summary")
st.caption("AI-powered categorization and summary generator for Master Naturalists.")

if not df.empty:
    # STEP 1: ACTIVITY DESCRIPTION
    with st.container(border=True):
        st.subheader("1. Describe Your Activity")
        raw_description = st.text_area(
            "What did you do? (Be specific)", 
            placeholder="e.g., Led a guided tour for 4th graders at the park and discussed water conservation.",
            height=100
        )
        
        if st.button("🔍 Analyze with AI"):
            if raw_description:
                with st.spinner("Analyzing against VMS rules..."):
                    result = get_ai_suggestion(raw_description, df)
                    if result:
                        # Update session state with AI results
                        st.session_state.suggested_cat = result.get('category')
                        st.session_state.suggested_sub = result.get('subcategory')
                        st.session_state.ai_reasoning = result.get('reasoning')
                    else:
                        st.error("AI couldn't find a definitive match. Please select manually.")
            else:
                st.warning("Please describe your activity first.")

    # Display AI Reasoning if available
    if st.session_state.ai_reasoning:
        with st.expander("🤖 Why did the AI choose this?", expanded=True):
            st.info(st.session_state.ai_reasoning)

    st.divider()

    # STEP 2: CATEGORIZATION
    st.subheader("2. Verify Categorization")
    
    # Category Selectbox logic
    categories = sorted(df['vms_category_name'].unique())
    current_cat_idx = 0
    if st.session_state.suggested_cat in categories:
        current_cat_idx = categories.index(st.session_state.suggested_cat)
    
    selected_category = st.selectbox(
        "VMS Category", 
        categories, 
        index=current_cat_idx,
        help="The AI suggested this category. You can override it if needed."
    )

    # Subcategory Selectbox logic (Filtered by category)
    sub_df = df[df['vms_category_name'] == selected_category]
    subcategories = sorted(sub_df['vms_subcategory'].unique())
    
    current_sub_idx = 0
    if st.session_state.suggested_sub in subcategories:
        current_sub_idx = subcategories.index(st.session_state.suggested_sub)
        
    selected_subcategory = st.selectbox(
        "VMS Subcategory", 
        subcategories, 
        index=current_sub_idx,
        help="The AI suggested this subcategory. You can override it if needed."
    )

    # Display Rules/Notes for the final selection
    current_row = sub_df[sub_df['vms_subcategory'] == selected_subcategory].iloc[0]
    with st.expander("📋 Official Rules for this Selection"):
        st.write(f"**Rules:** {current_row['rules']}")
        if pd.notna(current_row['notes']):
            st.write(f"**Notes:** {current_row['notes']}")

    st.divider()

    # STEP 3: ORGANIZATION & LOCATION
    st.subheader("3. Project Logistics")
    col1, col2 = st.columns(2)
    with col1:
        org = st.text_input("Organization / Chapter", value="Alamo Area Master Naturalists")
    with col2:
        loc = st.text_input("Location", placeholder="Where did this happen?")

    # --- 4. BLURB GENERATION ---
    if st.button("✨ Generate Final Summary"):
        # Map activity types to descriptive verbs
        verb_map = {
            'training': "participated in training on",
            'field_research': "conducted research regarding",
            'habitat restoration': "performed habitat restoration for",
            'outreach': "provided public outreach for",
            'administration': "assisted with chapter business for",
            'invasive removal': "removed invasive species for",
            'education': "provided environmental education via",
            'maintenance': "assisted with maintenance for",
            'cleanup': "participated in a cleanup for",
            'consultation': "provided technical consultation for"
        }
        
        act_type = current_row['activity_type']
        verb = verb_map.get(act_type, "completed work on")
        
        final_summary = (
            f"I {verb} {selected_subcategory} with {org} at {loc}. "
            f"Detailed activities: {raw_description}"
        )
        
        st.subheader("Your VMS Ready Summary:")
        st.success("Summary generated successfully!")
        st.text_area("Copy and paste this:", final_summary, height=150)
        
        st.download_button(
            "📥 Download .txt File", 
            final_summary, 
            file_name="VMS_Summary.txt",
            mime="text/plain"
        )

else:
    st.error("Missing Data: Please ensure 'VMS_Code_Reference_FULL_100pct.csv' is in your GitHub folder.")
