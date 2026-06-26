"""Gráficos Plotly reutilizables."""
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st


def bar_chart(df, x, y, title, color=None, orientation="v"):
    fig = px.bar(df, x=x, y=y, title=title, color=color, orientation=orientation)
    fig.update_layout(template="plotly_white")
    st.plotly_chart(fig, use_container_width=True)


def heatmap(df, title, x_title="", y_title=""):
    """Heatmap a partir de un DataFrame pivote (índices × columnas)."""
    fig = go.Figure(
        data=go.Heatmap(
            z=df.values,
            x=df.columns.tolist(),
            y=df.index.tolist(),
            colorscale="YlOrRd",
            text=df.values,
            texttemplate="%{text:.0f}%",
            hoverongaps=False,
        )
    )
    fig.update_layout(
        title=title,
        xaxis_title=x_title,
        yaxis_title=y_title,
        template="plotly_white",
    )
    st.plotly_chart(fig, use_container_width=True)


def scatter_chart(df, x, y, title, color=None, size=None):
    fig = px.scatter(df, x=x, y=y, title=title, color=color, size=size)
    fig.update_layout(template="plotly_white")
    st.plotly_chart(fig, use_container_width=True)


def pie_chart(df, names, values, title):
    fig = px.pie(df, names=names, values=values, title=title)
    fig.update_layout(template="plotly_white")
    st.plotly_chart(fig, use_container_width=True)