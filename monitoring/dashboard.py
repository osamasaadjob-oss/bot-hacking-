import dash
from dash import dcc, html
import plotly.graph_objs as go
from datetime import datetime

app = dash.Dash(__name__, title='Bug Bounty AI Monitoring')
app.layout = html.Div([
    html.H1("Bug Bounty AI System - Live Dashboard", style={'textAlign': 'center'}),
    html.H3("System is Online ✅"),
    dcc.Graph(
        id='example-graph',
        figure=go.Figure(data=[go.Bar(x=['A', 'B', 'C'], y=[1, 2, 3])])
    )
])

if __name__ == '__main__':
    app.run_server(host='0.0.0.0', port=8050, debug=False)
