#Drive_Des.py

import streamlit as st
import drive_module.drive_ops as drive_ops
from drive_module.auth import load_secret_value


Default_Tag_Folders = load_secret_value("app_config", "tag_folders")
# --- Setup Google Drive API ---
drive_service = drive_ops.drive_service
# --- UI ---
st.set_page_config(page_title="Drive Folder + Tag Manager", layout="wide")
st.title("📁 Google Drive Folder Tool")

All_TAGS = []

tab1, tab2 = st.tabs(["📂 Chọn thư mục hoặc file", " "])

# --- Extract ID ---
def extract_id_from_url(url):
    if "folders/" in url:
        return url.split("folders/")[1].split("?")[0]
    elif "file/d/" in url:
        return url.split("file/d/")[1].split("/")[0]
    elif "id=" in url:
        return url.split("id=")[1].split("&")[0]
    return None

# --- Metadata ---
def get_file_metadata(file_id):
    return drive_service.files().get(
        fileId=file_id,
        fields="id, name, mimeType, description"
    ).execute()

def update_file_description(file_id, new_description):
    return drive_service.files().update(
        fileId=file_id,
        body={"description": new_description}
    ).execute()


# --- Sidebar: Nguồn tag ---
st.sidebar.header("📌 Nguồn Tag (Folder)")

# Cho phép nhập nhiều link, mỗi link một dòng
tag_source_links = st.sidebar.text_area("Dán link các folder Drive (mỗi dòng 1 link)")

tag_folder_ids = []
if tag_source_links:
    for line in tag_source_links.splitlines():
        line = line.strip()
        if line:
            folder_id = extract_id_from_url(line)
            if folder_id:
                tag_folder_ids.append(folder_id)
S = st.sidebar.text_input("Secret Code: ")
Checked = S == load_secret_value("app_config", "passcode")
# Hiển thị danh sách ID đã lấy được
if tag_folder_ids:
    st.sidebar.success("✅ Đã lấy ID từ các link folder")
else:
    st.sidebar.info("🔎 Chưa có folder nào được nhập")
if Default_Tag_Folders and Checked:
    tag_folder_ids.extend(Default_Tag_Folders)
for link in set(tag_folder_ids):
    f = drive_ops.list_folder_contents(link)
    names = [item["name"][:-3] for item in f if item.get("mimeType") == "text/markdown"]
    All_TAGS.extend(names)
# --- TAB 1 ---
with tab1:
    file_url = st.text_input("🔗 Nhập link file hoặc folder Google Drive:")

    if file_url:
        file_id = extract_id_from_url(file_url)
        if file_id:
            metadata = get_file_metadata(file_id)
            descrip = metadata.get('description', '(trống)')
            st.subheader("📂 Đối tượng đã chọn:")
            st.markdown(f"**Tên:** `{metadata['name']}`")
            st.markdown(f"🔍 **Loại:** `{metadata['mimeType']}`")
            st.markdown(f"📄 **Mô tả hiện tại:** `{descrip}`")
            old_tag = []
            if "tag:" in descrip:
                for line in descrip.splitlines():
                    if line.strip().startswith("tag:"):
                        tag_str = line.replace("tag:", "").strip()
                        old_tag = [t.strip() for t in tag_str.split(",") if t.strip()]
                        break
            valid_old_tags = [t for t in old_tag if t in All_TAGS]
            sorted_all_tags = sorted(set(All_TAGS))
            with st.form("update_form"):
                date = st.date_input("📅 Ngày")
                selected_tags = st.multiselect("🏷️ Chọn tag", sorted_all_tags, default=set(valid_old_tags))
                submitted = st.form_submit_button("Cập nhật mô tả")

                if submitted:
                    date_str = date.strftime("%d/%m/%Y")
                    tag_str = ", ".join(selected_tags)
                    new_description = f"date: {date_str}\ntag: {tag_str}"
                    update_file_description(file_id, new_description)
                    st.success("✅ Mô tả đã được cập nhật.")
                    st.code(new_description, language="markdown")
        else:
            st.error("❌ Không thể trích xuất ID từ link.")
    else:
        st.info("🔎 Vui lòng nhập link file hoặc folder Drive.")
