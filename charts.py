"""Builds the Plotly figures for the chart types chosen by visualization_selector."""

import numbers

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from agent.nodes import profile_dataframe

BLUE = "#7B93FF"      # accent
GOLD = "#E8B65A"      # highlight
INK = "#09090B"
PALETTE = [BLUE, GOLD, "#4FC1E9", "#A78BFA", "#3DD68C", "#FF8A65", "#9AA4B2", "#F472B6", "#5B6CF0", "#C08A2E"]
BG = "rgba(0,0,0,0)"

CHART_TITLES_HE = {
    "bar": "השוואה בעמודות",
    "line": "מגמה לאורך זמן",
    "pie": "התפלגות באחוזים",
    "histogram": "התפלגות ערכים",
    "scatter": "קשר בין שני מדדים",
    "heatmap": "מפת חום",
}


def _pretty(col) -> str:
    return str(col).replace("_", " ").title()


def _style(fig: go.Figure, title: str) -> go.Figure:
    fig.update_layout(
        title={"text": title, "x": 0.5, "xanchor": "center", "font": {"size": 13, "color": "#EDEDF0"}},
        paper_bgcolor=BG, plot_bgcolor=BG,
        font={"family": "IBM Plex Sans Hebrew, Heebo, sans-serif", "color": "#686873", "size": 12},
        margin={"l": 8, "r": 8, "t": 40, "b": 8},
        height=320,
        legend={"orientation": "h", "y": -0.16, "x": 0.5, "xanchor": "center", "font": {"color": "#A0A0AB", "size": 12}},
        colorway=PALETTE,
        hoverlabel={"bgcolor": "#17171B", "bordercolor": "#2C2C33",
                    "font": {"family": "IBM Plex Sans Hebrew, sans-serif", "color": "#EDEDF0", "size": 13}},
        bargap=0.35,
    )
    axis = dict(zeroline=False, linecolor="#222228", tickfont={"color": "#686873", "size": 11},
                title_font={"color": "#686873", "size": 11}, showspikes=False)
    fig.update_xaxes(showgrid=False, **axis)
    fig.update_yaxes(gridcolor="#1E1E24", griddash="dot", showline=False, **axis)
    return fig


def _empty(title: str, msg: str = "אין מספיק נתונים לגרף זה") -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(text=msg, showarrow=False, font={"size": 13, "color": "#686873"})
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    return _style(fig, title)


def _single_value(df: pd.DataFrame, title: str) -> go.Figure:
    col = df.columns[0]
    val = df.iloc[0, 0]
    if isinstance(val, numbers.Number):
        fig = go.Figure(go.Indicator(mode="number", value=float(val),
                                     number={"font": {"color": GOLD, "size": 56}, "valueformat": ",.0f"},
                                     title={"text": _pretty(col), "font": {"color": "#E5E7EB"}}))
    else:
        return _empty(title, f"{_pretty(col)}: {val}")
    return _style(fig, title)


