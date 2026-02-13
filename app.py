import streamlit as st
import pandas as pd
import os

# Set page config
st.set_page_config(page_title="Alamo VMS Auto-Generator", layout="centered", page_icon="🌳")

# --- ROBUST FILE LOADER ---
def find_and_load_csv(filename):
    if os.path.exists(filename):
        return pd.read_csv(filename)
    for file in os.listdir('.'):
        if file.lower() == filename.lower():
            return pd.read_csv(file)
    return None

@st.cache_data
def get_data():
    target_file = 'VMS_Code_Reference_FULL_100pct.csv'
    df = find_and_load_csv(target_file)
    if df is not None:
        # Pre-process keywords for better matching
        df['keyword_list'] = df['keywords'].fillna('').str.lower().str.split(',')
        return df
    return None

df = get_data()

if df is None:
    st.error("⚠️ CSV File Not Found! Please ensure 'VMS_Code_Reference_FULL_100pct.csv' is in your GitHub repository.")
    st.stop()

# --- GRAMMAR HELPER ---
def conjugate_to_ing(text):
    """Converts past tense verbs to gerunds (-ing) for better sentence flow."""
    words = text.split()
    if not words:
        return text
    
    replacements = {
        "hosted": "hosting",
        "prepped": "prepping",
        "created": "creating",
        "pulled": "pulling",
        "cleared": "clearing",
        "led": "leading",
        "assisted": "assisting",
        "removed": "removing",
        "monitored": "monitoring",
        "attended": "attending",
        "presented": "presenting",
        "conducted": "conducting",
        "organized": "organizing",
        "taught": "teaching",
        "gave": "giving"
    }
    
    new_words = []
    for word in words:
        # Strip punctuation for the dictionary check
        clean_word = word.lower().rstrip(',.')
        punctuation = word[len(clean_word):]
        
        if clean_word in replacements:
            new_words.append(replacements[clean_word] + punctuation)
        elif clean_word.endswith('ed') and len(clean_word) > 4:
            # Simple heuristic for most -ed verbs
            stem = clean_word[:-2]
            if stem.endswith('e'): # e.g., 'created' -> 'creat' -> 'creating'
                stem = stem[:-1]
            new_words.append(stem + "ing" + punctuation)
        else:
            new_words.append(word)
            
    return " ".join(new_words)

# --- APP UI ---
st.title("🌳 VMS Auto-Categorizer")
st.caption("Enter your details and let the app handle the VMS coding and summary grammar.")

# 1. THE THREE INPUTS
notes = st.text_area(
    "1. Specific Task Details",
    placeholder="e.g., Hosted a Spring Sowing class, prepped materials, and created the presentation.",
    height=100
)

col1, col2 = st.columns(2)
with col1:
    organization = st.text_input("2. Organization / Chapter", placeholder="e.g., San Antonio River Foundation")
with col2:
    location = st.text_input("3. Location", placeholder="e.g., Confluence Park")

# --- AUTO-DECISION LOGIC ---
def auto_decide(text):
    if not text:
        return None, None
    
    t = text.lower()
    
    # Priority 1: Chapter Business
    if any(word in t for word in ['board', 'committee', 'newsletter', 'website', 'admin', 'meeting', 'reporting hours']):
        return "Chapter Business", "Chapter Business – AAMN"
    
    # Priority 2: Advanced Training
    if any(word in t for word in ['webinar', 'lecture', 'training', 'workshop', 'conference', 'tmn tuesday']):
        if 'tmn tuesday' in t: return "Advanced Training", "TMN Tuesday"
        return "Advanced Training", "Presentations"
    
    # Priority 3: Public Outreach
    if any(word in t for word in ['outreach', 'booth', 'presentation', 'public', 'students', 'tour', 'guide', 'museum', 'witte', 'class', 'taught', 'hosted']):
        return "Public Outreach", "Public Outreach – AAMN"
    
    # Priority 4: Nature Access / Restoration
    if any(word in t for word in ['trail', 'maintenance', 'garden', 'planting', 'invasive', 'brush', 'clearing', 'park']):
        return "Nature/Public Access", "Access Nature – AAMN"
    
    # Priority 5: Field Research
    if any(word in t for word in ['survey', 'monitoring', 'bird count', 'inaturalist', 'water quality', 'coco rahs']):
        if 'inaturalist' in t: return "Field Research", "iNaturalist Observations"
        return "Field Research", "Field Research – AAMN"

    return "Other", "Other – AAMN"

suggested_cat, suggested_sub = auto_decide(notes)

# --- NARRATIVE GENERATOR ---
def generate_narrative(cat, sub, task, org, loc):
    if not task: return ""
    
    # Use the grammar helper to fix the tense
    clean_notes = conjugate_to_ing(task.strip().rstrip('.'))
    
    # Set starting case correctly
    if clean_notes and not clean_notes[:2].isupper():
        clean_notes = clean_notes[0].lower() + clean_notes[1:]

    org_str = org if org else "the AAMN chapter"
    loc_str = f" at {loc}" if loc else ""
    
    if cat == "Advanced Training":
        return f"I attended an advanced training session regarding {sub} provided by {org_str}{loc_str}. The session involved {clean_notes}."
    
    if cat == "Public Outreach":
        return f"Representing the Master Naturalist program{loc_str}, I engaged in public outreach with {org_str} by {clean_notes}."
    
    if cat == "Field Research":
        return f"I contributed to citizen science and research efforts for {sub}{loc_str} by {clean_notes}."

    if cat == "Nature/Public Access":
        return f"I provided habitat restoration and trail maintenance service for {sub}{loc_str} with {org_str} by {clean_notes}."

    return f"I provided volunteer service for {sub} in coordination with {org_str}{loc_str} by {clean_notes}."

# --- DISPLAY RESULTS ---
st.divider()

if notes:
    st.subheader("VMS Classification Results")
    res_col1, res_col2 = st.columns(2)
    res_col1.metric("Category", suggested_cat)
    res_col2.metric("Subcategory", suggested_sub)
    
    rules_lookup = df[(df['vms_category_name'] == suggested_cat) & 
                      (df['vms_subcategory'] == suggested_sub)]
    
    if not rules_lookup.empty:
        rule = rules_lookup.iloc[0]['rules']
        if pd.notna(rule):
            st.info(f"💡 **VMS Rule:** {rule}")

    final_summary = generate_narrative(suggested_cat, suggested_sub, notes, organization, location)
    
    st.subheader("Generated Summary")
    st.text_area("Copy/Paste into VMS:", final_summary, height=120)
    st.caption("Grammar check: Verbs have been automatically adjusted to gerunds (e.g., 'hosted' to 'hosting') for a smoother summary.")
else:
    st.info("Start typing your task details above to see the VMS suggestion.")
