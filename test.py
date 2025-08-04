#main.py

import streamlit as st
import drive_module.drive_ops as drive_ops
import yaml
import re
import random

def gacha_form(label, file_id, Included, index, serie_exclude):
    yaml_data = drive_ops.get_or_cache_data(
        key=f"yaml_{file_id}",
        loader_func=lambda: drive_ops.extract_yaml_from_file_id(file_id),
        dependencies={"file_id": file_id}
    )

    if not yaml_data:
        return [], f"{label}_num_items", "manual", f"{label}_manual_choices"
    
    st.markdown(f"<h3 style='color:#0088ff;'>🔎 {label}</h3>", unsafe_allow_html=True)
    
    with st.expander(f"🔎 {label}", expanded=False):
        filters = {}
        cols = st.columns(3)
        for i, key in enumerate(yaml_data):
            checkbox_key = f"{label}_{key}"
            with cols[i % 3]:
                filters[key] = st.checkbox(key, value=key not in serie_exclude, key=checkbox_key)

        selected_items = set()
        for key, items in yaml_data.items():
            if isinstance(items, list):
                checkbox_key = f"{label}_{key}"
                if st.session_state.get(checkbox_key, False):
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
            max_gacha = len(filtered)
            if max_gacha > 0:
                num_items = st.number_input(
                    f"Số lượng Gacha cho {label}:",
                    min_value=1,
                    max_value=max_gacha,
                    value=max(1, min(index, max_gacha)),
                    step=1,
                    key=num_key
                )
            else:
                num_items = 0
        else:
            st.multiselect(
                f"Chọn thủ công cho {label}:", 
                options=filtered,
                key=manual_choices_key
            )

        st.markdown("---")

    return filtered, num_key, "gacha" if gacha_mode else "manual", manual_choices_key

