# -*- coding: utf-8 -*-
from __future__ import annotations

import base64
import io
import math
import mimetypes
import re
from pathlib import Path
from typing import Iterable

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components


plt.rcParams["font.family"] = ["Malgun Gothic", "Arial", "sans-serif"]
plt.rcParams["axes.unicode_minus"] = False

BASE_DIR = Path(__file__).resolve().parent
ASSET_DIR = BASE_DIR / "asset"
DATA_FILE = ASSET_DIR / "vib_data.xlsx"

DARK_BLUE = "#06113f"
EMERALD = "#63f7cf"
LIGHT_GRAY = "#eeeeee"
TEXT_BLUE = "#05205d"
MAX_WIDTH = 1080


st.set_page_config(
    page_title="Vibration Analysis",
    page_icon=str(ASSET_DIR / "logo.png"),
    layout="wide",
    initial_sidebar_state="collapsed",
)


@st.cache_data(show_spinner=False)
def file_to_data_uri(path_string: str) -> str:
    path = Path(path_string)
    if not path.exists():
        return ""
    mime_type, _ = mimetypes.guess_type(path.name)
    mime_type = mime_type or "application/octet-stream"
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"


def asset_uri(name: str) -> str:
    return file_to_data_uri(str(ASSET_DIR / name))


def render_html(markup: str) -> None:
    st.html(markup)


def get_page() -> str:
    try:
        value = st.query_params.get("page", "home")
    except Exception:
        value = st.experimental_get_query_params().get("page", ["home"])
    if isinstance(value, list):
        value = value[0] if value else "home"
    return str(value or "home").lower()


def get_query_value(key: str, default: str) -> str:
    try:
        value = st.query_params.get(key, default)
    except Exception:
        value = st.experimental_get_query_params().get(key, [default])
    if isinstance(value, list):
        value = value[0] if value else default
    return str(value or default)


def set_page(page: str) -> None:
    try:
        st.query_params["page"] = page
    except Exception:
        st.experimental_set_query_params(page=page)


def clean_number_series(values: Iterable[object]) -> np.ndarray:
    series = pd.Series(list(values))
    numeric = pd.to_numeric(series, errors="coerce").dropna()
    return numeric.to_numpy(dtype=float)


def excel_col_to_index(col: str) -> int:
    value = 0
    for char in col.upper():
        if not char.isalpha():
            raise ValueError("열 문자는 A-Z 형식이어야 합니다.")
        value = value * 26 + (ord(char) - ord("A") + 1)
    return value - 1


def parse_cell(cell: str) -> tuple[int, int]:
    match = re.fullmatch(r"\s*([A-Za-z]+)\s*(\d+)\s*", cell)
    if not match:
        raise ValueError("셀 주소는 A2처럼 입력해주세요.")
    col = excel_col_to_index(match.group(1))
    row = int(match.group(2)) - 1
    if row < 0 or col < 0:
        raise ValueError("셀 주소 범위가 올바르지 않습니다.")
    return row, col


def parse_range(range_text: str) -> tuple[int, int, int, int]:
    match = re.fullmatch(
        r"\s*([A-Za-z]+\s*\d+)\s*[-:]\s*([A-Za-z]+\s*\d+)\s*", range_text
    )
    if not match:
        raise ValueError("데이터 범위는 A2-A100 또는 A2:A100 형식으로 입력해주세요.")
    row1, col1 = parse_cell(match.group(1))
    row2, col2 = parse_cell(match.group(2))
    return min(row1, row2), min(col1, col2), max(row1, row2), max(col1, col2)


def extract_range_from_dataframe(df: pd.DataFrame, range_text: str) -> np.ndarray:
    row1, col1, row2, col2 = parse_range(range_text)
    if row2 >= len(df.index) or col2 >= len(df.columns):
        raise ValueError("입력한 데이터 범위가 파일의 실제 행/열 범위를 벗어났습니다.")
    selected = df.iloc[row1 : row2 + 1, col1 : col2 + 1]
    return clean_number_series(selected.to_numpy().ravel())


def read_uploaded_signal(uploaded_file, range_text: str) -> np.ndarray:
    suffix = Path(uploaded_file.name).suffix.lower()
    if suffix == ".csv":
        df = pd.read_csv(uploaded_file, header=None)
    elif suffix in {".xlsx", ".xls"}:
        df = pd.read_excel(uploaded_file, header=None, engine="openpyxl")
    else:
        raise ValueError("CSV 또는 XLSX 파일만 업로드할 수 있습니다.")
    values = extract_range_from_dataframe(df, range_text)
    if values.size < 4:
        raise ValueError("FFT 변환을 위해 최소 4개 이상의 숫자 데이터가 필요합니다.")
    return values


def compute_fft(values: np.ndarray, sampling_rate: float) -> tuple[np.ndarray, np.ndarray]:
    if sampling_rate <= 0:
        raise ValueError("샘플링 속도는 0보다 커야 합니다.")
    centered = values - np.mean(values)
    n = centered.size
    freqs = np.fft.rfftfreq(n, d=1.0 / sampling_rate)
    amplitudes = np.abs(np.fft.rfft(centered)) * 2.0 / n
    if amplitudes.size:
        amplitudes[0] = amplitudes[0] / 2.0
    return freqs, amplitudes


def top_frequency_table(freqs: np.ndarray, amplitudes: np.ndarray, top_n: int = 10) -> pd.DataFrame:
    frame = pd.DataFrame({"Frequency (Hz)": freqs, "Amplitude": amplitudes})
    frame = frame.replace([np.inf, -np.inf], np.nan).dropna()
    frame = frame[frame["Frequency (Hz)"] > 0]
    frame = frame.sort_values("Amplitude", ascending=False).head(top_n).reset_index(drop=True)
    frame.index = frame.index + 1
    return frame.round({"Frequency (Hz)": 4, "Amplitude": 8})


def make_time_plot(values: np.ndarray, sampling_rate: float):
    t = np.arange(values.size) / sampling_rate
    fig, ax = plt.subplots(figsize=(7.2, 4.2), dpi=130)
    ax.plot(t, values, color="#153e90", linewidth=1.15)
    ax.set_title("Displacement - Time", fontsize=12, fontweight="bold")
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Displacement")
    ax.grid(True, alpha=0.22)
    fig.tight_layout()
    return fig


def make_frequency_plot(
    freqs: np.ndarray,
    amplitudes: np.ndarray,
    title: str,
    focus_top: bool = False,
):
    fig, ax = plt.subplots(figsize=(7.2, 4.2), dpi=130)
    ax.plot(freqs, amplitudes, color="#0b7a75", linewidth=1.15)
    ax.set_title(title, fontsize=12, fontweight="bold")
    ax.set_xlabel("Frequency (Hz)")
    ax.set_ylabel("Amplitude")
    ax.grid(True, alpha=0.22)
    if focus_top and freqs.size > 1:
        table = top_frequency_table(freqs, amplitudes)
        if not table.empty:
            max_freq = float(table["Frequency (Hz)"].max())
            ax.set_xlim(left=0, right=max(max_freq * 1.15, 1.0))
    fig.tight_layout()
    return fig


