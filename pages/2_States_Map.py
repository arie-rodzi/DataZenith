# ---- Try choropleth, else fallback with diagnostics ----
geojson_file = None
upload_gj = st.file_uploader("Or upload a Malaysia states GeoJSON", type=["geojson","json"], key="gj_upload")
if upload_gj is not None:
    import json
    geojson_file = json.load(upload_gj)
else:
    try:
        with open("assets/malaysia_states.geojson", "r", encoding="utf-8") as f:
            import json
            geojson_file = json.load(f)
    except Exception as e:
        st.warning(f"GeoJSON not found/invalid at assets/malaysia_states.geojson ({e}). Showing bar chart fallback.")

if geojson_file is not None and "features" in geojson_file:
    # Inspect available property keys
    prop_keys = sorted(set(k for feat in geojson_file["features"] for k in feat.get("properties", {}).keys()))
    st.caption(f"GeoJSON property keys detected: {prop_keys}")

    # Try common feature id keys
    candidate_keys = ["properties.name", "properties.NAME_1", "properties.state", "properties.negeri"]
    used_key = None
    for k in candidate_keys:
        # verify key exists on first feature
        p = k.split(".", 1)[1]  # e.g. 'name'
        if p in geojson_file["features"][0].get("properties", {}):
            used_key = k
            break
    if used_key is None:
        st.warning("Couldn't find a suitable feature id key (tried name/NAME_1/state/negeri). Falling back to bar chart.")
    else:
        # Optional: harmonize state names to match GeoJSON
        name_fix = {
            "Pulau Pinang": "Penang",          # if needed
            "W.P. Kuala Lumpur": "Kuala Lumpur",
            "W.P. Labuan": "Labuan",
            "W.P. Putrajaya": "Putrajaya",
            # add more if your data uses different variants
        }
        if "state" in d.columns:
            d["state"] = d["state"].replace(name_fix)

        try:
            fig = px.choropleth(
                d,
                geojson=geojson_file,
                featureidkey=used_key,
                locations="state",
                color=metric,
                color_continuous_scale="Viridis",
                projection="mercator",
            )
            fig.update_geos(fitbounds="locations", visible=False)
            st.plotly_chart(fig, use_container_width=True)
        except Exception as e:
            st.warning(f"Choropleth failed ({e}). Showing bar chart instead.")
            index_col = "state" if "state" in d.columns else d.columns[0]
            d = d.sort_values(metric, ascending=False)
            st.bar_chart(d.set_index(index_col)[metric])
else:
    # Fallback bar chart
    index_col = "state" if "state" in d.columns else d.columns[0]
    if metric not in d.columns:
        st.error(f"Metric '{metric}' not found in data columns {list(d.columns)}.")
        st.stop()
    d = d.sort_values(metric, ascending=False)
    st.bar_chart(d.set_index(index_col)[metric])
