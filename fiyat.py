import streamlit as st
import pandas as pd
import os

st.set_page_config(page_title="Akaryakıt Raporlama Sistemi", layout="wide")
st.title("⛽ Kurumsal Akaryakıt Analiz Paneli")

# --- SABİT DOSYA AYARI ---
# Klasörde bu isimde bir dosya varsa otomatik onu açar
DEFAULT_FILE_PATH = "varsayilan_veri.xlsx"

# --- 1. VERİ YÜKLEME MANTIĞI ---
# Önce kullanıcı dosya yüklemiş mi ona bakalım
uploaded_file = st.file_uploader("📂 Güncel Veri Yükle (Yüklemezseniz sistemdeki son rapor gösterilir)",
                                 type=["xlsx", "xls"])

df = None
veri_kaynagi = ""

if uploaded_file is not None:
    # Kullanıcı dosya yükledi, onu kullan
    try:
        df = pd.read_excel(uploaded_file)
        veri_kaynagi = "Kullanıcı Yüklemesi"
        st.success("✅ Sizin yüklediğiniz dosya analiz ediliyor.")
    except Exception as e:
        st.error(f"Dosya okunurken hata oluştu: {e}")

elif os.path.exists(DEFAULT_FILE_PATH):
    # Kullanıcı yüklemedi ama klasörde sabit dosya var, onu kullan
    try:
        df = pd.read_excel(DEFAULT_FILE_PATH)
        veri_kaynagi = "Sistem Varsayılan Raporu"
        st.info(f"ℹ️ Şu an sistemdeki kayıtlı raporu (**{DEFAULT_FILE_PATH}**) görüntülüyorsunuz.")
    except Exception as e:
        st.error(f"Varsayılan dosya okunurken hata oluştu: {e}")

else:
    # Ne kullanıcı yükledi ne de sabit dosya var
    st.warning("⚠️ Lütfen bir Excel dosyası yükleyin veya klasöre 'varsayilan_veri.xlsx' adında bir dosya ekleyin.")