def make_case_plot(freqs: np.ndarray, amplitudes: np.ndarray, title: str):
    fig, ax = plt.subplots(figsize=(6.7, 3.6), dpi=130)
    ax.plot(freqs, amplitudes, color="#102b77", linewidth=1.05)
    ax.set_title(title, fontsize=11, fontweight="bold")
    ax.set_xlabel("Frequency (Hz)")
    ax.set_ylabel("Amplitude")
    ax.grid(True, alpha=0.2)
    if freqs.size > 1:
        table = top_frequency_table(freqs, amplitudes)
        if not table.empty:
            ax.set_xlim(left=0, right=max(float(table["Frequency (Hz)"].max()) * 1.15, 1.0))
    fig.tight_layout()
    return fig


@st.cache_data(show_spinner=False)
def load_case_data() -> pd.DataFrame:
    return pd.read_excel(DATA_FILE, sheet_name=0, header=0, engine="openpyxl")


def get_case_columns(freq_col: str, amp_col: str) -> tuple[np.ndarray, np.ndarray]:
    df = load_case_data()
    freqs = pd.to_numeric(df[freq_col], errors="coerce")
    amps = pd.to_numeric(df[amp_col], errors="coerce")
    valid = freqs.notna() & amps.notna()
    return freqs[valid].to_numpy(dtype=float), amps[valid].to_numpy(dtype=float)