def build_chart(df: pd.DataFrame, chart_type: str) -> go.Figure:
    title = CHART_TITLES_HE.get(chart_type, chart_type)
    if df is None or df.empty:
        return _empty(title, "אין תוצאות")
    if df.shape == (1, 1):
        return _single_value(df, title)

    p = profile_dataframe(df)
    dates, nums, cats = p["date_cols"], p["numeric_cols"], p["cat_cols"]
    # x-axis label for "per item" charts: first categorical, else first date column
    label = cats[0] if cats else (dates[0] if dates else None)
    y = nums[0] if nums else None

    try:
        if chart_type == "line":
            x = dates[0] if dates else (label or df.index.name or "index")
            data = df.sort_values(x) if x in df.columns else df.reset_index()
            ys = nums[:3] if nums else None
            if not ys:  # no numeric column -> count rows per x
                data = data.groupby(x).size().reset_index(name="count")
                ys = ["count"]
            color = cats[0] if cats and len(ys) == 1 and p["n_unique_cat"][cats[0]] <= 10 else None
            fig = px.line(data, x=x, y=ys if color is None else ys[0], color=color, markers=True,
                          labels={c: _pretty(c) for c in data.columns})
            fig.update_traces(line={"width": 2.4, "shape": "spline", "smoothing": 0.6}, marker={"size": 5})
            return _style(fig, f"{title}: {_pretty(ys[0])}")

        if chart_type == "bar":
            if label is None:
                return _empty(title)
            if y is None:
                data = df[label].value_counts().reset_index()
                data.columns = [label, "count"]
                y_col = "count"
            else:
                data = df.groupby(label, as_index=False)[y].sum()
                y_col = y
            data = data.sort_values(y_col, ascending=False).head(20)
            fig = px.bar(data, x=label, y=y_col, text_auto=".3~s",
                         labels={label: _pretty(label), y_col: _pretty(y_col)},
                         color_discrete_sequence=[BLUE])
            fig.update_traces(marker_line_width=0, marker_cornerradius=5, textposition="outside", cliponaxis=False,
                              textfont={"color": "#A0A0AB", "size": 11})
            return _style(fig, f"{title}: {_pretty(y_col)}")

        if chart_type == "pie":
            if label is None:
                return _empty(title)
            if y is None:
                data = df[label].value_counts().reset_index()
                data.columns = [label, "count"]
                y_col = "count"
            else:
                data = df.groupby(label, as_index=False)[y].sum()
                y_col = y
            data = data[data[y_col] > 0].sort_values(y_col, ascending=False)
            if len(data) > 8:  # keep the pie readable
                other = pd.DataFrame({label: ["Other"], y_col: [data[y_col].iloc[8:].sum()]})
                data = pd.concat([data.head(8), other], ignore_index=True)
            fig = px.pie(data, names=label, values=y_col, hole=0.58, color_discrete_sequence=PALETTE)
            fig.update_traces(textinfo="percent", textposition="inside", insidetextorientation="horizontal",
                              textfont={"size": 11, "color": "#FFFFFF"}, sort=True,
                              marker={"line": {"color": INK, "width": 3}})
            return _style(fig, f"{title}: {_pretty(y_col)}")

        if chart_type == "histogram":
            col = y or (dates[0] if dates else label)  # categorical -> count per value
            if col is None:
                return _empty(title)
            fig = px.histogram(df, x=col, nbins=min(30, max(5, len(df) // 3)),
                               labels={col: _pretty(col)}, color_discrete_sequence=[GOLD])
            fig.update_traces(marker_line_color=INK, marker_line_width=1, marker_cornerradius=3, marker_color=BLUE)
            return _style(fig, f"{title}: {_pretty(col)}")

        if chart_type == "scatter":
            if len(nums) < 2:
                return _empty(title, "נדרשים שני מדדים מספריים")
            color = cats[0] if cats and p["n_unique_cat"][cats[0]] <= 12 else None
            fig = px.scatter(df, x=nums[0], y=nums[1], color=color,
                             hover_name=label if label in df.columns else None,
                             labels={c: _pretty(c) for c in df.columns},
                             color_discrete_sequence=PALETTE)
            fig.update_traces(marker={"size": 11, "line": {"width": 1.5, "color": INK}, "opacity": 0.92})
            return _style(fig, f"{title}: {_pretty(nums[0])} / {_pretty(nums[1])}")

        if chart_type == "heatmap":
            axes = (cats + dates)
            if len(axes) >= 2 and nums:
                pivot = df.pivot_table(index=axes[0], columns=axes[1], values=nums[0], aggfunc="sum")
                z_label = _pretty(nums[0])
            elif len(nums) >= 2:
                pivot = df[nums].corr()
                z_label = "Correlation"
            elif axes and nums:
                pivot = df.set_index(axes[0])[[nums[0]]].T
                z_label = _pretty(nums[0])
            else:
                return _empty(title)
            fig = px.imshow(pivot, aspect="auto", text_auto=".2~s",
                            color_continuous_scale=[[0, "#141726"], [0.55, "#4A5BC4"], [1, GOLD]],
                            labels={"color": z_label})
            return _style(fig, f"{title}: {z_label}")
    except Exception as exc:  # never break the page because of one chart
        return _empty(title, f"לא ניתן לבנות את הגרף ({type(exc).__name__})")

    return _empty(title)


# ---------------------------------------------------------------------------
# Home-screen overview figures
# ---------------------------------------------------------------------------

MONTHS_HE = ["ינו", "פבר", "מרץ", "אפר", "מאי", "יונ", "יול", "אוג", "ספט", "אוק", "נוב", "דצמ"]


def overview_trend(df: pd.DataFrame, year: int) -> go.Figure:
    """Monthly revenue: `year` (filled area) vs. the previous year (dotted)."""
    fig = go.Figure()
    prev = df[df["y"] == year - 1].sort_values("m")
    cur = df[df["y"] == year].sort_values("m")
    fig.add_trace(go.Scatter(x=[MONTHS_HE[m - 1] for m in prev["m"]], y=prev["rev"], name=str(year - 1),
                             mode="lines", line={"color": "#4A4A55", "width": 1.6, "dash": "dot", "shape": "spline"},
                             hovertemplate="%{x} " + str(year - 1) + "<br><b>$%{y:,.0f}</b><extra></extra>"))
    fig.add_trace(go.Scatter(x=[MONTHS_HE[m - 1] for m in cur["m"]], y=cur["rev"], name=str(year),
                             mode="lines+markers", line={"color": BLUE, "width": 2.4, "shape": "spline"},
                             marker={"size": 5, "color": BLUE, "line": {"color": INK, "width": 1.5}},
                             fill="tozeroy", fillcolor="rgba(123,147,255,0.10)",
                             hovertemplate="%{x} " + str(year) + "<br><b>$%{y:,.0f}</b><extra></extra>"))
    _style(fig, "")
    fig.update_layout(title=None, height=268, margin={"l": 4, "r": 4, "t": 6, "b": 4}, hovermode="x unified",
                      legend={"orientation": "h", "y": 1.12, "x": 0, "xanchor": "left", "font": {"size": 11}})
    fig.update_yaxes(tickprefix="$", tickformat="~s", nticks=5)
    return fig
