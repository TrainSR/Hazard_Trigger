import streamlit as st
import re
import drive_module.drive_ops as drive_ops
from datetime import datetime


st.title("Time String Calculator - Live Update & Overwrite")

# Khởi tạo session_state cho input và kết quả
if "time_expr" not in st.session_state:
    st.session_state.time_expr = ""
if "result_str" not in st.session_state:
    st.session_state.result_str = ""

# Hệ số quy đổi về giây
unit_to_seconds = {
    "y": 365*24*3600,
    "mo": 30*24*3600,
    "d": 24*3600,
    "h": 3600,
    "m": 60,
    "s": 1
}

# Chuyển time string → giây
def time_string_to_seconds(s):
    parts = re.findall(r'\d+(?:y|mo|d|h|m|s)', s)
    total_seconds = 0
    for part in parts:
        match = re.match(r'(\d+)(y|mo|d|h|m|s)', part)
        if match:
            value, unit = match.groups()
            total_seconds += int(value) * unit_to_seconds[unit]
    return total_seconds

# Chuyển giây → time string chuẩn hóa
def seconds_to_time_string(total_seconds):
    remainder = total_seconds
    normalized_parts = []
    for unit, sec in [("y", 365*24*3600),
                      ("mo", 30*24*3600),
                      ("d", 24*3600),
                      ("h", 3600),
                      ("m", 60),
                      ("s", 1)]:
        count = remainder // sec
        if count > 0:
            normalized_parts.append(f"{int(count)}{unit}")
            remainder %= sec
    return "".join(normalized_parts)

# Hàm parse biểu thức → giây → string
def evaluate_expression(expr):
    try:
        if expr.strip() == "":
            return "", 0
        # Tách toán hạng và toán tử
        tokens = re.split(r'(\+|\-|\*|/)', expr)
        for i in range(0, len(tokens), 2):
            tokens[i] = str(time_string_to_seconds(tokens[i].strip()))
        numeric_expr = "".join(tokens)
        total_seconds = eval(numeric_expr)
        percent = f"{100 - 100 * total_seconds / int(tokens[0]):.3f}%"
        return seconds_to_time_string(int(total_seconds)), percent
    except:
        return "Lỗi", 0
    
# --- Nút ghi đè kết quả vào input ---
def overwrite_input(file_id = "1Zu4f_v3VIdhGEQuT5FhOK23LLH9oM7iY"):
    # Lưu lịch sử vào mô tả file

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    data_str = f"{timestamp} | {st.session_state.time_expr} | {st.session_state.result_str} | {y}"
    st.session_state.time_expr = st.session_state.result_str
    drive_ops.history_description(file_id, data_str)
def takeold():
    st.session_state.time_expr = st.session_state.latestvalue

file_id = "1Zu4f_v3VIdhGEQuT5FhOK23LLH9oM7iY"
metadata = drive_ops.get_file_metadata(file_id)
descrip = metadata.get('description', '')
if descrip:
    last_change = descrip.split("\n")
    st.session_state.latestvalue = last_change[-1].split("|")[2].strip()
else:
    st.session_state.latestvalue = ""
# --- Text area input ---
st.text_area("Nhập biểu thức:", key="time_expr", height=100)

# --- Tính toán kết quả tự động ---

x, y = evaluate_expression(st.session_state.time_expr)
st.session_state.result_str = x
# --- Hiển thị kết quả ---
if st.session_state.result_str != st.session_state.time_expr:
    st.success(f"Result: {st.session_state.result_str} ~ {y}")

col1, col2 = st.columns([1, 1])   # chia đều 2 cột

with col1:
    st.button(
        f"Old Value? - {st.session_state.latestvalue}",
        on_click=takeold,
        key="redreacheal"
    )

with col2:
    st.button(
        "Ghi đè kết quả vào input",
        on_click=overwrite_input,
        key="heheheh"
    )