def inject_css() -> None:
    background_uri = asset_uri("background.png")
    css = f"""
    <style>
    :root {{
        --dark-blue: {DARK_BLUE};
        --emerald: {EMERALD};
        --light-gray: {LIGHT_GRAY};
        --text-blue: {TEXT_BLUE};
        --max-width: {MAX_WIDTH}px;
        --brand-height: 74px;
        --menu-height: 44px;
        --category-height: 42px;
        --header-height: 160px;
    }}

    html {{
        scroll-behavior: smooth;
        margin: 0;
        padding: 0;
        width: 100%;
        overflow-x: hidden;
    }}

    body {{
        margin: 0;
        padding: 0;
        color: #000;
        font-family: Arial, "Noto Sans KR", sans-serif;
        overflow-x: hidden;
    }}

    .stApp {{
        background:
            linear-gradient(180deg, rgba(2, 8, 40, 0.4), rgba(25, 0, 130, 0.55)),
            url("{background_uri}") center center / cover fixed no-repeat;
        margin: 0;
        padding: 0;
    }}

    [data-testid="stAppViewContainer"],
    [data-testid="stMain"],
    .main {{
        margin: 0 !important;
        padding: 0 !important;
        width: 100% !important;
        min-width: 100% !important;
        max-width: none !important;
    }}

    header[data-testid="stHeader"],
    div[data-testid="stToolbar"],
    #MainMenu,
    footer[data-testid="stFooter"] {{
        visibility: hidden;
        height: 0;
    }}

    [data-testid="stMainBlockContainer"],
    .block-container {{
        max-width: none !important;
        width: 100% !important;
        min-width: 100% !important;
        margin: 0 !important;
        padding: 0 !important;
    }}

    div[data-testid="stVerticalBlock"] {{
        gap: 0 !important;
    }}

    div[data-testid="stElementContainer"] {{
        margin: 0 !important;
        width: 100% !important;
        max-width: none !important;
    }}

    div[data-testid="stHtml"] {{
        display: block;
        width: 100% !important;
        max-width: none !important;
    }}

    .site-header {{
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        z-index: 9999;
        width: 100%;
        box-shadow: 0 1px 0 rgba(0, 0, 0, 0.08);
    }}

    .header-spacer {{
        height: var(--header-height);
        width: 100%;
    }}

    section {{
        scroll-margin-top: var(--header-height);
    }}

    .nav-black {{
        background: #000;
        color: #fff;
        width: 100%;
    }}

    .nav-inner {{
        max-width: var(--max-width);
        margin: 0 auto;
        padding: 0 36px;
        box-sizing: border-box;
    }}

    .brand-row {{
        height: var(--brand-height);
        display: flex;
        align-items: center;
        justify-content: space-between;
    }}

    .brand-left {{
        display: flex;
        align-items: center;
        gap: 18px;
        text-decoration: none !important;
        color: #fff !important;
    }}

    .brand-logo {{
        width: 68px;
        height: auto;
        display: block;
    }}

    .brand-name {{
        font-size: 27px;
        line-height: 1;
        font-weight: 800;
        color: #fff;
        letter-spacing: 0;
    }}

    .about-wrap {{
        position: relative;
        width: 34px;
        height: 34px;
        display: flex;
        align-items: center;
        justify-content: center;
    }}

    .about-icon {{
        width: 27px;
        height: 27px;
        object-fit: contain;
        display: block;
    }}

    .about-tooltip {{
        position: absolute;
        right: 0;
        top: 42px;
        width: 390px;
        padding: 12px 14px;
        background: #fff;
        color: #111;
        border: 1px solid #d7d7d7;
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.2);
        opacity: 0;
        pointer-events: none;
        transform: translateY(-4px);
        transition: 0.18s ease;
        font-size: 14px;
        text-align: center;
        white-space: nowrap;
        z-index: 10000;
    }}

    .about-wrap:hover .about-tooltip {{
        opacity: 1;
        transform: translateY(0);
    }}

    .menu-row {{
        height: var(--menu-height);
        display: flex;
        align-items: center;
        gap: clamp(34px, 7vw, 90px);
    }}

    .menu-row a {{
        color: #fff !important;
        text-decoration: none !important;
        font-size: 14px;
        font-weight: 500;
    }}

    .menu-trigger {{
        color: #fff;
        font-size: 14px;
        font-weight: 500;
        cursor: default;
        user-select: none;
    }}

    .menu-item {{
        position: relative;
        height: var(--menu-height);
        display: flex;
        align-items: center;
    }}

    .cases-dropdown {{
        position: absolute;
        left: 50%;
        top: calc(100% - 2px);
        width: 265px;
        transform: translateX(-50%) translateY(-4px);
        background: #fff;
        border: 1px solid #d9d9d9;
        box-shadow: 0 10px 26px rgba(0, 0, 0, 0.24);
        opacity: 0;
        pointer-events: none;
        transition: 0.16s ease;
        z-index: 10001;
        padding: 8px 0;
    }}

    .menu-item:hover .cases-dropdown {{
        opacity: 1;
        pointer-events: auto;
        transform: translateX(-50%) translateY(0);
    }}

    .cases-dropdown a {{
        display: block;
        color: #111 !important;
        padding: 12px 16px;
        font-size: 14px;
        line-height: 1.2;
        white-space: nowrap;
    }}

    .cases-dropdown a:hover {{
        background: #f0f0f0;
        color: var(--text-blue) !important;
    }}

    .category-bar {{
        height: var(--category-height);
        background: #fff;
        color: var(--text-blue);
        display: flex;
        align-items: center;
        width: 100%;
    }}

    .category-inner {{
        max-width: var(--max-width);
        margin: 0 auto;
        width: 100%;
        padding: 0 36px;
        box-sizing: border-box;
        font-size: 14px;
        color: var(--text-blue);
    }}

    .section-inner {{
        max-width: var(--max-width);
        margin: 0 auto;
        padding: 0 36px;
        box-sizing: border-box;
    }}

    .hero {{
        min-height: 405px;
        display: flex;
        align-items: center;
        background-size: cover;
        background-position: center;
    }}

    .hero .section-inner {{
        width: 100%;
        text-align: left;
    }}

    .hero h1 {{
        margin: 0 0 13px;
        color: #fff;
        font-size: clamp(28px, 3.65vw, 42px);
        line-height: 1.12;
        font-weight: 850;
        letter-spacing: 0;
        text-align: left;
    }}

    .hero p {{
        margin: 0;
        color: #fff;
        font-size: 15.5px;
        font-weight: 500;
        text-align: left;
    }}

    .split-band {{
        min-height: 345px;
        display: flex;
        align-items: center;
    }}

    .white-band {{
        background: #fff;
        box-shadow: 0 0 0 100vmax #fff;
        clip-path: inset(0 -100vmax);
    }}

    .gray-band {{
        background: var(--light-gray);
        box-shadow: 0 0 0 100vmax var(--light-gray);
        clip-path: inset(0 -100vmax);
    }}

    .split-grid {{
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 64px;
        align-items: center;
        width: 100%;
    }}

    .copy h2 {{
        margin: 0 0 46px;
        font-size: 33px;
        line-height: 1.1;
        font-weight: 500;
        color: #000;
        letter-spacing: 0;
    }}

    .copy h2.blue {{
        color: var(--text-blue);
    }}

    .copy p {{
        margin: 0 0 18px;
        font-size: 16px;
        line-height: 1.45;
        color: #000;
    }}

    .split-image {{
        width: 100%;
        max-height: 250px;
        object-fit: contain;
        display: block;
    }}

    .fft-intro {{
        min-height: 700px;
        display: flex;
        align-items: center;
        color: #fff;
        box-sizing: border-box;
        padding: 34px 0 46px;
    }}

    .fft-intro h2 {{
        margin: 0 0 56px;
        color: #fff;
        font-size: 34px;
        font-weight: 850;
        letter-spacing: 0;
    }}

    .fft-image {{
        display: block;
        width: min(610px, 70%);
        margin: 0 auto 50px;
        background: #fff;
    }}

    .fft-copy {{
        max-width: 820px;
        margin: 0 auto;
        color: #fff;
        font-size: 18px;
        line-height: 1.48;
    }}

    .cta-row {{
        display: flex;
        justify-content: center;
        margin-top: 34px;
    }}

    .cta-button {{
        display: inline-flex;
        align-items: center;
        justify-content: center;
        min-height: 54px;
        padding: 0 38px;
        background: var(--emerald);
        color: #001716 !important;
        text-decoration: none !important;
        font-weight: 800;
        font-size: 18px;
        border: none;
    }}

    .cases-band {{
        background: var(--light-gray);
        box-shadow: 0 0 0 100vmax var(--light-gray);
        clip-path: inset(0 -100vmax);
        min-height: 660px;
        padding: 52px 0 82px;
    }}

    .cases-band h2 {{
        margin: 0 0 44px;
        font-size: 31px;
        font-weight: 850;
        letter-spacing: 0;
    }}

    .case-card-grid {{
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: 34px;
    }}

    .case-card {{
        background: #fff;
        min-height: 485px;
        display: flex;
        flex-direction: column;
        box-shadow: 0 3px 10px rgba(0, 0, 0, 0.32);
        border: 1px solid #d2d2d2;
    }}

    .case-card img {{
        width: 100%;
        aspect-ratio: 1.42 / 1;
        object-fit: cover;
        display: block;
    }}

    .case-card-body {{
        padding: 26px 28px 34px;
        display: flex;
        flex: 1;
        flex-direction: column;
    }}

    .case-card h3 {{
        margin: 0 0 28px;
        font-size: 18px;
        line-height: 1.18;
        font-weight: 850;
        color: #000;
        letter-spacing: 0;
    }}

    .case-card p {{
        margin: 0;
        color: #000;
        font-size: 15px;
        line-height: 1.32;
        padding-bottom: 24px;
    }}

    .round-arrow {{
        align-self: flex-end;
        margin-top: auto;
        width: 47px;
        height: 47px;
        border-radius: 999px;
        background: var(--emerald);
        color: #001716 !important;
        text-decoration: none !important;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        font-size: 0;
        font-weight: 900;
        line-height: 1;
        position: relative;
    }}

    .round-arrow::before {{
        content: ">";
        position: absolute;
        left: 50%;
        top: 50%;
        font-family: Arial, "Noto Sans KR", sans-serif;
        font-size: 21px;
        font-weight: 900;
        line-height: 1;
        transform: translate(-50%, -54%);
    }}

    .site-footer {{
        min-height: 240px;
        color: #fff;
        display: flex;
        align-items: flex-end;
    }}

    .footer-inner {{
        max-width: var(--max-width);
        width: 100%;
        margin: 0 auto;
        padding: 0 36px 34px;
        box-sizing: border-box;
    }}

    .footer-top {{
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 30px;
        margin-bottom: 18px;
        font-weight: 850;
        font-size: 17px;
    }}

    .footer-brand {{
        display: flex;
        align-items: center;
        gap: 18px;
        font-size: 28px;
    }}

    .footer-brand img {{
        width: 64px;
        height: auto;
    }}

    .footer-line {{
        height: 3px;
        background: rgba(255, 255, 255, 0.95);
        width: 100%;
    }}

    .page-spacer {{
        min-height: 520px;
    }}

    div[data-testid="stForm"] {{
        background: var(--light-gray);
        border: none;
        border-radius: 0;
        padding: 48px max(36px, calc((100vw - var(--max-width)) / 2 + 36px)) 44px;
        max-width: none !important;
        width: 100% !important;
        min-height: 370px;
        margin-left: 0 !important;
        margin-right: 0 !important;
        box-sizing: border-box;
    }}

    div[data-testid="stForm"] h2 {{
        font-size: 28px;
        color: #000;
        margin-bottom: 24px;
    }}

    div[data-testid="stForm"] [data-testid="stFileUploader"],
    div[data-testid="stForm"] [data-testid="stNumberInput"],
    div[data-testid="stForm"] [data-testid="stTextInput"] {{
        max-width: 560px;
    }}

    .st-key-fft_plot_band,
    .st-key-case_visual_band,
    .st-key-case_plot_band {{
        background: #fff;
        width: 100% !important;
        max-width: none !important;
        margin-left: 0 !important;
        margin-right: 0 !important;
        padding: 58px max(36px, calc((100vw - var(--max-width)) / 2 + 36px)) 64px;
        min-height: 620px;
        box-sizing: border-box;
    }}

    .st-key-case_visual_band {{
        background: transparent;
        min-height: 430px;
        padding-top: 54px;
        padding-bottom: 50px;
    }}

    .stButton > button,
    button[kind="primaryFormSubmit"],
    div[data-testid="stFormSubmitButton"] button {{
        background: var(--emerald) !important;
        color: #001716 !important;
        border: 0 !important;
        border-radius: 0 !important;
        min-height: 45px;
        font-weight: 850 !important;
        box-shadow: none !important;
    }}

    .stButton > button:hover,
    div[data-testid="stFormSubmitButton"] button:hover {{
        background: #7dffdc !important;
        color: #001716 !important;
        border: 0 !important;
    }}

    .plot-band {{
        background: #fff;
        padding: 58px 0 64px;
        min-height: 620px;
    }}

    .plot-band .section-inner {{
        max-width: var(--max-width);
    }}

    .case-control-number {{
        color: #fff;
        font-size: 38px;
        font-weight: 500;
        text-align: center;
        margin: 0;
        line-height: 1;
        width: 140px;
    }}

    .case-button-stack {{
        display: flex;
        flex-direction: column;
        gap: 22px;
        width: 150px;
    }}

    .case-svg-wrap {{
        width: 100%;
        height: 320px;
        display: flex;
        align-items: center;
        justify-content: center;
    }}

    .case-svg-wrap svg {{
        width: 100%;
        height: 100%;
        display: block;
    }}

    .case-image-wrap {{
        width: 100%;
        height: 330px;
        display: flex;
        align-items: center;
        justify-content: center;
    }}

    .case-image-wrap img {{
        max-width: 100%;
        max-height: 100%;
        object-fit: contain;
        display: block;
    }}

    .case-motor-scene {{
        width: 100%;
        height: 330px;
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 34px;
        overflow: visible;
    }}

    .case-motor-scene img {{
        width: min(42%, 360px);
        max-height: 280px;
        object-fit: contain;
        display: block;
    }}

    .case-motor-right {{
        transform-origin: 50% 50%;
        transition: transform 0.18s ease;
    }}

    .case-angle-control-wrap {{
        min-height: 250px;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        gap: 14px;
    }}

    .st-key-case1_angle_controls [data-testid="stVerticalBlock"] {{
        min-height: 310px;
        display: grid !important;
        grid-template-rows: 96px 48px 96px;
        align-items: center;
        justify-content: center;
        justify-items: center;
        gap: 18px !important;
    }}

    .st-key-case1_angle_controls [data-testid="stElementContainer"] {{
        width: 140px !important;
        display: flex !important;
        justify-content: center !important;
        margin: 0 !important;
    }}

    .st-key-case1_angle_controls div[data-testid="stHtml"] {{
        width: 140px !important;
    }}

    .st-key-case1_angle_up button,
    .st-key-case1_angle_down button {{
        width: 132px !important;
        height: 88px !important;
        min-height: 88px !important;
        margin: 0 auto !important;
        background: transparent !important;
        color: var(--emerald) !important;
        border: 0 !important;
        font-size: 0 !important;
        font-weight: 900 !important;
        line-height: 1 !important;
        padding: 0 !important;
        position: relative !important;
        box-shadow: none !important;
    }}

    .st-key-case1_angle_up button::before,
    .st-key-case1_angle_down button::before {{
        content: "";
        position: absolute;
        left: 50%;
        width: 23px;
        height: 44px;
        background: var(--emerald);
        transform: translateX(-50%);
        border-radius: 2px;
    }}

    .st-key-case1_angle_up button::after,
    .st-key-case1_angle_down button::after {{
        content: "";
        position: absolute;
        left: 50%;
        transform: translateX(-50%);
        width: 0;
        height: 0;
        border-left: 32px solid transparent;
        border-right: 32px solid transparent;
    }}

    .st-key-case1_angle_up button::before {{
        top: 34px;
    }}

    .st-key-case1_angle_up button::after {{
        top: 7px;
        border-bottom: 34px solid var(--emerald);
    }}

    .st-key-case1_angle_down button::before {{
        bottom: 34px;
    }}

    .st-key-case1_angle_down button::after {{
        bottom: 7px;
        border-top: 34px solid var(--emerald);
    }}

    .st-key-case1_angle_up button:hover,
    .st-key-case1_angle_down button:hover {{
        background: transparent !important;
        color: #89ffe2 !important;
    }}

    .st-key-case1_angle_up button:hover::before,
    .st-key-case1_angle_down button:hover::before {{
        background: #89ffe2;
    }}

    .st-key-case1_angle_up button:hover::after {{
        border-bottom-color: #89ffe2;
    }}

    .st-key-case1_angle_down button:hover::after {{
        border-top-color: #89ffe2;
    }}

    .st-key-case3_mode_mass button,
    .st-key-case3_mode_crack button,
    .st-key-case3_mode_bolt button {{
        width: 150px !important;
        min-height: 48px !important;
        margin: 0 auto !important;
        font-size: 16px !important;
    }}

    .st-key-case3_mode_mass,
    .st-key-case3_mode_crack {{
        margin-bottom: 28px !important;
    }}

    .case3-button-gap {{
        height: 34px;
        width: 100%;
    }}

    .arrow-separator {{
        display: flex;
        align-items: center;
        justify-content: center;
        min-height: 70px;
        color: var(--emerald);
        font-size: 62px;
        font-weight: 900;
    }}

    .references-panel {{
        background: var(--light-gray);
        box-shadow: 0 0 0 100vmax var(--light-gray);
        clip-path: inset(0 -100vmax);
        min-height: 310px;
        padding: 62px 0 48px;
    }}

    .references-panel li {{
        margin: 0 0 26px;
        font-size: 16px;
        line-height: 1.45;
        color: #000;
    }}

    .references-panel a {{
        color: #0056d6 !important;
    }}

    .status-note {{
        min-height: 310px;
        display: flex;
        align-items: center;
        justify-content: center;
        color: #777;
        font-size: 18px;
        border: 1px dashed #c7c7c7;
        background: #fafafa;
    }}

    .mobile-break {{
        display: none;
    }}

    @media (max-width: 780px) {{
        .nav-inner,
        .category-inner,
        .section-inner,
        .footer-inner {{
            padding-left: 22px;
            padding-right: 22px;
        }}

        .brand-row {{
            height: 68px;
        }}

        .brand-logo {{
            width: 50px;
        }}

        .brand-name {{
            font-size: 21px;
        }}

        .menu-row {{
            gap: 22px;
            overflow-x: auto;
            white-space: nowrap;
        }}

        .hero {{
            min-height: 310px;
        }}

        .split-grid,
        .case-card-grid,
        .case-visual-grid {{
            grid-template-columns: 1fr;
            gap: 34px;
        }}

        .split-band {{
            padding: 46px 0;
        }}

        .fft-image {{
            width: 100%;
        }}

        .footer-top {{
            align-items: flex-start;
            flex-direction: column;
        }}

        .footer-brand {{
            font-size: 23px;
        }}

        .mobile-break {{
            display: inline;
        }}
    }}
    </style>
    """
    render_html(css)


