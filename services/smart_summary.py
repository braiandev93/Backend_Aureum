import yfinance as yf

def generate_summary(symbol, scores, info):
    summary = []

    sector = info.get("sector")
    industry = info.get("industry")
    long_name = info.get("longName")

    # --- 1. Sector e industria ---
    if sector and industry:
        summary.append(
            f"La empresa opera en el sector {sector.lower()}, dentro de la industria {industry.lower()}."
        )
    elif sector:
        summary.append(f"La empresa pertenece al sector {sector.lower()}.")
    elif industry:
        summary.append(f"La empresa forma parte de la industria {industry.lower()}.")

    # --- 2. IA1 – Técnico ---
    ia1 = scores["ia1"]
    if ia1 > 0.75:
        summary.append("Los indicadores técnicos muestran fortaleza reciente en el movimiento del precio.")
    elif ia1 > 0.55:
        summary.append("Los indicadores técnicos reflejan un comportamiento estable en el precio.")
    else:
        summary.append("Los indicadores técnicos muestran señales de debilidad en el movimiento del precio.")

    # --- 3. IA2 – Valuación relativa ---
    ia2 = scores["ia2"]
    if ia2 > 0.75:
        summary.append("La valuación relativa se encuentra en niveles favorables respecto a su historial.")
    elif ia2 > 0.55:
        summary.append("La valuación relativa se mantiene en niveles moderados.")
    else:
        summary.append("La valuación relativa indica que el precio podría estar por encima de su promedio histórico.")

    # --- 4. IA3 – ML ---
    ia3 = scores["ia3"]
    if ia3 > 0.75:
        summary.append("Los modelos estadísticos detectan señales positivas en el corto plazo.")
    elif ia3 > 0.55:
        summary.append("Los modelos estadísticos muestran un comportamiento neutral en el corto plazo.")
    else:
        summary.append("Los modelos estadísticos detectan señales de riesgo en el corto plazo.")

    # --- 5. IA4 – Salud financiera ---
    ia4 = scores["ia4"]
    if ia4 > 0.75:
        summary.append("Los ratios financieros reflejan una estructura sólida y estable.")
    elif ia4 > 0.55:
        summary.append("Los ratios financieros muestran una situación equilibrada.")
    else:
        summary.append("Los ratios financieros indican presión en la estructura de capital.")

    # --- 6. IA5 – Reputación / Sentimiento ---
    ia5 = scores["ia5"]
    if ia5 > 0.75:
        summary.append("El sentimiento del mercado hacia la empresa es mayormente positivo.")
    elif ia5 > 0.55:
        summary.append("El sentimiento del mercado se mantiene estable.")
    else:
        summary.append("El sentimiento del mercado refleja cautela debido a noticias recientes.")

    # --- 7. IA6 – Outlook del mercado ---
    ia6 = scores["ia6"]
    if ia6 > 0.75:
        summary.append("El contexto del mercado y las proyecciones del sector son favorables.")
    elif ia6 > 0.55:
        summary.append("El contexto del mercado muestra estabilidad en el sector.")
    else:
        summary.append("El entorno del mercado presenta incertidumbre para esta industria.")

    return summary
