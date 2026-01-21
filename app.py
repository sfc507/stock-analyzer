import streamlit as st
import pandas as pd

# ==========================================
# 0. 全域設定 (Global Settings)
# ==========================================
# 您可以在這裡直接修改字串，網頁標題會同步更新
PAGE_TITLE = "台股觀測站：成交值與營收綜合分析" 

st.set_page_config(page_title=PAGE_TITLE, layout="wide")

# ==========================================
# 區域 A: 資料清洗與處理模組
# ==========================================

def clean_stock_id(series):
    """強力清洗代號: 移除 = 和 " 符號"""
    return series.astype(str).str.replace(r'[="]', '', regex=True).str.strip()

def clean_number(series):
    """清洗數字: 移除千分位逗號"""
    return series.astype(str).str.replace(',', '', regex=False)

def process_industry_data(df):
    """處理產業資料 (查表用)"""
    target_cols = ['代號', '名稱', '產業別']
    if not set(target_cols).issubset(df.columns):
        return None, f"產業檔缺少欄位: {set(target_cols) - set(df.columns)}"
    
    df_clean = df[target_cols].copy()
    df_clean['代號'] = clean_stock_id(df_clean['代號'])
    # 移除產業為空的資料 (嚴格模式)
    df_clean = df_clean.dropna(subset=['產業別'])
    return df_clean, None

def process_revenue_data(rev_df, ind_df):
    """
    處理營收排行 (Tab 1 使用)
    邏輯: 
    1. 改用 [單月營收年增(%)]
    2. 剔除特定產業
    3. 取 Top 50
    """
    # 【修改 1】欄位改成 單月營收年增(%)
    target_col = '單月營收年增(%)'
    req_cols = ['代號', '名稱', target_col]
    
    if not set(req_cols).issubset(rev_df.columns):
        return None, f"營收檔缺少欄位: {set(req_cols) - set(rev_df.columns)}"

    df_clean = rev_df[req_cols].copy()
    df_clean['代號'] = clean_stock_id(df_clean['代號'])
    df_clean[target_col] = clean_number(df_clean[target_col])
    df_clean[target_col] = pd.to_numeric(df_clean[target_col], errors='coerce').fillna(-999)

    # 合併產業
    merged_df = pd.merge(df_clean, ind_df[['代號', '產業別']], on='代號', how='left')
    merged_df = merged_df.dropna(subset=['產業別']) # 剔除查不到產業的

    # 產業過濾
    exclude_industries = ['建材營造', '建材營造業', '金融保險', '金融保險業', '金控業', '銀行業', '證券業', '通信網路業']
    filter_mask = ~merged_df['產業別'].isin(exclude_industries)
    filtered_df = merged_df[filter_mask].copy()

    # 排序
    final_df = filtered_df.sort_values(by=target_col, ascending=False).head(50)
    return final_df, None

def process_value_data(df):
    """處理成交值排行"""
    col_map = {c: c for c in df.columns if '成交' in c and '百萬' in c}
    target_val_col = list(col_map.values())[0] if col_map else '成交額(百萬)'
    
    req_cols = ['代號', '名稱', target_val_col]
    if not set(req_cols).issubset(df.columns):
        return None, f"成交值檔缺少欄位: {req_cols}"
    
    df_clean = df[req_cols].copy()
    df_clean['代號'] = clean_stock_id(df_clean['代號'])
    df_clean[target_val_col] = clean_number(df_clean[target_val_col])
    df_clean[target_val_col] = pd.to_numeric(df_clean[target_val_col], errors='coerce').fillna(0)
    
    # 換算億
    df_clean['成交額(億)'] = df_clean[target_val_col] / 100
    
    # 排序 (取出全部排序好的資料，不只 50，方便後續取 20 或更多)
    df_result = df_clean.sort_values(by='成交額(億)', ascending=False)
    
    return df_result[['代號', '名稱', '成交額(億)']], None