def render_header(active_label: str) -> None:
    logo_uri = asset_uri("logo.png")
    about_uri = asset_uri("about_me.png")
    html = f"""
    <div class="site-header">
        <div class="nav-black">
            <div class="nav-inner">
                <div class="brand-row">
                    <a class="brand-left" href="?page=home" target="_self" title="Home">
                        <img class="brand-logo" src="{logo_uri}" alt="Vibration Analysis logo">
                        <span class="brand-name">Vibration Analysis</span>
                    </a>
                    <div class="about-wrap" aria-label="about me">
                        <img class="about-icon" src="{about_uri}" alt="about me">
                        <div class="about-tooltip">기계시스템디자인공학과 C217162 유재원</div>
                    </div>
                </div>
                <nav class="menu-row" aria-label="main navigation">
                    <a href="?page=home#motivation" target="_self">Motivation</a>
                    <a href="?page=fft" target="_self">FFT transform</a>
                    <div class="menu-item">
                        <span class="menu-trigger">Cases</span>
                        <div class="cases-dropdown">
                            <a href="?page=case1" target="_self">Shaft angular misalignment</a>
                            <a href="?page=case2" target="_self">Bearing inner &amp; outer defect</a>
                            <a href="?page=case3" target="_self">Floating wind turbine defect</a>
                        </div>
                    </div>
                    <a href="?page=references" target="_self">References</a>
                </nav>
            </div>
        </div>
        <div class="category-bar">
            <div class="category-inner" id="active-category-label">{active_label}</div>
        </div>
    </div>
    <div class="header-spacer" aria-hidden="true"></div>
    """
    render_html(html)


