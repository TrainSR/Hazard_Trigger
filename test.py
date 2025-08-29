#main.py

import streamlit as st
import drive_module.drive_ops as drive_ops
import yaml
import re
import random
from collections import defaultdict
import pandas as pd
import random, math

def bounce(num, max_delta=5, k=0.8):
    deltas = range(-max_delta, max_delta + 1)
    weights = [math.exp(-k * abs(d)) for d in deltas]
    delta = random.choices(deltas, weights=weights, k=1)[0]
    return max(num + delta, 0)  # đảm bảo không âm

def merge_lists(include_list, include_num):
    """
    Gộp các phần tử trùng trong include_list và nối string tương ứng trong include_num.
    
    Args:
        include_list (list[str]): danh sách string (có thể trùng).
        include_num  (list[str]): danh sách string song song với include_list.
    
    Returns:
        (list[str], list[str]): include_list đã loại trùng, include_num đã gộp thành chuỗi.
    """
    result_list = []
    result_num = {}
    
    for item, num in zip(include_list, include_num):
        if item not in result_num:
            result_list.append(item)
            result_num[item] = [num]
        else:
            result_num[item].append(num)
    
    return result_list, [", ".join(result_num[item]) for item in result_list]


def map_index_to_yaml_flat(index, yaml_data):
    flat_list = []
    yaml_keys = list(yaml_data.keys())

    for d in index:
        key, num = next(iter(d.items()))

        if key in yaml_data:
            chosen_key = key
        else:
            chosen_key = random.choice(yaml_keys) if yaml_keys else None

        if chosen_key:
            items = yaml_data[chosen_key]
            if items:
                sampled = random.sample(items, min(bounce(num), len(items)))
                flat_list.extend(sampled)

    return flat_list


def gacha_form(label, folder_id, Included, index, serie_exclude, components_change, compo_memo):
    folder_data = compo_memo[folder_id]

    yaml_data = {}
    for ite in folder_data:

        data = drive_ops.get_or_cache_data(
            key=f"yaml_{ite}_IIOO",
            loader_func=lambda: drive_ops.extract_yaml(ite),
            dependencies={"_component_id": components_change}
        )
        yaml_data.update(data)
        st.write(yaml_data)
    if not yaml_data:
        return [], []
    
    st.markdown(f"<h3 style='color:#0088ff;'>🔎 {label}</h3>", unsafe_allow_html=True)
    
    with st.expander(f"🔎 {label}", expanded=Included):

        selected_items = set()
        for key, items in yaml_data.items():
            if isinstance(items, list):
                selected_items.update(items)

        filtered = sorted(selected_items)

        st.markdown("🎯 Kết quả sau lọc:")
        if filtered:
            st.markdown(
                f"""
                <div style="max-height: 300px; overflow-y: auto; padding: 10px; border: 1px solid #ccc; border-radius: 8px;">
                    {'<br>'.join(f"- {item}" for item in filtered)}
                </div>
                """,
                unsafe_allow_html=True
            )
        else:
            st.info("Không có phần tử nào để hiển thị.")

        # Chọn chế độ
        mode_key = f"{label}_mode"
        st.markdown("\n")
        gacha_mode = st.checkbox(f"Gacha ngẫu nhiên ({label})", value=Included, key=mode_key)
        manual_choices_key = f"{label}_manual_choices"
        num_key = f"{label}_num_items"
        if gacha_mode:
            prompts = map_index_to_yaml_flat(index, yaml_data)
        else:
            prompts = st.multiselect(
                f"Chọn thủ công cho {label}:", 
                options=filtered,
                key=manual_choices_key
            )
    return filtered, prompts

