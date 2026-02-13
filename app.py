import streamlit as st
import pandas as pd
from datetime import date

# Set page config
st.set_page_config(page_title="VMS Activity Summary Generator", layout="centered", page_icon="🌿")

# Load reference data from the attached CSV
@st.cache_data
def load_data():
    try:
        df = pd.read_csv('VMS_Code_Reference_FULL_100pct.csv')
        return df
    except FileNotFoundError:
        st.error("CSV file 'VMS_Code_Reference_FULL_100pct.csv' not found. Please ensure it is in the same directory.")
        return pd.DataFrame()

df = load_data()

st.title("🌿 VMS Activity Summary Generator")
st.caption("Automatically create a VMS-ready summary blurb using approved categories.")

if not df.empty:
    # ---- INPUT FIELDS ----

    # 1. Category Selection (from CSV)
    categories = sorted(df['vms_category_name'].unique())
    selected_category = st.selectbox("Select VMS Category", categories)

    # 2. Subcategory Selection (Filtered by Category)
    sub_df = df[df['vms_category_name'] == selected_category]
    subcategories = sorted(sub_df['vms_subcategory'].unique())
    selected_subcategory = st.selectbox("Select Specific Activity (VMS Subcategory)", subcategories)

    # Get details for the selected subcategory to use in the summary logic
    row = sub_df[sub_df['vms_subcategory'] == selected_subcategory].iloc[0]
    vms_activity_type = row['activity_type']
    vms_rules = row['rules']

    # 3. Display VMS Rules & Requirements
    if pd.notna(vms_rules) and vms_rules.strip() != "":
        with st.expander("📌 VMS Rules for this activity", expanded=True):
            st.info(vms_rules)

    # 4. Manual Context Inputs
    col1, col2 = st.columns(2)
    with col1:
        organization = st.text_input("Organization / Chapter", value="Alamo Area Master Naturalists")
        activity_date = st.date_input("Date of Activity", value=date.today())
    with col2:
        location = st.text_input("Location", placeholder="e.g., Phil Hardberger Park")
        hours = st.number_input("Hours Spent", min_value=0.25, step=0.25)

    notes = st.text_area(
        "Specific Task Details (what you did)",
        placeholder="Pulled invasive Chinaberry, cleared trails, led a tour for 10 people, etc."
    )

    # ---- SUMMARY GENERATION ----

    def generate_summary():
        # Base start
        summary_start = f"On {activity_date.strftime('%B %d, %Y')}, I "
        
        # Verb mapping based on activity_type column in CSV
        mapping = {
            'training': "participated in an advanced training focused on",
            'administration': "contributed to chapter business activities including",
            'field_research': "assisted with research and monitoring activities related to",
            'habitat restoration': "volunteered on a habitat restoration activity involving",
            'invasive removal': "assisted with invasive species removal during",
            'cleanup': "participated in a cleanup activity during",
            'maintenance': "performed maintenance tasks during",
            'construction': "assisted with construction or infrastructure work for",
            'outreach': "supported public outreach efforts through",
            'education': "provided environmental education through",
            'consultation': "provided technical guidance for",
            'other': "completed volunteer work involving"
        }
        
        verb = mapping.get(vms_activity_type, "completed work related to")
        
        # Sentence construction
        main_sentence = f"{verb} {selected_subcategory}."
        
        # Context
        details = f" This activity was conducted with {organization}"
        if location:
            details += f" at {location}"
        details += "."
        
        # Impact / Notes
        impact = ""
        if notes:
            impact = f" Key tasks included: {notes.rstrip('.')}."
            
        # Time
        time_log = f" A total of {hours} hours were logged."
        
        return summary_start + main_sentence + details + impact + time_log

    # ---- OUTPUT ----

    if st.button("✨ Generate Summary"):
        summary = generate_summary()
        
        st.subheader("Generated Summary")
        # Text area for easy copying
        st.text_area("Copy & paste into VMS:", summary, height=180)
        
        # Download option
        st.download_button(
            label="📄 Download as Text File",
            data=summary,
            file_name=f"VMS_Summary_{activity_date}.txt",
            mime="text/plain"
        )
else:
    st.warning("Please upload or provide the CSV file to enable categorization.")