def render_footer() -> None:
    logo_uri = asset_uri("logo.png")
    html = f"""
    <footer class="site-footer">
        <div class="footer-inner">
            <div class="footer-top">
                <div class="footer-brand">
                    <img src="{logo_uri}" alt="Vibration Analysis logo">
                    <span>Vibration Analysis</span>
                </div>
                <div>기계시스템디자인공학과 C217162 유재원</div>
            </div>
            <div class="footer-line"></div>
        </div>
    </footer>
    """
    render_html(html)


def render_main_category_tracker() -> None:
    components.html(
        """
        <script>
        (function () {
            const parentWindow = window.parent;
            const parentDocument = parentWindow.document;

            function installTracker() {
                const label = parentDocument.getElementById("active-category-label");
                const sections = [
                    { id: "motivation", label: "Motivation" },
                    { id: "fft-info", label: "FFT transform" },
                    { id: "cases", label: "Cases" },
                ].map((item) => ({
                    label: item.label,
                    element: parentDocument.getElementById(item.id),
                }));

                if (!label || sections.some((item) => !item.element)) {
                    parentWindow.setTimeout(installTracker, 100);
                    return;
                }

                function updateCategory() {
                    const headerHeight = 160;
                    let active = "Motivation";
                    for (const section of sections) {
                        const top = section.element.getBoundingClientRect().top;
                        if (top <= headerHeight + 8) {
                            active = section.label;
                        }
                    }
                    label.textContent = active;
                }

                parentWindow.removeEventListener("scroll", updateCategory);
                parentWindow.addEventListener("scroll", updateCategory, { passive: true });
                parentWindow.addEventListener("resize", updateCategory);
                updateCategory();
            }

            installTracker();
        })();
        </script>
        """,
        height=0,
    )


def render_main_page() -> None:
    render_header("Motivation")
    hero_uri = asset_uri("man_with_analysis_device.png")
    vib1_uri = asset_uri("about_vibration_1.png")
    vib2_uri = asset_uri("about_vibration_2.png")
    fft_uri = asset_uri("fft_transform.png")
    motor_uri = asset_uri("motor_misalignment.jpg")
    bearing_uri = asset_uri("bearing.jpeg")
    wind_uri = asset_uri("wind_turbine.jpg")

    html = f"""
    <main>
        <section id="motivation" class="hero"
            style='background-image: linear-gradient(90deg, rgba(4, 18, 55, 0.98) 0%, rgba(4, 18, 55, 0.73) 35%, rgba(4, 18, 55, 0.18) 64%, rgba(4, 18, 55, 0.04) 100%), url("{hero_uri}");'>
            <div class="section-inner">
                <h1>Vibration Analysis (FFT)</h1>
                <p>진동 분석에 대해 알아보고 실제 사례를 살펴보기</p>
            </div>
        </section>

        <section class="split-band white-band">
            <div class="section-inner">
                <div class="split-grid">
                    <div class="copy">
                        <h2>Vibration?</h2>
                        <p>일반적으로 사람들은 진동을 단순한 떨림이나<br class="mobile-break"> 이상 현상에 의한 흔들림 정도로 인식합니다.</p>
                        <p>하지만 산업 현장에서 진동은 장치의 상태를<br class="mobile-break"> 파악할 수 있는 중요한 신호로 활용됩니다.</p>
                    </div>
                    <img class="split-image" src="{vib1_uri}" alt="Vibration illustration">
                </div>
            </div>
        </section>

        <section class="split-band gray-band">
            <div class="section-inner">
                <div class="split-grid">
                    <img class="split-image" src="{vib2_uri}" alt="FFT analysis illustration">
                    <div class="copy">
                        <h2 class="blue">Analysis?</h2>
                        <p>FFT(Fast Fourier Transform) 변환을 이용한 진동 분석은 단순히 이상 유무를 확인하는 것을 넘어, 이상의 정도와 원인을 분석할 수 있습니다.</p>
                        <p>이를 통해 결함에 대해 정확한 조치가 가능해질 뿐만 아니라, 결함이 발생하기 전 이상 징후를 미리 감지할 수 있습니다.</p>
                        <p>최근에는 AI 기술을 결합하여 장치의 상태를 더욱 구체적으로 진단하는 방향으로 발전하고 있습니다.</p>
                    </div>
                </div>
            </div>
        </section>

        <section id="fft-info" class="fft-intro">
            <div class="section-inner">
                <h2>Vibration Analysis (FFT)</h2>
                <img class="fft-image" src="{fft_uri}" alt="FFT transform diagram">
                <div class="fft-copy">
                    <p>FFT(Fast Fourier Transform) 란 시간에 따라 변하는 진동 신호를 주파수 성분으로 변환하는 분석 방법입니다.</p>
                    <p>이를 통해 복잡한 진동 신호 속에 어떤 주요 주파수 성분이 포함되어 있는지 확인할 수 있고 이의 분석을 통해 장치 상태의 정상 유무를 확인할 수 있습니다.</p>
                </div>
                <div class="cta-row">
                    <a class="cta-button" href="?page=fft" target="_self">실제 데이터를 업로드하여 FFT 변환을 직접 확인해보세요 &gt;</a>
                </div>
            </div>
        </section>

        <section id="cases" class="cases-band">
            <div class="section-inner">
                <h2>Cases</h2>
                <div class="case-card-grid">
                    <article class="case-card">
                        <img src="{motor_uri}" alt="Motor shaft angular misalignment">
                        <div class="case-card-body">
                            <h3>Motor shaft angular<br>misalignment</h3>
                            <p>모터 축 연결부의 틀어짐 정도에 따른 진동 측정</p>
                            <a class="round-arrow" href="?page=case1" target="_self" aria-label="Case1 보기">›</a>
                        </div>
                    </article>
                    <article class="case-card">
                        <img src="{bearing_uri}" alt="Bearing inner and outer ring defect">
                        <div class="case-card-body">
                            <h3>Bearing inner &amp; outer<br>ring defect</h3>
                            <p>베어링 내륜과 외륜 링의 결함에 따른 진동 측정</p>
                            <a class="round-arrow" href="?page=case2" target="_self" aria-label="Case2 보기">›</a>
                        </div>
                    </article>
                    <article class="case-card">
                        <img src="{wind_uri}" alt="Floating wind turbine defect">
                        <div class="case-card-body">
                            <h3>Floating wind turbine<br>defect</h3>
                            <p>부유식 풍력 발전기 날개의 편심 하중, 균열 그리고 체결 불량에 따른 진동 측정</p>
                            <a class="round-arrow" href="?page=case3" target="_self" aria-label="Case3 보기">›</a>
                        </div>
                    </article>
                </div>
            </div>
        </section>
    </main>
    """
    render_html(html)
    render_main_category_tracker()
    render_footer()