def main():
    Included_Sorted = set()
    excluded_include = []
    classified = {}
    Instructions_List = []
    components_change = st.checkbox("Thay đổi Components", key="components_change")
    important_change = st.checkbox("Thay đổi Important", key="important_change")
    sorted_change = st.checkbox("Thay đổi Sorted", key="sorted_change")
    st.title("Hazard Trigger")

    folder_id = drive_ops.select_working_folder()
    if folder_id:
        contents = drive_ops.get_or_cache_data(
            key="root_folder_contents",
            loader_func=lambda: drive_ops.list_folder_contents(folder_id),
            dependencies={"folder_id": folder_id}
        )
        if contents:
            important_folders = [
                item for item in contents
                if item.get("mimeType") == "application/vnd.google-apps.folder"
                and item.get("name") == "Important"
            ]
            components_folders = [
                item for item in contents
                if item.get("mimeType") == "application/vnd.google-apps.folder"
                and item.get("name") == "Components"
            ]

            if not components_folders:
                st.error("❌ Không tìm thấy thư mục 'Components'.")
            else:
                components_folder_id = components_folders[0]["id"]

                # Bước 2: Liệt kê các file .md trong thư mục Components
                component_contents = drive_ops.get_or_cache_data(
                    key="components_folder_contents",
                    loader_func=lambda: drive_ops.list_folder_contents_recursive(components_folder_id),
                    dependencies={"components_folder_change": components_change}
                )
                component_subfolders = [
                    item for item in component_contents
                    if item.get("mimeType") == "application/vnd.google-apps.folder"
                ]

        else:
            st.warning("📭 Thư mục rỗng hoặc không đọc được nội dung.")
        if important_folders:
            important_folder_id = important_folders[0]["id"]
            sub_contents = drive_ops.get_or_cache_data(
                key=f"folder_contents_{folder_id}",
                loader_func=lambda: drive_ops.list_folder_contents(important_folder_id),
                dependencies={"folder_id": important_change}
            )

            Important_Folders = sorted(
                [{"name": item["name"], "id": item["id"]}
                    for item in sub_contents
                    if item.get("mimeType") == "application/vnd.google-apps.folder"
                ], key=lambda x: x["name"].lower())

        with st.sidebar:
            Prompt = []
            Negative = []
            Include_List = []
            Include_Num = []
            Exclude = []
            for folder in Important_Folders:
                folder_name = folder["name"]
                folder_id = folder["id"]

                st.markdown(
                    f"<h3 style='color:#00bfff;'>📚 Duyệt - {folder_name}</h3>",
                    unsafe_allow_html=True,
                )

                try:
                    folder_contents = drive_ops.get_or_cache_data(
                        key=f"folder_contents_{folder_id}",
                        loader_func=lambda: drive_ops.list_folder_contents(folder_id),
                        dependencies={"sub_folder_important": important_change}
                    )

                    md_files = sorted(
                        [
                            f for f in folder_contents
                            if f["mimeType"] != "application/vnd.google-apps.folder" and f["name"].endswith(".md")
                        ],
                        key=lambda f: f["name"]
                    )

                except Exception as e:
                    st.warning(f"Lỗi khi đọc thư mục: {e}")
                    continue

                if not md_files:
                    st.info("Không có file .md nào trong thư mục.")
                    continue

                Hazard = st.checkbox(f"Ngẫu nhiên?", value=False, key=f"key_{folder_id}")

                if Hazard:
                    selected = random.choice(md_files)
                else:
                    file_names = [f["name"].removesuffix(".md") for f in md_files]
                    selected_name = st.selectbox(
                        f"Chọn {folder_name}:", options= [""] + file_names
                    )
                    selected = next(
                        (f for f in md_files if f["name"] == selected_name + ".md"),
                        None,
                    )

                if selected and selected != "":
                    file_id = selected["id"]
                    important_file_content = drive_ops.get_or_cache_data(
                        key=f"Important_file_contents_{file_id}",
                        loader_func=lambda: drive_ops.get_file_content(file_id),
                        dependencies={"sub_folder_important": important_change}
                    )

                    yaml_data = drive_ops.extract_yaml(important_file_content)

                    if yaml_data:
                        Prompt.extend(yaml_data.get("Prompt", []))
                        Negative.extend(yaml_data.get("Negative", []))
                        Exclude.extend(yaml_data.get("Exclude", []))

                        with st.expander("🧾 Thuộc tính YAML", expanded=False):
                            for key, value in yaml_data.items():
                                st.markdown(
                                    f"<h4 style='color:#DAA520;'>🔹 <b>{key}</b></h4>",
                                    unsafe_allow_html=True,
                                )
                                if isinstance(value, list):
                                    for item in value:
                                        st.markdown(f"- {item}")
                                else:
                                    st.markdown(f"- {value}")

                    default_set_lines = drive_ops.extract_bullet_items_from_section(important_file_content, "Default_Built")
                    default_prompt = []
                    default_entries = []  # Danh sách tuple (category, value)

                    # Bước 1: Parse các dòng và lưu từng cặp (category, value)
                    for line in default_set_lines:
                        match_1 = re.match(r'-\s*(.*?):\s*(.+)', line)
                        if match_1:
                            category = match_1.group(1).strip()
                            value = match_1.group(2).strip()
                            default_entries.append((category, value))

                    # Bước 2: Hiển thị checkbox
                    with st.expander("Thành phần Built Sẵn", expanded=True):
                        for category, value in default_entries:
                            take_default = st.checkbox(f"Lấy {category}?", value=True, key=f"laplace_{file_id + category}")
                            if take_default:
                                if "|" in value:
                                    lst = [s.strip() for s in value.split("|")]
                                    value = random.choice(lst)
                                default_prompt.append(value)  # Ghép chuỗi
                                excluded_include.append(category)
                    if default_prompt != []:
                        Prompt.extend(default_prompt)
                    include_lines = drive_ops.extract_bullet_items_from_section(important_file_content, "Include")

                    include_list = []
                    include_number = []

                    for line in include_lines:
                        match = re.match(r'-\s*(?:(.*?):\s*)?\[\[(.*?)\]\]\s*\|\s*(.*)', line)
                        if match:
                            category_name = match.group(1)
                            component_name = match.group(2)
                            quantity = match.group(3)
                            include_list.append(component_name)
                            include_number.append(quantity.strip(","))
                    if include_list:
                        with st.expander("📦 Thành phần Include", expanded=False):
                            for i in range(len(include_list)):
                                include_or_not = st.checkbox(f"- {include_list[i]}: {include_number[i]}", value=include_list[i] not in excluded_include, key=f'{include_list[i]}.included')
                                if include_or_not:
                                    Include_List.append(include_list[i])
                                    Include_Num.append(include_number[i])
                    Instructions_List.extend(drive_ops.extract_bullet_items_from_section(important_file_content, "Instruction"))
        tab_labels = ["🎮 Gacha Chính", "Components", "Sorted_Components", "Prompt Sorting", "Chance"]
        tabs = st.tabs(tab_labels)


        # Bổ sung xử lý Sorted_Components
        sorted_components_folders = [
            item for item in contents
            if item.get("mimeType") == "application/vnd.google-apps.folder"
            and item.get("name") == "Sorted_Components"
        ]


        if sorted_components_folders:
            sorted_components_folder_id = sorted_components_folders[0]["id"]

            sorted_subfolders = drive_ops.get_or_cache_data(
                key=f"folder_contents_{sorted_components_folder_id}",
                loader_func=lambda: drive_ops.list_folder_contents_recursive(sorted_components_folder_id),
                dependencies={"sorted_compo_id": sorted_change}
            )
            tree = drive_ops.build_tree(sorted_subfolders)
            exists = sorted_components_folder_id in tree
            # st.write(sorted_subfolders)
            x, sorted_memo = drive_ops.collect(sorted_components_folder_id, tree, sorted_change)

            sorted_component_folders = sorted(
                [{"name": item["name"], "id": item["id"], "parents": item["parents"]}
                 for item in sorted_subfolders
                 if item.get("mimeType") == "application/vnd.google-apps.folder"],
                key=lambda x: x["name"].lower()
            )

            with tabs[2]:  # Tab Sorted_Components
                # Group folder theo parents
                grouped_folders = defaultdict(list)

                for folder in sorted_component_folders:
                    parent = folder.get("parents", [None])[0]
                    grouped_folders[parent].append(folder)
                # Hiển thị từng nhóm theo parents
                for parent, folders in grouped_folders.items():
                    mact = next((item for item in sorted_component_folders if item["id"] == parent), None)
                    if mact:
                        Name = mact["name"]
                    else: 
                        Name = "Sorted"
                    with st.expander(f"📂 {Name}", expanded=False):
                        for folder in folders:
                            folder_name = folder["name"]
                            folder_id = folder["id"]
                            Burst_Mode = folder_name in Include_List

                            st.markdown(
                                f"<h3 style='color:#00bfff;'>📦 Sorted - {folder_name}</h3>",
                                unsafe_allow_html=True,
                            )

                            try:
                                folder_contents = drive_ops.get_or_cache_data(
                                    key=f"Sorted_folder_contents_{folder_id}",
                                    loader_func=lambda: drive_ops.list_folder_contents_recursive(folder_id),
                                    dependencies={"sorted_compo_id": sorted_change}
                                )

                                md_files = sorted(
                                    [
                                        f for f in folder_contents
                                        if f["mimeType"] != "application/vnd.google-apps.folder" and f["name"].endswith(".md")
                                    ],
                                    key=lambda f: f["name"]
                                )
                            except Exception as e:
                                st.warning(f"Lỗi khi đọc thư mục: {e}")
                                continue

                            if not md_files:
                                st.info("Không có file .md nào trong thư mục.")
                                continue

                            folder_prompts = set()

                            use_random = st.checkbox(
                                "🎲 Random chọn 1 file",
                                value=Burst_Mode,
                                key=f"use_random_{folder_id}"
                            )
                            if use_random:
                                selected_file = random.choice(md_files)
                                st.info(f"🎲 Đã chọn ngẫu nhiên: **{selected_file['name'].removesuffix('.md')}**")
                            else:
                                # Tìm file trùng với Include_List (ưu tiên file đầu tiên match)
                                default_file = ""
                                for f in md_files:
                                    base_name = f["name"].removesuffix(".md")
                                    if base_name in Include_List:
                                        default_file = f
                                        break
                                # Tạo selectbox
                                selected_file = st.selectbox(
                                    f"📄 Chọn file Markdown trong {folder_name}",
                                    options=[""] + md_files,
                                    format_func=lambda f: f["name"].removesuffix(".md") if isinstance(f, dict) else "",
                                    index=([""] + md_files).index(default_file) if default_file else 0,
                                    key=f"selected_md_file_{folder_id}"
                                )


                            if selected_file:
                                file_id = selected_file["id"]
                                sorted_file_content = drive_ops.get_or_cache_data(
                                    key=f"Sorted_file_contents_{file_id}",
                                    loader_func=lambda: drive_ops.get_file_content(file_id),
                                    dependencies={"sorted_compo_id": sorted_change}
                                )


                                Included_Sorted.add(folder_name)
                                # --- YAML ---
                                yaml_data = drive_ops.extract_yaml(sorted_file_content)

                                if yaml_data:
                                    Prompt.extend(yaml_data.get("Prompt", []))
                                    Negative.extend(yaml_data.get("Negative", []))
                                    Exclude.extend(yaml_data.get("Exclude", []))

                                    with st.expander(f"🧾 YAML - {selected_file['name']}", expanded=False):
                                        for key, value in yaml_data.items():
                                            st.markdown(
                                                f"<h4 style='color:#DAA520;'>🔹 <b>{key}</b></h4>",
                                                unsafe_allow_html=True,
                                            )
                                            if isinstance(value, list):
                                                for item in value:
                                                    st.markdown(f"- {item}")
                                            else:
                                                st.markdown(f"- {value}")

                                # --- Include ---
                                include_lines = drive_ops.extract_bullet_items_from_section(sorted_file_content, "Include")

                                include_list = []
                                include_number = []

                      