def compose_bullets(context: dict, lang: str = "ms") -> str:
    q = context.get("quarter","-")
    ymi = context.get("YMI")
    yu = context.get("youth_unemp_rate")
    su = context.get("skills_underemp_rate")
    tu = context.get("time_underemp_rate")
    u  = context.get("u_rate")
    cpi= context.get("cpi_index")

    if lang == "ms":
        lines = [f"• Pada {q}, YMI: {float(ymi):.1f} (0–100, lebih tinggi = lebih teruk)."]
        if yu is not None: lines.append(f"• Pengangguran belia: {float(yu):.1f}%.")
        if su is not None: lines.append(f"• Kekurangan guna tenaga (kemahiran): {float(su):.1f}%.")
        if tu is not None: lines.append(f"• Kekurangan guna tenaga (masa): {float(tu):.1f}%.")
        if u is not None:  lines.append(f"• Kadar pengangguran keseluruhan: {float(u):.1f}%.")
        if cpi is not None:lines.append(f"• Indeks CPI (tekanan kos sara hidup): {float(cpi):.1f}.")
        lines.append("• Fokus polisi: kurangkan pengangguran belia; sejajarkan latihan TVET/industri; pantau CPI negeri.")
    else:
        lines = [f"• In {q}, YMI: {float(ymi):.1f} (0–100; higher = worse)."]
        if yu is not None: lines.append(f"• Youth unemployment: {float(yu):.1f}%.")
        if su is not None: lines.append(f"• Skills underemployment: {float(su):.1f}%.")
        if tu is not None: lines.append(f"• Time underemployment: {float(tu):.1f}%.")
        if u is not None:  lines.append(f"• Overall unemployment: {float(u):.1f}%.")
        if cpi is not None:lines.append(f"• CPI index (cost pressure): {float(cpi):.1f}.")
        lines.append("• Policy focus: reduce youth unemployment; align TVET/industry; monitor state CPI.")
    return "\n".join(lines)