def render_fft_page() -> None:
    render_header("FFT transform")

    with st.form("fft_upload_form"):
        st.markdown("## Xlsx 또는 csv 파일을 업로드해주세요")
        uploaded_file = st.file_uploader(
            "파일",
            type=["csv", "xlsx"],
            label_visibility="visible",
        )
        sampling_rate_text = st.text_input(
            "샘플링 속도 (Hz)",
            value="1000",
            help="숫자를 직접 입력하세요. 예: 1000",
        )
        range_text = st.text_input("데이터 범위", value="A2-A100", help="예: A2-A145")
        st.caption("ex) A2-A100")
        submitted = st.form_submit_button("변환")

    with st.container(key="fft_plot_band"):
        if submitted:
            try:
                if uploaded_file is None:
                    raise ValueError("변환할 CSV 또는 XLSX 파일을 먼저 업로드해주세요.")
                try:
                    sampling_rate = float(sampling_rate_text.replace(",", "").strip())
                except ValueError as exc:
                    raise ValueError("샘플링 속도는 숫자로 직접 입력해주세요.") from exc
                values = read_uploaded_signal(uploaded_file, range_text)
                freqs, amplitudes = compute_fft(values, sampling_rate)
                table = top_frequency_table(freqs, amplitudes)

                plot_left, arrow_col, plot_right = st.columns([1, 0.13, 1], vertical_alignment="center")
                with plot_left:
                    st.pyplot(make_time_plot(values, sampling_rate), width="stretch")
                with arrow_col:
                    render_html('<div class="arrow-separator">→</div>')
                with plot_right:
                    st.pyplot(make_frequency_plot(freqs, amplitudes, "Amplitude - Frequency", True), width="stretch")
                st.markdown("### 상위 10개 주파수 table")
                st.dataframe(table, width="stretch", height=285)
            except Exception as exc:
                st.error(str(exc))
                render_empty_fft_area()
        else:
            render_empty_fft_area()
    render_footer()


def render_empty_fft_area() -> None:
    plot_left, arrow_col, plot_right = st.columns([1, 0.13, 1], vertical_alignment="center")
    with plot_left:
        render_html('<div class="status-note">변위-시간 그래프</div>')
    with arrow_col:
        render_html('<div class="arrow-separator">→</div>')
    with plot_right:
        render_html('<div class="status-note">진폭-주파수 그래프</div>')
    render_html('<div class="status-note" style="min-height: 180px; margin-top: 24px;">상위 10개 주파수 table</div>')


def motor_svg(angle: float) -> str:
    rotation = {0.0: 0, 0.4: -15, 0.8: -30}.get(float(angle), 0)
    svg = f"""
    <svg viewBox="0 0 760 260" role="img" aria-label="motor angular misalignment">
        <defs>
            <style>
                .motor-body {{ fill:#b8c7cb; stroke:#111923; stroke-width:6; }}
                .motor-cap {{ fill:#6ef1d3; stroke:#111923; stroke-width:6; }}
                .motor-line {{ stroke:#27343b; stroke-width:6; stroke-linecap:round; }}
                .shaft {{ fill:#777; stroke:#111923; stroke-width:5; }}
            </style>
        </defs>
        <g>
            <g transform="translate(64 54)">
                <rect class="shaft" x="-26" y="74" width="26" height="52" rx="9"/>
                <rect class="motor-cap" x="0" y="35" width="26" height="130" rx="12"/>
                <rect class="motor-body" x="24" y="48" width="214" height="104" rx="4"/>
                <rect class="motor-cap" x="238" y="35" width="26" height="130" rx="12"/>
                <rect class="motor-body" x="60" y="15" width="82" height="29" rx="2"/>
                <rect class="motor-body" x="56" y="156" width="150" height="31" rx="2"/>
                <line class="motor-line" x1="62" y1="73" x2="198" y2="73"/>
                <line class="motor-line" x1="62" y1="100" x2="198" y2="100"/>
                <line class="motor-line" x1="62" y1="127" x2="198" y2="127"/>
                <rect class="shaft" x="286" y="88" width="62" height="24" rx="2"/>
            </g>
            <rect class="shaft" x="352" y="132" width="56" height="24" rx="2"/>
            <g transform="translate(560 124) rotate({rotation}) translate(-560 -124)">
                <g transform="translate(432 54)">
                    <rect class="shaft" x="-48" y="88" width="62" height="24" rx="2"/>
                    <rect class="motor-cap" x="0" y="35" width="26" height="130" rx="12"/>
                    <rect class="motor-body" x="24" y="48" width="214" height="104" rx="4"/>
                    <rect class="motor-cap" x="238" y="35" width="26" height="130" rx="12"/>
                    <rect class="motor-body" x="60" y="15" width="82" height="29" rx="2"/>
                    <rect class="motor-body" x="56" y="156" width="150" height="31" rx="2"/>
                    <line class="motor-line" x1="62" y1="73" x2="198" y2="73"/>
                    <line class="motor-line" x1="62" y1="100" x2="198" y2="100"/>
                    <line class="motor-line" x1="62" y1="127" x2="198" y2="127"/>
                    <rect class="shaft" x="286" y="74" width="26" height="52" rx="9"/>
                </g>
            </g>
        </g>
    </svg>
    """
    return svg


