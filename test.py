#main.py

import streamlit as st
import drive_module.drive_ops as drive_ops
import re
from collections import defaultdict
import pandas as pd
import random, math

def bounce(num, max_delta=5, k=2.0):
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

    yaml_data = drive_ops.extract_yamls(folder_data)
    if not yaml_data:
        return [], []
    
    st.markdown(f"<h3 style='color:#0088ff;'>🔎 {label}</h3>", unsafe_allow_html=True)
    
    with st.expander(f"🔎 {label}", expanded=Included):

        selected_items = set()
        for key, items in yaml_data.items():
            if isinstance(items, list):
                selected_items.update(str(x) for x in items)

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
        mode_key = f"{label}{folder_id}_mode"
        st.markdown("\n")
        gacha_mode = st.checkbox(f"Gacha ngẫu nhiên ({label})", value=Included, key=mode_key)
        manual_choices_key = f"{label}{folder_id}_manual_choices"
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
    classified = {}
    Instructions_List = []
    call_list = {}
    Prompt = []
    Negative = []
    Include_List = []
    Include_Num = []
    Exclude = []
    Called = []
    Random_List = {}
    Navigate_Exlucde = []
    Navigate_Exclusive = []
    Prior_Level = []
    Prior_Level_Default = []
    Prior_Cate_List = []
    with st.sidebar.expander("Change"):
        components_change = st.checkbox("Thay đổi Components", key="components_change")
        important_change = st.checkbox("Thay đổi Important", key="important_change")
        sorted_change = st.checkbox("Thay đổi Sorted", key="sorted_change")
    st.title("Hazard Trigger")

    folder_id = drive_ops.select_working_folder()
    if folder_id:
        contents = drive_ops.get_or_cache_data(
            key="root_folder_contents",
            loader_func=lambda: drive_ops.list_folder_contents(folder_id),
        )
        if contents:
            navigate_folder = [
                item for item in contents
                if item.get("mimeType") == "application/vnd.google-apps.folder"
                and item.get("name") == "1. Navigate"
            ]
            important_folders = [
                item for item in contents
                if item.get("mimeType") == "application/vnd.google-apps.folder"
                and item.get("name") == "2. Important"
            ]
            components_folders = [
                item for item in contents
                if item.get("mimeType") == "application/vnd.google-apps.folder"
                and item.get("name") == "4. Components"
            ]

            if navigate_folder: 
                st.sidebar.markdown(
                    '<h1 style="color:golden; -webkit-text-stroke:1px blue;">Navigation</h1>',
                    unsafe_allow_html=True
                )
                navigate_folder_id = navigate_folder[0]["id"]
                navigate_contents = drive_ops.get_or_cache_data(
                    key=f"folder_contents_{navigate_folder_id}",
                    loader_func=lambda: drive_ops.list_folder_contents_recursive(navigate_folder_id),
                    dependencies={"folder_id": important_change}
                )
                navigate_tree = drive_ops.build_tree(navigate_contents)
                x, navigate_memo, y, advanced_map_memo = drive_ops.collect(navigate_folder_id, navigate_tree, important_change)
                sorted_navigate_folders = sorted(
                    [{"name": item["name"], "id": item["id"], "parents": item["parents"]}
                    for item in navigate_contents
                    if item.get("mimeType") == "application/vnd.google-apps.folder"],
                    key=lambda x: x["name"].lower()
                )
                grouped_Navigate_folders = defaultdict(list)
                for folder in sorted_navigate_folders:
                    parent = folder.get("parents", [None])[0]
                    mact = next((item for item in sorted_navigate_folders if item["id"] == parent), None)
                    if mact:
                        Name = mact["name"]
                    else: 
                        Name = "Navigate"
                    grouped_Navigate_folders[Name].append(folder)
                # Hiển thị từng nhóm theo parents
                for parent, folders in grouped_Navigate_folders.items():
                    with st.sidebar.expander(f"📂 {parent}", expanded=False):
                        for folder in folders:
                            folder_name = folder["name"]
                            folder_id = folder["id"]

                            st.markdown(
                                f"<h3 style='color:#00bfff;'>Navigate - {folder_name}</h3>",
                                unsafe_allow_html=True,
                            )

                            try:
                                navigate_subfolder_content = advanced_map_memo[folder_id]

                                # Lấy cả 3 phần
                                md_files_list = [s.split('|') for s in navigate_subfolder_content]

                                # Đặt key tương ứng
                                keys = ["id", "modifiedTime", "name"]

                                # Chuyển thành dict
                                md_file = [dict(zip(keys, item)) for item in md_files_list]

                            except Exception as e:
                                st.warning(f"Lỗi khi đọc thư mục: {e}")
                                continue

                            if not md_file:
                                st.info("Không có file .md nào trong thư mục.")
                                continue
                            use_random = st.checkbox(
                                "🎲 Random chọn 1 file",
                                value=False,
                                key=f"use_random_{folder_id}"
                            )
                            if use_random:
                                selected_file = random.choice(md_file)
                                st.info(f"🎲 Đã chọn ngẫu nhiên: **{selected_file['name'].removesuffix('.md')}**")
                            else:
                                # Tìm file trùng với Include_List (ưu tiên file đầu tiên match)
                                default_file = ""
                                # Tạo selectbox
                                selected_file = st.selectbox(
                                    f"📄 Chọn file Markdown trong {folder_name}",
                                    options=[""] + md_file,
                                    format_func=lambda f: f["name"].removesuffix(".md") if isinstance(f, dict) else "",
                                    index=([""] + md_file).index(default_file) if default_file else 0,
                                    key=f"selected_md_file_{folder_id}"
                                )


                            if selected_file:
                                file_id = selected_file["id"]
                                navigate_file_content = drive_ops.get_or_cache_data(
                                    key=f"Sorted_file_contents_{file_id}",
                                    loader_func=lambda: drive_ops.get_file_content(file_id),
                                    dependencies={"sorted_compo_id": selected_file["modifiedTime"]}
                                )
                                # --- YAML ---
                                yaml_data = drive_ops.extract_yaml(navigate_file_content)
                                if yaml_data:
                                    Prompt.extend(yaml_data.get("Prompt", []))
                                    Negative.extend(yaml_data.get("Negative", []))

                                call_lines = drive_ops.extract_bullet_items_from_section(navigate_file_content, "Call")
                                for line in call_lines:
                                    match = re.match(r'-\s*(?:(.*?):\s*)?\[\[(.*?)\]\](?:\s*\|\s*(.+))?', line)
                                    if match:
                                        called_important = match.group(2)
                                        raw_prior = match.group(3)
                                        call_list[called_important] = raw_prior
                                if call_list:
                                    st.code("\n".join(call_list))


            if not components_folders:
                st.error("❌ Không tìm thấy thư mục 'Components'.")
            else:
                components_folder_id = components_folders[0]["id"]

                # Bước 2: Liệt kê các content trong thư mục Components
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

        with st.sidebar.expander("Important"):
            for folder in Important_Folders:
                folder_name = folder["name"]
                folder_id = folder["id"]
                default_index = 0
                Called_Folder = folder_name in tuple(call_list.keys())
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
                Hazard = st.checkbox(f"Ngẫu nhiên?", value=Called_Folder, key=f"key_{folder_id}")
                if Hazard:
                    selected = random.choice(md_files)
                    Random_List[folder_name] = "Important"  
                else:
                    names = [f["name"].removesuffix(".md") for f in md_files]
                    default_value = next((n for n in names if n in call_list), "")

                    options = [""] + names
                    default_index = options.index(default_value) if default_value in options else 0
                    selected_name = st.selectbox(
                        f"Chọn {folder_name}:", 
                        options=options, 
                        index=default_index
                    )
                    selected = next(
                        (f for f in md_files if f["name"] == selected_name + ".md"),
                        None,
                    )
                    

                if selected and selected != "":
                    if Hazard: 
                        Called.append(folder_name)
                    else: 
                        Called.append(selected["name"].removesuffix(".md"))
                    navigate_takes = None
                    if Called_Folder: 
                        navigate_takes = call_list[folder_name]
                        del call_list[folder_name] 
                    elif default_index:
                        try:  
                            navigate_takes = call_list[selected["name"].removesuffix(".md")]
                            del call_list[default_value]
                        except: 
                            pass
                    if navigate_takes: 
                        navigate_takes = navigate_takes.strip()
                        if navigate_takes[0] == "[":
                            Navigate_Exlucde = navigate_takes.strip("[]").split(",")
                        elif navigate_takes[0] == "(":
                            Navigate_Exclusive = navigate_takes.strip("()").split(",")
                    else: 
                        Navigate_Exlucde = []
                    file_id = selected["id"]
                    important_file_content = drive_ops.get_or_cache_data(
                        key=f"Important_file_contents_{file_id}",
                        loader_func=lambda: drive_ops.get_file_content(file_id),
                        dependencies={"sub_folder_important": selected["modifiedTime"]}
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
                        match_1 = re.match(r'-\s*(.*?):\s*([^|]+)(?:\s*\|\s*(.+))?', line)
                        if match_1:
                            category = match_1.group(1).strip()
                            value = match_1.group(2).strip()
                            Prior_Level_Default = (match_1.group(3))
                            if Prior_Level_Default: 
                                Prior_Level_Default = Prior_Level_Default.strip("[]")
                            Prior_Cate_List.append(("Default", category, str(Prior_Level_Default)))
                            default_entries.append((category, value, Prior_Level_Default))

                    # Bước 2: Hiển thị checkbox
                    with st.expander("Thành phần Built Sẵn", expanded=True):
                        for category, value, navi_def in default_entries:
                            if Navigate_Exclusive:
                                Taking_Navi = navi_def in Navigate_Exclusive
                            elif Navigate_Exlucde: 
                                Taking_Navi = navi_def not in Navigate_Exlucde
                            else: 
                                Taking_Navi = True
                            take_default = st.checkbox(f"Lấy {category}?", value=Taking_Navi, key=f"laplace_{file_id}_{category}_{navi_def}")
                            if take_default:
                                default_prompt.append(value)  # Ghép chuỗi
                                
                    if default_prompt != []:
                        Prompt.extend(default_prompt)
                    include_lines = drive_ops.extract_bullet_items_from_section(important_file_content, "Include")

                    include_list = []
                    include_number = []

                    for line in include_lines:
                        match = re.match(r'-\s*(?:(.*?):\s*)?\[\[(.*?)\]\]\s*\|\s*(.*)', line)
                        if match:
                            Prior_Level = match.group(1)
                            component_name = match.group(2)
                            quantity = match.group(3)
                            Prior_Cate_List.append(("Include", component_name, str(Prior_Level)))
                            include_list.append(component_name)
                            include_number.append(quantity.strip(","))
                    if include_list:
                        with st.expander("📦 Thành phần Include", expanded=False):
                            for i in range(len(include_list)):
                                if Navigate_Exclusive:
                                    Taking_Navi = Prior_Level[i] in Navigate_Exclusive
                                elif Navigate_Exlucde: 
                                    Taking_Navi = Prior_Level[i] not in Navigate_Exlucde
                                else: 
                                    Taking_Navi = True
                                include_or_not = st.checkbox(f"- {include_list[i]}: {include_number[i]}", value=Taking_Navi, key=f'{include_list[i]}.included')
                                if include_or_not:
                                    Include_List.append(include_list[i])
                                    Include_Num.append(include_number[i])
                    Instructions_List.extend(drive_ops.extract_bullet_items_from_section(important_file_content, "Instruction"))
                    Navigate_Exlucde = []
                    Navigate_Exclusive = []
                    Prior_Level = []
                    Prior_Level_Default = []
        tab_labels = ["🎮 Gacha Chính", "Components", "Sorted_Components", "Prompt Sorting", "Chance"]
        tabs = st.tabs(tab_labels)


        # Bổ sung xử lý Sorted_Components
        sorted_components_folders = [
            item for item in contents
            if item.get("mimeType") == "application/vnd.google-apps.folder"
            and item.get("name") == "3. Sorted_Components"
        ]


        if sorted_components_folders:
            sorted_components_folder_id = sorted_components_folders[0]["id"]

            sorted_subfolders = drive_ops.get_or_cache_data(
                key=f"folder_contents_{sorted_components_folder_id}",
                loader_func=lambda: drive_ops.list_folder_contents_recursive(sorted_components_folder_id),
                dependencies={"sorted_compo_id": sorted_change}
            )
            tree = drive_ops.build_tree(sorted_subfolders)
            x, sorted_memo, y, advanced_map_sorted = drive_ops.collect(sorted_components_folder_id, tree, sorted_change)
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
                    mact = next((item for item in sorted_component_folders if item["id"] == parent), None)
                    if mact:
                        Name = mact["name"]
                    else: 
                        Name = "1. Sorted"
                    grouped_folders[Name].append(folder)
                # Hiển thị từng nhóm theo parents
                for parent, folders in grouped_folders.items():
                    with st.expander(f"📂 {parent}", expanded=False):
                        for folder in folders:
                            folder_name = folder["name"]
                            folder_id = folder["id"]
                            Burst_Mode = (folder_name in Include_List) or (folder_name in tuple(call_list.keys()))
                            st.markdown(
                                f"<h3 style='color:#00bfff;'>📦 Sorted - {folder_name}</h3>",
                                unsafe_allow_html=True,
                            )

                            try:
                                folder_content = advanced_map_sorted[folder_id]

                                # Lấy cả 3 phần
                                md_files_list = [s.split('|') for s in folder_content]

                                # Đặt key tương ứng
                                keys = ["id", "modifiedTime", "name"]

                                # Chuyển thành dict
                                md_files = [dict(zip(keys, item)) for item in md_files_list]

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
                                Random_List[folder_name] = "Sorted Component"
                            else:
                                # Tìm file trùng với Include_List (ưu tiên file đầu tiên match)
                                default_file = ""
                                for f in md_files:
                                    base_name = f["name"].removesuffix(".md")
                                    if (base_name in Include_List) or (base_name in tuple(call_list.keys())):
                                        default_file = f
                                        if base_name in tuple(call_list.keys()): 
                                            del call_list[base_name]
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
                                    dependencies={"sorted_compo_id": selected_file["modifiedTime"]}
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

                                for line in include_lines:
                                    match = re.match(r'-\s*(?:(.*?):\s*)?\[\[(.*?)\]\]\s*\|\s*(.*)', line)
                                    if match:
                                        category_name = match.group(1)
                                        component_name = match.group(2)
                                        quantity = match.group(3)

                                        include_list.append(component_name)
                                        include_number.append(quantity)

                                if include_list:
                                    with st.expander(f"📦 Include - {selected_file['name']}", expanded=False):
                                        for i in range(len(include_list)):
                                            st.markdown(
                                                f"- <span style='color:#0073ff'><b>{include_list[i]}</b></span>: {include_number[i]}",
                                                unsafe_allow_html=True
                                            )
                                            Include_List.append(include_list[i])
                                            Include_Num.append(include_number[i])

        all_gacha_prompts = []
        serie_exclude = Exclude

        with tabs[1]:
            serie_include, include_numbering = merge_lists(Include_List, Include_Num)
            setof_serie_include = set(serie_include)
            tree_compo = drive_ops.build_tree(component_contents)
            x, compo_memo, y, compo_map_advanced = drive_ops.collect(components_folder_id, tree_compo, components_change)
            # Render theo nhóm
            # Nhóm subfolders theo parents
            grouped = {}
            for item in component_subfolders:
                parent = item.get("parents", [None])[0]  # fallback nếu không có parents
                mact_compo = next((item for item in component_subfolders if item["id"] == parent), None)
                if mact_compo:
                    Name_compo = mact_compo["name"]
                else: 
                    Name_compo = "1. Components"
                grouped.setdefault(Name_compo, []).append(item)

            for parent, items in sorted(grouped.items()):
                with st.expander(f"📂 {parent}", expanded=False):
                    for item in items:
                        Included = False
                        index = ({None: 1},)
                        label = item["name"]
                        if label in serie_include:
                            idx = serie_include.index(label)
                            raws = include_numbering.pop(idx)
                            serie_include.pop(idx)

                            # Tách theo dấu phẩy
                            parts = [part.strip() for part in raws.split(",")]

                            # Tạo tuple chứa nhiều dict
                            index = tuple(
                                ({key.strip(): int(val.strip())} if ":" in raw else {None: int(raw.strip())})
                                for raw in parts
                                for key, val in ([raw.split(":")] if ":" in raw else [(None, raw)])
                            )
                            Included = True

                        # Gọi gacha_form
                        filtered, gacha_prompts = gacha_form(label, item["id"], Included, index, serie_exclude, components_change, compo_memo)

                        all_gacha_prompts.extend(gacha_prompts)

                        # flat = [s.strip() for f in filtered for s in f.split(",")]
                        # classified[label] = set(flat)



        with tabs[3]:
            # merged = classified
            # reverse_classified = {}
            # for key, container in merged.items():
            #     for item in container:
            #         reverse_classified[item] = key
            user_prompt = st.text_input("Prompt: ", value="", key="classsing_prompting")
            stripped_prompt_to_classify = [s.strip() for s in user_prompt.split(",") if s.strip()]
            # Tạo sorted_dict rỗng
            unique_lst = list(dict.fromkeys(stripped_prompt_to_classify))
            st.code(", ".join(map(str, unique_lst)))
            # sorted_dict = {}

            # # Đối chiếu và phân loại
            # for elem in stripped_prompt_to_classify:
            #     key = reverse_classified.get(elem, "_Wild")
            #     if key not in sorted_dict:
            #         sorted_dict[key] = []
            #     sorted_dict[key].append(elem)
            # with st.expander("Sorted", expanded=False):
            #     for key in sorted(sorted_dict.keys()):
            #         # Header có màu (dùng markdown)
            #         st.markdown(
            #             f"<h4 style='color:#7300ff; margin-top:0'>{key}</h4>",
            #             unsafe_allow_html=True
            #         )
            #         items_html = "<br>".join(f"- {item}" for item in sorted(sorted_dict[key]))
            #         st.markdown(
            #             f"""
            #             <div style="max-height: 200px; overflow-y: auto; 
            #                         padding: 10px; border: 1px solid #ccc; border-radius: 8px;">
            #                 {items_html}
            #             </div>
            #             """,
            #             unsafe_allow_html=True
            #         )
            Prior_Cate_List = sorted(Prior_Cate_List, key=lambda x: x[1])
            dfOP = pd.DataFrame(Prior_Cate_List, columns=["Col", "SortKey", "Row"])

            pivot = dfOP.pivot_table(
                index="Row",
                columns="Col",
                values="SortKey",
                aggfunc=lambda x: ", ".join(sorted(set(x)))  # gộp thành chuỗi, bỏ trùng
            )
            st.table(pivot)
        # Tab Gacha Chính
        with tabs[0]:
            Init_Prompt = st.text_input("Prompt Gốc: ", value="", key="input_init_intro")
            Lora_Prompt = st.text_input(
                "Prompt Lora: ",
                value="sidelighting, shade, best quality",
                key="Lora_outa_outro"
            )
            st.subheader("✨ Quay Gacha Tất Cả")

            if st.button("🎲 Quay!", key="quay_gacha"):

                # Xử lý prompt và negative
                serie_prompt = Prompt
                serie_negative = Negative
                cleaned = [item.strip().strip(",") for item in all_gacha_prompts]

                # Ghép prompt của series (nếu có) và Default_Prompt
                all_prompts = []
                if Init_Prompt != "":
                    all_prompts.append(Init_Prompt)
                if serie_prompt:
                    all_prompts.extend([item.strip().strip(",") for item in serie_prompt])
                all_prompts.extend(cleaned)
                all_prompts.append(Lora_Prompt)
                seen = set()
                unique_prompts = [p for p in all_prompts if not (p in seen or seen.add(p))]
                joined = ", ".join(unique_prompts)
                st.subheader("📋 Prompt dạng chuỗi copy được:")
                st.code(joined, language="text")
                st.code(", ".join(cleaned))

                # In Negative riêng nếu có
                try:
                    cleaned_neg = serie_negative[0].strip().strip(",")
                    st.subheader("🚫 Negative Prompt:")
                    st.code(cleaned_neg, language="text")
                except:
                    pass
        filtered = [
            (s, n) for s, n in zip(serie_include, include_numbering)
            if s not in Included_Sorted and n != "0"
        ]

        if filtered:
            sorted_filtered = sorted(filtered, key=lambda x: x[0])
            serie_include, include_numbering = map(list, zip(*sorted_filtered))
        else:
            serie_include, include_numbering = [], []
        serie_include.extend(list(call_list.keys()))
        include_numbering.extend(list(call_list.keys()))

        if serie_include:  # chỉ hiện khi còn phần tử
            df = pd.DataFrame({
                "Include": serie_include,
                "Num": include_numbering
            })
            with tabs[0]:
                st.markdown(
                    "<h5 style='color: goldenrod;'>⚠️ Các Include sau vẫn còn bỏ ngỏ:</h5>",
                    unsafe_allow_html=True
                )
                st.table(df)
        if Random_List:
            sorted_items = sorted(Random_List.items(), key=lambda x: (x[1], x[0]))
            sorted_dict = dict(sorted_items)
            dfr = pd.DataFrame({
                "From": list(sorted_dict.values()),
                "Name": list(sorted_dict.keys())
            })
            with tabs[0]:
                st.markdown(
                    "<h5 style='color: goldenrod;'>🔀 Các thành phần Random:</h5>",
                    unsafe_allow_html=True
                )
                st.table(dfr)
                    
        with tabs[4]:
            nums = list(map(float, st.text_input("Các lần: ").split()))
            result = 1.0
            for i, n in enumerate(nums, start=1):
                result *= (1 - n/10)
                Tk = 1 - result
            if nums: 
                success = random.random() <= Tk
                st.markdown(
                    f"""
                    <div style="font-size:20px; font-weight:bold;">
                        Rate = <span style="color:skyblue;">{Tk * 100:.2f}%</span> 
                        --> <span style="color:{'limegreen' if success else 'crimson'};">
                            {'✅ Success!' if success else '❌ Pfft- Lucky Next Time'}
                        </span>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

            if Instructions_List:
                st.markdown("## 📋 Hướng dẫn:")

                for i, instr in enumerate(Instructions_List, 1):
                    st.markdown(f"""
                    <div style="
                        border:2px solid #4a90e2;
                        border-radius:10px;
                        padding:10px;
                        margin-bottom:8px;
                        background-color:#1e1e1e;
                        color:#ffffff;
                    ">
                        <b>🔹 Note {i}:</b> {instr}
                    </div>
                    """, unsafe_allow_html=True)
            if st.button("💾 Lưu!", key="luucauhinh"):
                code_content = "---\n---\n\n## Call:\n"
                for i in Called:
                    code_content += f"- [[{i}]]\n"
                st.code(code_content)

    else:
        st.info("Vui lòng nhập link thư mục Google Drive ở sidebar.")
main()