# --- 2. ANALİZ KODLARI (EĞER DF DOLUYSA ÇALIŞIR) ---
if df is not None:
    # --- VERİ TEMİZLEME & HAZIRLIK ---
    df['Fiyat'] = pd.to_numeric(df['Fiyat'], errors='coerce')
    df['Tarih'] = pd.to_datetime(df['Tarih'], dayfirst=True, errors='coerce')
    df['Tarih_Str'] = df['Tarih'].dt.strftime('%d.%m.%Y')

    # Temizle ve Sırala
    df = df.dropna(subset=['Tarih', 'Fiyat'])
    df = df.sort_values('Tarih')

    # --- SOL MENÜ ---
    with st.sidebar:
        st.markdown(f"**Veri Kaynağı:** {veri_kaynagi}")
        st.header("Segment Seçimi")
        yakitlar = df['Yakıt Tipi'].unique()
        secilen_yakit = st.radio("Bir Yakıt Tipi Seç:", yakitlar)
        st.markdown("---")
        st.info(f"Seçili: **{secilen_yakit}**")

    # --- SEKMELER ---
    tab1, tab2 = st.tabs(["🏙️ Şehir Bazlı Analiz", "⭐ MOİL & TOTAL Matrisi"])

    # ==========================================
    # SEKME 1: ŞEHİR BAZLI DETAY + RENKLİ YAZI
    # ==========================================
    with tab1:
        st.subheader(f"{secilen_yakit} - Şehir ve Tarih Analizi")

        # İl Seçimi
        sehirler = sorted(df['İl'].astype(str).unique())
        secilen_sehir = st.selectbox("Bir Şehir Seç:", sehirler)

        # Veriyi Süz
        df_sehir = df[(df['İl'] == secilen_sehir) & (df['Yakıt Tipi'] == secilen_yakit)].copy()

        if not df_sehir.empty:
            mevcut_tarihler_dt = sorted(df_sehir['Tarih'].unique())
            mevcut_tarihler_str = [pd.to_datetime(t).strftime('%d.%m.%Y') for t in mevcut_tarihler_dt]

            # Tarih Seçimi
            st.write("---")
            col1, col2 = st.columns(2)
            baslangic_str = col1.selectbox("Başlangıç Tarihi:", mevcut_tarihler_str, index=0)
            bitis_str = col2.selectbox("Bitiş Tarihi:", mevcut_tarihler_str, index=len(mevcut_tarihler_str) - 1)

            baslangic_dt = pd.to_datetime(baslangic_str, dayfirst=True)
            bitis_dt = pd.to_datetime(bitis_str, dayfirst=True)

            # Süzme
            mask_tarih = (df_sehir['Tarih'] >= baslangic_dt) & (df_sehir['Tarih'] <= bitis_dt)
            df_sehir_filtered = df_sehir.loc[mask_tarih]

            if df_sehir_filtered.empty:
                st.warning("Seçilen tarih aralığında veri yok.")
            else:
                # Pivot Tablo
                df_pivot = df_sehir_filtered.pivot_table(index="Marka", columns="Tarih_Str", values="Fiyat")

                # İndex reset (Marka sütun olsun diye)
                df_pivot = df_pivot.reset_index()

                # Sütun Sıralama
                araliktaki_tarihler = [t for t in mevcut_tarihler_dt if baslangic_dt <= t <= bitis_dt]
                tarih_cols = [t.strftime('%d.%m.%Y') for t in araliktaki_tarihler]
                final_cols = ['Marka'] + tarih_cols

                valid_cols = [c for c in final_cols if c in df_pivot.columns]
                df_pivot = df_pivot[valid_cols]

                # Değişim Hesapla
                if len(valid_cols) > 2:
                    ilk_fiyat_col = valid_cols[1]
                    son_fiyat_col = valid_cols[-1]
                    df_pivot['DEĞİŞİM (TL)'] = df_pivot[son_fiyat_col] - df_pivot[ilk_fiyat_col]
                else:
                    df_pivot['DEĞİŞİM (TL)'] = 0


                # --- RENKLENDİRME ---
                def highlight_full_row(row):
                    marka = str(row['Marka']).upper()

                    if 'MOİL' in marka:
                        # Mavi Arkaplan, Koyu Mavi Yazı, Kalın
                        return ['background-color: #dbeafe; color: #00008B; font-weight: bold'] * len(row)
                    elif 'TOTAL' in marka:
                        # Turuncu Arkaplan, Koyu Turuncu Yazı, Kalın
                        return ['background-color: #ffedd5; color: #d94e00; font-weight: bold'] * len(row)
                    return [''] * len(row)


                def color_change_col(val):
                    if pd.isna(val): return ''
                    if val > 0: return 'color: red; font-weight: bold'
                    if val < 0: return 'color: green; font-weight: bold'
                    return 'color: gray'


                st.write(f"📋 **{baslangic_str}** - **{bitis_str}** | Veri Kaynağı: {veri_kaynagi}")

                st.dataframe(
                    df_pivot.style
                    .apply(highlight_full_row, axis=1)
                    .applymap(color_change_col, subset=['DEĞİŞİM (TL)'])
                    .format(precision=2, na_rep="-"),
                    use_container_width=True
                )
        else:
            st.warning("Veri yok.")

    # ==========================================
    # SEKME 2: MATRİS (Tüm İller)
    # ==========================================
    with tab2:
        st.subheader(f"Tüm İller Matrisi ({secilen_yakit})")
        secilen_marka_ana = st.radio("Marka Seç:", ["MOİL", "TOTAL"], horizontal=True)

        mask_yakit = df['Yakıt Tipi'] == secilen_yakit
        mask_marka = df['Marka'].str.upper().str.contains(secilen_marka_ana)
        df_ozel = df[mask_yakit & mask_marka].copy()

        if not df_ozel.empty:
            df_matris = df_ozel.pivot_table(index="İl", columns="Tarih_Str", values="Fiyat",
                                            aggfunc='mean').reset_index()

            # Sıralama
            mevcut_tarihler = sorted(df_ozel['Tarih'].unique())
            sirali_tarih_cols = [pd.to_datetime(t).strftime('%d.%m.%Y') for t in mevcut_tarihler]
            final_cols_matris = ['İl'] + sirali_tarih_cols

            valid_cols_matris = [c for c in final_cols_matris if c in df_matris.columns]
            df_matris = df_matris[valid_cols_matris]

            # Fark Hesapla
            if len(valid_cols_matris) > 2:
                df_matris['TOPLAM DEĞİŞİM (TL)'] = df_matris[valid_cols_matris[-1]] - df_matris[valid_cols_matris[1]]


            # Matris Boyama
            def highlight_matrix_full(s):
                if secilen_marka_ana == "MOİL":
                    return ['background-color: #dbeafe; color: #00008B; font-weight: bold'] * len(s)
                else:
                    return ['background-color: #ffedd5; color: #d94e00; font-weight: bold'] * len(s)


            st.dataframe(
                df_matris.style
                .apply(highlight_matrix_full, axis=0)
                .applymap(color_change_col,
                          subset=['TOPLAM DEĞİŞİM (TL)'] if 'TOPLAM DEĞİŞİM (TL)' in df_matris.columns else None)
                .format(precision=2, na_rep="-"),
                use_container_width=True,
                height=800
            )
        else:
            st.warning("Veri yok.")