def bearing_svg(defective: bool = False) -> str:
    cracks = ""
    if defective:
        cracks = """
        <path d="M89 71 l24 42 -18 -6 13 46 -35 -55 20 8z" fill="#111923"/>
        <path d="M253 64 l16 44 -16 -5 8 46 -29 -54 17 6z" fill="#111923"/>
        <path d="M274 199 l34 21 -20 8 32 29 -54 -17 18 -15z" fill="#111923"/>
        <path d="M157 124 l14 23 -12 -3 7 27 -22 -30 12 3z" fill="#111923"/>
        """
    svg = f"""
    <svg viewBox="0 0 360 330" role="img" aria-label="bearing defect">
        <defs>
            <style>
                .ring {{ fill:none; stroke:#0e1116; stroke-width:8; }}
                .outer-fill {{ fill:#cfd2d2; }}
                .race {{ fill:#85898b; stroke:#0e1116; stroke-width:7; }}
                .ball {{ fill:#d2d4d4; stroke:#0e1116; stroke-width:6; }}
            </style>
        </defs>
        <circle cx="180" cy="165" r="137" class="outer-fill"/>
        <circle cx="180" cy="165" r="137" class="ring"/>
        <circle cx="180" cy="165" r="103" class="race"/>
        <circle cx="180" cy="165" r="63" fill="#070b28" stroke="#0e1116" stroke-width="8"/>
        <circle cx="180" cy="165" r="77" fill="none" stroke="#d8dddd" stroke-width="8"/>
        <g>
            <circle class="ball" cx="180" cy="62" r="27"/>
            <circle class="ball" cx="253" cy="92" r="27"/>
            <circle class="ball" cx="284" cy="165" r="27"/>
            <circle class="ball" cx="253" cy="238" r="27"/>
            <circle class="ball" cx="180" cy="268" r="27"/>
            <circle class="ball" cx="107" cy="238" r="27"/>
            <circle class="ball" cx="76" cy="165" r="27"/>
            <circle class="ball" cx="107" cy="92" r="27"/>
        </g>
        <text x="180" y="21" text-anchor="middle" fill="#d8dddd" font-size="17" font-weight="700">외륜</text>
        <text x="180" y="171" text-anchor="middle" fill="#d8dddd" font-size="15" font-weight="700">내륜</text>
        {cracks}
    </svg>
    """
    return svg


def turbine_svg(mode: str = "normal") -> str:
    blade1 = "#f2f7ff"
    blade2 = "#f2f7ff"
    blade3 = "#f2f7ff"
    crack = ""
    mast_transform = ""
    base_transform = ""
    gap = ""
    if mode == "mass":
        blade1 = "#e02d3c"
    elif mode == "crack":
        crack = '<path d="M188 98 l18 31 -14 -4 7 35 -26 -44 13 4z" fill="#111923"/>'
    elif mode == "bolt":
        mast_transform = "rotate(-9 180 245)"
        base_transform = "translate(-19 8) rotate(-5 180 292)"
        gap = '<line x1="145" y1="286" x2="215" y2="286" stroke="#63f7cf" stroke-width="8" stroke-linecap="round"/>'
    svg = f"""
    <svg viewBox="0 0 360 345" role="img" aria-label="floating wind turbine defect">
        <defs>
            <style>
                .tower {{ fill:#eef6ff; stroke:#7d8aa6; stroke-width:7; stroke-linejoin:round; }}
                .blade {{ stroke:#7d8aa6; stroke-width:7; stroke-linejoin:round; }}
            </style>
        </defs>
        <g transform="{mast_transform}">
            <polygon class="tower" points="166,292 194,292 187,162 173,162"/>
            <circle cx="180" cy="153" r="18" fill="#dceafa" stroke="#7d8aa6" stroke-width="7"/>
            <polygon class="blade" points="179,134 174,28 196,26 190,137" fill="{blade1}"/>
            <polygon class="blade" points="164,162 58,214 49,195 156,142" fill="{blade2}"/>
            <polygon class="blade" points="196,162 296,219 283,236 185,174" fill="{blade3}"/>
            {crack}
        </g>
        {gap}
        <rect x="139" y="292" width="82" height="24" transform="{base_transform}" fill="#eef6ff" stroke="#7d8aa6" stroke-width="7"/>
    </svg>
    """
    return svg


def render_case_visual_start(label: str) -> None:
    render_header(label)
    render_html('<section class="case-visual"><div class="section-inner">')


def render_case_visual_end() -> None:
    render_html("</div></section>")


def render_svg_component(svg_markup: str, height: int = 330) -> None:
    html = f"""
        <style>
        html, body {{
            margin: 0;
            padding: 0;
            background: transparent;
            overflow: hidden;
        }}
        .case-svg-wrap {{
            width: 100%;
            height: {height}px;
            display: flex;
            align-items: center;
            justify-content: center;
        }}
        .case-svg-wrap svg {{
            width: 100%;
            height: 100%;
            display: block;
        }}
        </style>
        <div class="case-svg-wrap">{svg_markup}</div>
    """
    encoded = base64.b64encode(html.encode("utf-8")).decode("ascii")
    st.iframe(f"data:text/html;base64,{encoded}", height=height, width="stretch")


def render_case_image(image_name: str, alt: str, height: int = 330) -> None:
    image_uri = asset_uri(image_name)
    render_html(
        f"""
        <div class="case-image-wrap" style="height: {height}px;">
            <img src="{image_uri}" alt="{alt}">
        </div>
        """
    )


def render_motor_pair(angle: float) -> None:
    left_uri = asset_uri("motor_L.png")
    right_uri = asset_uri("motor_R.png")
    rotation = {0.0: 0, 0.4: -15, 0.8: -30}.get(float(angle), 0)
    render_html(
        f"""
        <div class="case-motor-scene">
            <img src="{left_uri}" alt="left motor">
            <img class="case-motor-right" src="{right_uri}" alt="right motor" style="transform: rotate({rotation}deg);">
        </div>
        """
    )


def render_case_comparison(
    normal_freq: np.ndarray,
    normal_amp: np.ndarray,
    abnormal_freq: np.ndarray | None,
    abnormal_amp: np.ndarray | None,
    abnormal_label: str,
    show_abnormal: bool = True,
) -> None:
    with st.container(key="case_plot_band"):
        left, arrow, right = st.columns([1, 0.13, 1], vertical_alignment="center")
        with left:
            st.pyplot(make_case_plot(normal_freq, normal_amp, "정상 상태 진폭-주파수 그래프"), width="stretch")
            st.dataframe(top_frequency_table(normal_freq, normal_amp), width="stretch", height=240)
        with arrow:
            render_html('<div class="arrow-separator">→</div>')
        with right:
            if show_abnormal and abnormal_freq is not None and abnormal_amp is not None:
                st.pyplot(make_case_plot(abnormal_freq, abnormal_amp, abnormal_label), width="stretch")
                st.dataframe(top_frequency_table(abnormal_freq, abnormal_amp), width="stretch", height=240)
            else:
                render_html('<div class="status-note">비정상 상태 영역</div>')


