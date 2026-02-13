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
        df['keyword_list'] = df['keywords'].fillna('').str.lower().str.split(',')
        return df
    return None

df = get_data()

if df is None:
    st.error("⚠️ CSV File Not Found! Please ensure 'VMS_Code_Reference_FULL_100pct.csv' is in your GitHub repository.")
    st.stop()

# --- GRAMMAR HELPER ---
def conjugate_to_ing(text):
    words = text.split()
    if not words: return text
    replacements = {
        "hosted": "hosting", "prepped": "prepping", "created": "creating",
        "pulled": "pulling", "cleared": "clearing", "led": "leading",
        "assisted": "assisting", "removed": "removing", "monitored": "monitoring",
        "attended": "attending", "presented": "presenting", "conducted": "conducting",
        "organized": "organizing", "taught": "teaching", "gave": "giving"
    }
    new_words = []
    for word in words:
        clean_word = word.lower().rstrip(',.')
        punctuation = word[len(clean_word):]
        if clean_word in replacements:
            new_words.append(replacements[clean_word] + punctuation)
        elif clean_word.endswith('ed') and len(clean_word) > 4:
            stem = clean_word[:-2]
            if stem.endswith('e'): stem = stem[:-1]
            new_words.append(stem + "ing" + punctuation)
        else:
            new_words.append(word)
    return " ".join(new_words)

# --- APP UI ---
st.title("🌳 VMS Auto-Categorizer")
st.caption("Now recognizes partners like San Antonio River Authority based on Organization/Location.")

# 1. INPUTS
notes = st.text_area(
    "1. Specific Task Details",
    placeholder="e.g., Pulled weeds and cleared trails.",
    height=100
)

col1, col2 = st.columns(2)
with col1:
    organization = st.text_input("2. Organization / Chapter", placeholder="e.g., San Antonio River Foundation")
with col2:
    location = st.text_input("3. Location", placeholder="e.g., Confluence Park")

# --- PARTNER & ACTIVITY MATCHING LOGIC ---
def auto_decide(task_text, org_text, loc_text):
    if not task_text: return "Other", "Other – AAMN"
    
    t = task_text.lower()
    o_l = (org_text + " " + loc_text).lower()
    
    # Identify Partner based on Org/Loc
    partner = "AAMN" # Default
    partner_map = {
        "san antonio river": "San Antonio River Authority",
        "sara": "San Antonio River Authority",
        "river foundation": "San Antonio River Authority",
        "mitchell lake": "Mitchell Lake Audubon Center",
        "botanical garden": "San Antonio Botanical Garden",
        "bulverde oaks": "Bulverde Oaks Nature Preserve",
        "cibolo": "Cibolo Conservation Center",
        "government canyon": "Government Canyon",
        "guadalupe river": "Guadalupe River State Park",
        "headwaters": "Headwaters-Incarnate Word",
        "witte": "Witte Museum",
        "phil hardberger": "San Antonio Parks and Recreation",
        "friedrich": "San Antonio Parks and Recreation",
        "canyon gorge": "Canyon Gorge",
        "kendall county": "Kendall County Parks Partnership",
        "kronkosky": "Kronkosky State Natural Area"
    }
    
    for key, val in partner_map.items():
        if key in o_l:
            partner = val
            break

    # Determine Base Activity
    category = "Other"
    base_activity = "Other"

    if any(word in t for word in ['board', 'committee', 'admin', 'meeting', 'reporting hours']):
        category, base_activity = "Chapter Business", "Chapter Business"
    elif any(word in t for word in ['webinar', 'lecture', 'training', 'workshop', 'tmn tuesday']):
        category = "Advanced Training"
        base_activity = "TMN Tuesday" if "tmn tuesday" in t else "Presentations"
        return category, base_activity # These don't follow the Partner format
    elif any(word in t for word in ['outreach', 'booth', 'presentation', 'public', 'students', 'tour', 'guide', 'class']):
        category, base_activity = "Public Outreach", "Public Outreach"
    elif any(word in t for word in ['invasive', 'weed', 'privet', 'chinaberry']):
        category, base_activity = "Resource Management", "Invasives"
    elif any(word in t for word in ['trail', 'maintenance', 'clearing', 'trash', 'litter', 'cleanup']):
        category = "Nature/Public Access" if "trail" in t else "Resource Management"
        base_activity = "Access Nature" if "trail" in t else "Trash Removal"
    elif any(word in t for word in ['survey', 'monitoring', 'bird count', 'inaturalist']):
        category, base_activity = "Field Research", "Field Research"
        if "inaturalist" in t: base_activity = "iNaturalist Observations"
    elif any(word in t for word in ['planting', 'restore', 'restoration']):
        category, base_activity = "Resource Management", "Habitat Restore"

    # Construct and validate subcategory name: "Activity – Partner"
    suggested_sub = f"{base_activity} – {partner}"
    
    # Check if this subcategory actually exists in the CSV
    exists = df[df['vms_subcategory'] == suggested_sub]
    if exists.empty:
        # Fallback if specific partner combo doesn't exist (e.g. Outreach - Government Canyon)
        suggested_sub = f"{base_activity} – AAMN"
        if df[df['vms_subcategory'] == suggested_sub].empty:
            # Final fallback to first match in category
            suggested_sub = df[df['vms_category_name'] == category]['vms_subcategory'].iloc[0]

    return category, suggested_sub

suggested_cat, suggested_sub = auto_decide(notes, organization, location)

# --- OVERRIDE SECTION ---
st.divider()
st.subheader("VMS Classification")
cat_list = sorted(df['vms_category_name'].unique().tolist())
cat_index = cat_list.index(suggested_cat) if suggested_cat in cat_list else 0
selected_category = st.selectbox("Confirm VMS Category", cat_list, index=cat_index)

sub_df = df[df['vms_category_name'] == selected_category]
sub_list = sorted(sub_df['vms_subcategory'].unique().tolist())
sub_index = sub_list.index(suggested_sub) if suggested_sub in sub_list else 0
selected_subcategory = st.selectbox("Confirm VMS Subcategory", sub_list, index=sub_index)

# --- NARRATIVE GENERATOR ---
def generate_narrative(cat, sub, task, org, loc):
    if not task: return ""
    clean_notes = conjugate_to_ing(task.strip().rstrip('.'))
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
    if cat == "Nature/Public Access" or "Resource Management" in cat:
        return f"I provided habitat restoration and trail maintenance service for {sub}{loc_str} with {org_str} by {clean_notes}."

    return f"I provided volunteer service for {sub} in coordination with {org_str}{loc_str} by {clean_notes}."

# --- OUTPUT ---
st.divider()
if notes:
    rules_lookup = df[(df['vms_category_name'] == selected_category) & (df['vms_subcategory'] == selected_subcategory)]
    if not rules_lookup.empty:
        rule = rules_lookup.iloc[0]['rules']
        if pd.notna(rule): st.warning(f"💡 **VMS Rule for this code:** {rule}")

    final_summary = generate_narrative(selected_category, selected_subcategory, notes, organization, location)
    st.subheader("Generated Summary")
    st.text_area("Copy/Paste into VMS:", final_summary, height=120)
else:
    st.info("Start typing your task details above to see the VMS suggestion.")
