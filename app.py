import streamlit as st
import pandas as pd
import os

# Set page config
st.set_page_config(page_title="Alamo VMS Helper", layout="centered", page_icon="🌳")

# --- ROBUST FILE LOADER ---
def find_and_load_csv(filename):
    # 1. Try direct match
    if os.path.exists(filename):
        return pd.read_csv(filename)
    
    # 2. Search for the file (case-insensitive) in the current directory
    for file in os.listdir('.'):
        if file.lower() == filename.lower():
            return pd.read_csv(file)
            
    return None

@st.cache_data
def get_data():
    target_file = 'VMS_Code_Reference_FULL_100pct.csv'
    df = find_and_load_csv(target_file)
    if df is not None:
        df['keyword_list'] = df['keywords'].fillna('').str.lower().str.split(',')
        return df
    return None

df = get_data()

# --- ERROR HANDLING UI ---
if df is None:
    st.error("⚠️ CSV File Not Found!")
    st.info(f"The app is looking for: `VMS_Code_Reference_FULL_100pct.csv`")
    
    with st.expander("Troubleshooting: What files does GitHub see?"):
        st.write("The following files were found in your repository:")
        st.write(os.listdir('.'))
        st.write("1. Ensure the filename matches exactly (including .csv).")
        st.write("2. Ensure the file is in the root folder, not inside a subfolder like 'data/'.")
    st.stop()

# --- APP LOGIC ---
st.title("🌳 Alamo VMS Decision Assistant")
st.caption("Categorization based on the AAMN Decision Tree logic.")

# 1. INPUT DESCRIPTION
notes = st.text_area(
    "Specific Task Details (What did you do?)",
    placeholder="e.g., I led a guided nature hike for 15 middle school students at the park.",
    height=100
)

# 2. DECISION TREE LOGIC
def predict_category(text):
    t = text.lower()
    if any(word in t for word in ['board', 'committee', 'newsletter', 'website', 'admin', 'meeting']):
        return "Chapter Business", "Chapter Business – AAMN"
    if any(word in t for word in ['webinar', 'lecture', 'training', 'workshop', 'conference']):
        if 'tmn tuesday' in t: return "Advanced Training", "TMN Tuesday"
        return "Advanced Training", "Presentations"
    if any(word in t for word in ['outreach', 'booth', 'presentation', 'public', 'students', 'tour', 'guide']):
        return "Public Outreach", "Public Outreach – AAMN"
    if any(word in t for word in ['trail', 'maintenance', 'garden', 'planting', 'invasive']):
        return "Nature/Public Access", "Access Nature – AAMN"
    if any(word in t for word in ['survey', 'monitoring', 'bird count', 'inaturalist']):
        return "Field Research", "Field Research – AAMN"
    return None, None

suggested_cat, suggested_sub = predict_category(notes)

# 3. DYNAMIC DROPDOWNS
st.divider()
col1, col2 = st.columns(2)

with col1:
    categories = sorted(df['vms_category_name'].unique())
    cat_idx = categories.index(suggested_cat) if suggested_cat in categories else 0
    selected_category = st.selectbox("VMS Category", categories, index=cat_idx)

with col2:
    sub_df = df[df['vms_category_name'] == selected_category].reset_index()
    sub_list = sub_df['vms_subcategory'].tolist()
    sub_idx = sub_list.index(suggested_sub) if suggested_sub in sub_list else 0
    selected_subcategory = st.selectbox("VMS Subcategory", sub_list, index=sub_idx)

current_row = sub_df[sub_df['vms_subcategory'] == selected_subcategory].iloc[0]

# 4. CONTEXT
organization = st.text_input("Organization / Chapter", placeholder="e.g., Alamo Area Master Naturalist Chapter")
location = st.text_input("Location", placeholder="e.g., Phil Hardberger Park")

# 5. NARRATIVE GENERATOR
def generate_narrative():
    if not notes: return ""
    clean_notes = notes.strip().rstrip('.')
    if clean_notes and not clean_notes[:3].isupper():
        clean_notes = clean_notes[0].lower() + clean_notes[1:]

    org = organization if organization else "the AAMN chapter"
    loc = f" at {location}" if location else ""
    
    if selected_category == "Advanced Training":
        return f"I attended an advanced training session regarding {selected_subcategory} provided by {org}{loc}. The focus was {clean_notes}."
    if selected_category == "Public Outreach":
        return f"Representing the Master Naturalist program {loc}, I engaged in public outreach with {org} by {clean_notes}."
    if selected_category == "Field Research":
        return f"I contributed to citizen science and research efforts for {selected_subcategory} {loc}. My activities involved {clean_notes}."
    return f"I provided volunteer service for {selected_subcategory} in coordination with {org}{loc}. My specific tasks included {clean_notes}."

if st.button("✨ Generate VMS Summary"):
    summary = generate_narrative()
    st.subheader("VMS Ready Summary")
    st.text_area("Copy/Paste into VMS:", summary, height=120)
    
    if pd.notna(current_row['rules']):
        st.info(f"💡 **VMS Rule:** {current_row['rules']}")