@st.fragment
def render_case1_interactive() -> None:
    angles = [0.0, 0.4, 0.8]
    if "case1_angle_index" not in st.session_state:
        st.session_state.case1_angle_index = 0
    current_index = int(st.session_state.case1_angle_index)
    current_angle = angles[current_index]

    with st.container(key="case_visual_band"):
        visual_col, control_col = st.columns([2.25, 0.75], vertical_alignment="center")
        with visual_col:
            render_motor_pair(current_angle)
        with control_col:
            with st.container(key="case1_angle_controls"):
                if st.button(" ", key="case1_angle_up", use_container_width=True):
                    st.session_state.case1_angle_index = min(current_index + 1, len(angles) - 1)
                    st.rerun(scope="fragment")
                render_html(f'<div class="case-control-number">{current_angle:.1f}°</div>')
                if st.button(" ", key="case1_angle_down", use_container_width=True):
                    st.session_state.case1_angle_index = max(current_index - 1, 0)
                    st.rerun(scope="fragment")

    normal_freq, normal_amp = get_case_columns("shaft_frq", "shaft_hlth")
    if current_angle == 0.4:
        abnormal_freq, abnormal_amp = get_case_columns("shaft_frq", "shaft_0.4")
        render_case_comparison(normal_freq, normal_amp, abnormal_freq, abnormal_amp, "0.4도 비정상 상태 진폭-주파수 그래프")
    elif current_angle == 0.8:
        abnormal_freq, abnormal_amp = get_case_columns("shaft_frq", "shaft_0.8")
        render_case_comparison(normal_freq, normal_amp, abnormal_freq, abnormal_amp, "0.8도 비정상 상태 진폭-주파수 그래프")
    else:
        render_case_comparison(normal_freq, normal_amp, None, None, "비정상 상태 진폭-주파수 그래프", show_abnormal=False)


def render_case1_page() -> None:
    render_header("Motor shaft angular misalignment")
    render_case1_interactive()
    render_footer()


def render_case2_page() -> None:
    render_header("Bearing inner & outer ring defect")
    with st.container(key="case_visual_band"):
        render_case_image("bearing_crack.png", "bearing inner and outer defect", height=330)

    normal_freq, normal_amp = get_case_columns("bearing_frq", "bearing_hlth")
    abnormal_freq, abnormal_amp = get_case_columns("bearing_frq", "bearing_unhlth")
    render_case_comparison(normal_freq, normal_amp, abnormal_freq, abnormal_amp, "비정상 상태 진폭-주파수 그래프")
    render_footer()


@st.fragment
def render_case3_interactive() -> None:
    mode_to_label = {
        "mass": "편심 하중",
        "crack": "균열",
        "bolt": "체결 불량",
    }
    mode_to_column = {
        "mass": "wind_m",
        "crack": "wind_c",
        "bolt": "wind_b",
    }
    mode_to_image = {
        "mass": "mass.png",
        "crack": "crack.png",
        "bolt": "bolt.png",
    }
    if "case3_mode" not in st.session_state or st.session_state.case3_mode not in mode_to_label:
        st.session_state.case3_mode = "mass"
    current_mode = st.session_state.case3_mode

    with st.container(key="case_visual_band"):
        visual_col, buttons_col = st.columns([2.25, 0.75], vertical_alignment="center")
        with visual_col:
            render_case_image(mode_to_image[current_mode], mode_to_label[current_mode], height=340)
        with buttons_col:
            modes = list(mode_to_label.items())
            for index, (mode, label) in enumerate(modes):
                button_label = f"{label} ✓" if mode == current_mode else label
                if st.button(button_label, key=f"case3_mode_{mode}", use_container_width=True):
                    st.session_state.case3_mode = mode
                    st.rerun(scope="fragment")
                if index < len(modes) - 1:
                    render_html('<div class="case3-button-gap" aria-hidden="true"></div>')

    normal_freq, normal_amp = get_case_columns("wind_frq", "wind_hlth")
    abnormal_freq, abnormal_amp = get_case_columns("wind_frq", mode_to_column[current_mode])
    render_case_comparison(
        normal_freq,
        normal_amp,
        abnormal_freq,
        abnormal_amp,
        f"{mode_to_label[current_mode]} 비정상 상태 진폭-주파수 그래프",
    )


def render_case3_page() -> None:
    render_header("Floating wind turbine defect")
    render_case3_interactive()
    render_footer()


def render_references_page() -> None:
    render_header("References")
    html = """
    <section class="references-panel">
        <div class="section-inner">
            <ul>
                <li>Bourdalos, D., Korolis, J., &amp; Sakellariou, J. (2026). <em>UPATRAS Floating Wind Turbine Vibration Dataset for Damage Diagnosis under Varying Wind Conditions</em> (Version 1) [Data set]. Mendeley Data. <a href="https://doi.org/10.17632/zmbjjg9kbj.1" target="_blank">https://doi.org/10.17632/zmbjjg9kbj.1</a></li>
                <li>Kechik, D., Aslamov, Y., &amp; Davydov, I. (2021). <em>Shaft Angular Misalignment Dataset</em> (Version 1) [Data set]. Mendeley Data. <a href="https://doi.org/10.17632/kf96jx9dzf.1" target="_blank">https://doi.org/10.17632/kf96jx9dzf.1</a></li>
                <li>Kechik, D., Aslamov, Y., &amp; Davydov, I. (2020). <em>Bearing 6213 Norm/OR Dataset</em> (Version 1) [Data set]. Mendeley Data. <a href="https://doi.org/10.17632/fbf6y8m4mv.1" target="_blank">https://doi.org/10.17632/fbf6y8m4mv.1</a></li>
            </ul>
        </div>
    </section>
    <div class="page-spacer"></div>
    """
    render_html(html)
    render_footer()


def render_missing_assets_warning() -> None:
    required = [
        "background.png",
        "logo.png",
        "about_me.png",
        "man_with_analysis_device.png",
        "about_vibration_1.png",
        "about_vibration_2.png",
        "fft_transform.png",
        "motor_misalignment.jpg",
        "bearing.jpeg",
        "wind_turbine.jpg",
        "vib_data.xlsx",
    ]
    missing = [name for name in required if not (ASSET_DIR / name).exists()]
    if missing:
        st.warning("asset 폴더에 다음 파일이 필요합니다: " + ", ".join(missing))


def main() -> None:
    inject_css()
    render_missing_assets_warning()
    page = get_page()

    if page == "fft":
        render_fft_page()
    elif page == "case1":
        render_case1_page()
    elif page == "case2":
        render_case2_page()
    elif page == "case3":
        render_case3_page()
    elif page == "references":
        render_references_page()
    else:
        render_main_page()


if __name__ == "__main__":
    main()
