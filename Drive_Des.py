#Drive_Des.py

import streamlit as st
import drive_module.drive_ops as drive_ops
from drive_module.auth import load_secret_value
import datetime


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
        fields="id, name, mimeType, description, createdTime"
    ).execute()

def update_file_description(file_id, new_description):
    return drive_service.files().update(
        fileId=file_id,
        body={"description": new_description}
    ).execute()
def parse_description(descrip: str) -> dict:
    result = {}
    wild_lines = []
    for line in descrip.splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            key = key.strip().lower()
            value = value.strip()
            result[key] = value
        else:
            if line.strip():  # bỏ qua dòng trống
                wild_lines.append(line.strip())
    if wild_lines:
        result["wild"] = wild_lines
    return result



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
    f = drive_ops.list_folder_contents_recursive(link)
    names = [item["name"][:-3] for item in f if item.get("mimeType") == "text/markdown"]
    All_TAGS.extend(names)
# --- TAB 1 ---
with tab1:
    file_url = st.text_input("🔗 Nhập link file hoặc folder Google Drive:")

    if file_url:
        file_id = extract_id_from_url(file_url)
        if file_id:
            metadata = get_file_metadata(file_id)
            descrip = metadata.get('description', '')
            descrip_dict = parse_description(descrip)
            st.subheader("📂 Đối tượng đã chọn:")
            st.markdown(f"**Tên:** `{metadata['name']}`")
            st.markdown(f"🔍 **Loại:** `{metadata['mimeType']}`")
            st.markdown("📄 Mô tả hiện tại: ")
            st.code(descrip)
            old_tag = []
            if "tag" in descrip_dict:
                old_tag = [t.strip() for t in descrip_dict["tag"].split(",") if t.strip()]
                All_TAGS.extend(old_tag)
            if "date" in descrip_dict:
                default_date = datetime.datetime.strptime(descrip_dict["date"], "%d/%m/%Y").date()   
            else:
                default_date = datetime.datetime.fromisoformat(metadata['createdTime'].replace("Z", "+00:00")).date()
            sorted_all_tags = sorted(set(All_TAGS))
            with st.form("update_form"):
                date = st.date_input("📅 Ngày", value=default_date)
                selected_tags = st.multiselect("🏷️ Chọn tag", sorted_all_tags, default=set(old_tag))
                submitted = st.form_submit_button("Cập nhật mô tả")
                if "wild" not in descrip_dict:
                    descrip_dict["wild"] = [""]
                extra_descrip = st.text_area("📝 Nội dung bổ sung", "\n".join(descrip_dict["wild"]))

                if submitted:
                    date_str = date.strftime("%d/%m/%Y")
                    tag_str = ", ".join(selected_tags)
                    new_description = f"date: {date_str}\ntag: {tag_str}\n{extra_descrip}"
                    update_file_description(file_id, new_description)
                    st.success("✅ Mô tả đã được cập nhật.")
                    st.code(new_description, language="markdown")
        else:
            st.error("❌ Không thể trích xuất ID từ link.")
    else:
        st.info("🔎 Vui lòng nhập link file hoặc folder Drive.")