def main():

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
                    loader_func=lambda: drive_ops.list_folder_contents(components_folder_id),
                    dependencies={"components_folder_id": components_folder_id}
                )

                files = {}
                for item in component_contents:
                    if item.get("mimeType") != "application/vnd.google-apps.folder" and item.get("name", "").endswith(".md"):
                        label = item["name"][:-3]  # bỏ phần .md
                        files[label] = item["id"]

        else:
            st.warning("📭 Thư mục rỗng hoặc không đọc được nội dung.")
        if important_folders:
            important_folder_id = important_folders[0]["id"]
            sub_contents = drive_ops.get_or_cache_data(
                key=f"folder_contents_{folder_id}",
                loader_func=lambda: drive_ops.list_folder_contents(important_folder_id),
                dependencies={"folder_id": folder_id}
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
                        dependencies={"folder_id": folder_id}
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
                        f"Chọn {folder_name}:", options=file_names + [""]
                    )
                    selected = next(
                        (f for f in md_files if f["name"] == selected_name + ".md"),
                        None,
                    )

                if selected:
                    file_id = selected["id"]
                    yaml_data = drive_ops.get_or_cache_data(
                        key=f"yaml_{file_id}",
                        loader_func=lambda: drive_ops.extract_yaml_from_file_id(file_id),
                        dependencies={"file_id": file_id}
                    )

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

                include_lines = drive_ops.get_or_cache_data(
                    key=f"include_section_{file_id}",
                    loader_func=lambda: drive_ops.extract_bullet_items_from_section(file_id, "Include"),
                    dependencies={"file_id": file_id, "section": "Include"}
                )

                include_list = []
                include_number = []

                for line in include_lines:
                    match = re.match(r'-\s*\[\[(.*?)\]\]\s*\|\s*(\d+)', line)
                    if match:
                        component_name = match.group(1)
                        quantity = match.group(2)
                        include_list.append(component_name)
                        include_number.append(quantity)

                if include_list:
                    with st.expander("📦 Thành phần Include", expanded=False):
                        for i in range(len(include_list)):
                            st.markdown(
                                f"- <span style='color:#0073ff'><b>{include_list[i]}</b></span>: {include_number[i]}",
                                unsafe_allow_html=True
                            )
                            Include_List.extend(include_list)
                            Include_Num.extend(include_number)

        tab_labels = ["🎮 Gacha Chính", "Components", "Sorted_Components"]
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
                loader_func=lambda: drive_ops.list_folder_contents(sorted_components_folder_id),
                dependencies={"folder_id": sorted_components_folder_id}
            )

            sorted_component_folders = sorted(
                [{"name": item["name"], "id": item["id"]}
                 for item in sorted_subfolders
                 if item.get("mimeType") == "application/vnd.google-apps.folder"],
                key=lambda x: x["name"].lower()
            )

            with tabs[2]:  # Tab Sorted_Components
                for folder in sorted_component_folders:
                    folder_name = folder["name"]
                    folder_id = folder["id"]

                    st.markdown(
                        f"<h3 style='color:#00bfff;'>📦 Sorted - {folder_name}</h3>",
                        unsafe_allow_html=True,
                    )

                    try:
                        folder_contents = drive_ops.get_or_cache_data(
                            key=f"folder_contents_{folder_id}",
                            loader_func=lambda: drive_ops.list_folder_contents(folder_id),
                            dependencies={"folder_id": folder_id}
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

                    for selected in md_files:
                        file_id = selected["id"]
                        yaml_data = drive_ops.get_or_cache_data(
                            key=f"yaml_{file_id}",
                            loader_func=lambda: drive_ops.extract_yaml_from_file_id(file_id),
                            dependencies={"file_id": file_id}
                        )

                        if yaml_data:
                            Prompt.extend(yaml_data.get("Prompt", []))
                            Negative.extend(yaml_data.get("Negative", []))
                            Exclude.extend(yaml_data.get("Exclude", []))

                            with st.expander(f"🧾 YAML - {selected['name']}", expanded=False):
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

                        include_lines = drive_ops.get_or_cache_data(
                            key=f"include_section_{file_id}",
                            loader_func=lambda: drive_ops.extract_bullet_items_from_section(file_id, "Include"),
                            dependencies={"file_id": file_id, "section": "Include"}
                        )

                        include_list = []
                        include_number = []

                        for line in include_lines:
                            match = re.match(r'-\s*\[\[(.*?)\]\]\s*\|\s*(\d+)', line)
                            if match:
                                component_name = match.group(1)
                                quantity = match.group(2)
                                include_list.append(component_name)
                                include_number.append(quantity)

                        if include_list:
                            with st.expander(f"📦 Include - {selected['name']}", expanded=False):
                                for i in range(len(include_list)):
                                    st.markdown(
                                        f"- <span style='color:#0073ff'><b>{include_list[i]}</b></span>: {include_number[i]}",
                                        unsafe_allow_html=True
                                    )
                                    Include_List.append(include_list[i])
                                    Include_Num.append(include_number[i])

        results_dict = {}
        num_items_dict = {}
        mode_dict = {}
        manual_key_dict = {}
        serie_exclude = Exclude

        with tabs[1]:
            for i, (label, file_id) in enumerate(files.items(), start=1):
                Included = False
                index = 1
                serie_include = Include_List
                include_numbering = Include_Num
                if label in serie_include:
                    index = int(include_numbering[serie_include.index(label)])
                    Included = True

                # Gọi gacha_form với file_id thay vì filepath
                filtered, num_key, mode, manual_key = gacha_form(label, file_id, Included, index, serie_exclude)

                results_dict[label] = filtered
                num_items_dict[label] = num_key
                mode_dict[label] = mode
                manual_key_dict[label] = manual_key

        # Tab Gacha Chính
        with tabs[0]:
            Init_Prompt = st.text_input("Prompt Gốc: ", value="", key="input_init_intro")
            Lora_Prompt = st.text_input(
                "Prompt Lora: ",
                value="best quality, hyper-detailed, high contrast, depth of field, ray tracing, best lighting, cinematic composition, beautiful face, beautiful eyes, sharp focus, (masterpiece:1.2), (best quality:1.2), (very aesthetic:1.2), (absurdres:1.2), (detailed background),",
                key="Lora_outa_outro"
            )
            st.subheader("✨ Quay Gacha Tất Cả")
            final_results = []

            if st.button("🎲 Quay!"):
                for label, file_id in files.items():  # file_id được dùng thay cho filepath
                    pool = results_dict.get(label, [])
                    mode = mode_dict.get(label)

                    if mode == "gacha":
                        num_key = num_items_dict.get(label)
                        num = st.session_state.get(num_key, 0)
                        if pool and num > 0:
                            chosen = random.sample(pool, num)
                            final_results.extend(chosen)
                        else:
                            st.info(f"{label}: Không có dữ liệu hoặc số lượng = 0.")
                    else:
                        manual_key = manual_key_dict.get(label)
                        chosen = st.session_state.get(manual_key, [])
                        if chosen:
                            final_results.extend(chosen)

                # Xử lý prompt và negative
                serie_prompt = Prompt
                serie_negative = Negative
                cleaned = [item.strip().strip(",") for item in final_results]

                # Ghép prompt của series (nếu có) và Default_Prompt
                all_prompts = []
                if Init_Prompt != "":
                    all_prompts.append(Init_Prompt)
                if serie_prompt:
                    all_prompts.extend([item.strip().strip(",") for item in serie_prompt])
                all_prompts.extend(cleaned)
                all_prompts.append(Lora_Prompt)

                joined = ", ".join(all_prompts)
                st.subheader("📋 Prompt dạng chuỗi copy được:")
                st.code(joined, language="text")

                # In Negative riêng nếu có
                try:
                    cleaned_neg = serie_negative[0].strip().strip(",")
                    st.subheader("🚫 Negative Prompt:")
                    st.code(cleaned_neg, language="text")
                except:
                    pass

    else:
        st.info("Vui lòng nhập link thư mục Google Drive ở sidebar.")
main()


