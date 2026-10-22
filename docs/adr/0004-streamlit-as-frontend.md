# ADR-0004: Streamlit as the dashboard frontend

* **Status:** Accepted
* **Date:** 2026-04

## Context

A thesis demo needs an interactive UI that:

* loads quickly,
* lets the reader explore by year, category, method, entity,
* shows individual tender records with their anomaly evidence,
* can be deployed in a single container.

We considered:

* Streamlit
* Plotly Dash
* Panel
* A custom React + FastAPI stack

## Decision

Use **Streamlit** with **Plotly** for charts.

* `streamlit_app/Home.py` is the landing page.
* `streamlit_app/pages/*.py` are separate pages, reached through a grouped
  Albanian sidebar (`_bootstrap.page_header`) instead of Streamlit's default list.
* `streamlit_app/_bootstrap.py` provides cached loaders, the filter
  sidebar, KPI rows, and the caveat banner.

Why not Dash:

* More boilerplate. Streamlit's "write Python top-to-bottom" model
  matches the thesis-prototype mood.
* Plotly works equally in Streamlit; we don't lose interactive plots.

Why not a custom React + FastAPI stack:

* Out of scope for a one-author thesis project.
* No backend logic needed beyond pandas filtering — Streamlit's
  in-process model is sufficient.

## Consequences

**Positive:**

* New pages take ~50 lines of Python.
* `@st.cache_data` ensures the gold tables load once per session.
* The filter sidebar persists across pages via `st.session_state`.

**Negative:**

* Not multi-tenant. For a public deployment we would put the app
  behind a reverse proxy with rate limiting.
* Page-level state isn't fine-grained — a filter change in the sidebar
  re-runs the page top-to-bottom. Acceptable at our data size.

## Related

* `Dockerfile` — multi-stage build with a non-root runtime exposing port 8501.
* `docker-compose.yml` — `app` service with `data/` mounted.