def get_raw_revenue_map(rev_df):
    """
    【新增模組】取得乾淨的營收對照表 (不篩選，只清洗)
    用途: 讓成交值表可以由代號查到營收
    """
    target_col = '單月營收年增(%)'
    req_cols = ['代號', target_col] # 只需要代號跟數值
    
    if not set(req_cols).issubset(rev_df.columns):
        return None
    
    df_clean = rev_df[req_cols].copy()
    df_clean['代號'] = clean_stock_id(df_clean['代號'])
    df_clean[target_col] = clean_number(df_clean[target_col])
    # 這裡不填 -999，保留 NaN 以便知道原本沒資料
    df_clean[target_col] = pd.to_numeric(df_clean[target_col], errors='coerce') 
    
    return df_clean

def load_csv_safe(uploaded_file):
    try:
        return pd.read_csv(uploaded_file, encoding='utf-8')
    except UnicodeDecodeError:
        uploaded_file.seek(0)
        return pd.read_csv(uploaded_file, encoding='big5')

# ==========================================
# 區域 B: 主程式介面
# ==========================================

st.title(f"📈 {PAGE_TITLE}")
st.caption("版本: V4 | 修改: 單月營收年增、可變標題、新增 Top 20 綜合表")
st.markdown("---")

col1, col2, col3 = st.columns(3)
with col1:
    file_rev = st.file_uploader("1. 上傳營收 CSV", key="rev")
with col2:
    file_val = st.file_uploader("2. 上傳成交值 CSV", key="val")
with col3:
    file_ind = st.file_uploader("3. 上傳產業 CSV", key="ind")

if file_rev and file_val and file_ind:
    st.divider()
    
    try:
        # 讀檔
        raw_rev = load_csv_safe(file_rev)
        raw_val = load_csv_safe(file_val)
        raw_ind = load_csv_safe(file_ind)

        # 1. 處理基礎資料
        df_ind, err_ind = process_industry_data(raw_ind)
        
        if df_ind is not None:
            # 2. 產生各自的排行表
            df_rev_top50, err_rev = process_revenue_data(raw_rev, df_ind)
            df_val_sorted, err_val = process_value_data(raw_val) # 這裡拿到全部排序

            # 3. 【新增需求】產生 "成交值 Top 20 + 營收 + 產業" 綜合表
            if df_val_sorted is not None:
                # A. 取出成交值前 20 名
                df_top20_mix = df_val_sorted.head(20).copy()
                
                # B. 準備乾淨的營收資料來查表
                raw_rev_clean = get_raw_revenue_map(raw_rev)
                
                # C. 合併營收 (Left Join)
                if raw_rev_clean is not None:
                    df_top20_mix = pd.merge(df_top20_mix, raw_rev_clean, on='代號', how='left')
                
                # D. 合併產業 (Left Join)
                df_top20_mix = pd.merge(df_top20_mix, df_ind[['代號', '產業別']], on='代號', how='left')

            # 錯誤顯示
            if err_rev: st.error(err_rev)
            if err_val: st.error(err_val)

            # 4. 顯示三個分頁
            if df_rev_top50 is not None and df_val_sorted is not None:
                
                tab1, tab2, tab3 = st.tabs(["🏆 成交熱門 Top 20 (綜合)", "📊 營收飆股 (單月年增)", "💰 成交值排行 (純清單)"])
                
                with tab1:
                    st.subheader("成交值前 20 名：附加營收與產業資訊")
                    st.caption("邏輯：取成交值最高前 20 檔 -> 加入單月營收年增 -> 加入產業別")
                    # 格式化顯示：營收年增率顯示 2 位小數，成交額顯示 2 位小數
                    st.dataframe(
                        df_top20_mix.style.format({
                            '成交額(億)': '{:.2f}', 
                            '單月營收年增(%)': '{:.2f}%'
                        }), 
                        use_container_width=True
                    )
                    
                with tab2:
                    st.subheader("營收年增排行 Top 50")
                    st.caption("條件：已剔除特定產業，依 [單月營收年增] 排序")
                    st.dataframe(df_rev_top50, use_container_width=True)
                    
                with tab3:
                    st.subheader("成交值排行 Top 50")
                    st.dataframe(df_val_sorted.head(50), use_container_width=True)
        else:
            st.error(err_ind)

    except Exception as e:
        st.error(f"程式執行錯誤: {e}")
        