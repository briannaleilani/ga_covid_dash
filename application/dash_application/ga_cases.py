#!/usr/bin/env python
# coding: utf-8

import sys
import os
import pandas as pd
import numpy as np
import datetime as dt
import copy
import geopandas as gpd
import plotly.graph_objects as go
import plotly.figure_factory as ff
import dash
import dash_table
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output, State, ClientsideFunction
from dash.exceptions import PreventUpdate
import plotly.express as px


cwd = os.getcwd()
data_dir = f'/{cwd}/assets/data'
styles_dir = f'/{cwd}/application/static/css'

sys.path.insert(0, data_dir)
sys.path.insert(0, styles_dir)

from mappings import ALL_COUNTIES, LIST_OF_COLORS, COLORS, DAY_DICT, DATE_DICT, LABEL_STATS, BAR_STATS


######################  DATA & ADDITIONAL ANALYSIS  ###################### 
def get_datasets():
	ga_covid_data_repo = 'https://raw.githubusercontent.com/briannaleilani/georgia_covid_cases/master/ga_data/output'
	datadir = f'{data_dir}/split/05032020/PM'

	over_time = pd.read_csv(f'{data_dir}/merged/ga_90days.csv', parse_dates=['Date'])
	ga_time = pd.read_csv(f'{data_dir}/merged/georgia_pm.csv', parse_dates=['Date'])

	yesterday = (pd.Timestamp.today() - dt.timedelta(days=1)).strftime("%m/%d/%Y")
	most_recent = DAY_DICT[yesterday]
	over_time = over_time[over_time["Day"].between(1, most_recent)]

	age = pd.read_csv(f"{datadir}/Age_05032020_PM.csv", parse_dates=['Date'])
	deaths = pd.read_csv(f"{datadir}/Deaths_05032020_PM.csv", parse_dates=['Date'])
	gender = pd.read_csv(f"{datadir}/Gender_05032020_PM.csv", parse_dates=['Date'])
	summary = pd.read_csv(f"{datadir}/Summary_05032020_PM.csv", parse_dates=['Date'])
	testing = pd.read_csv(f"{datadir}/Testing_05032020_PM.csv", parse_dates=['Date'])
	race = pd.read_csv(f"{datadir}/Race_05032020_PM.csv", parse_dates=['Date'])

	ga_dfs = [age, deaths, gender, summary, testing, over_time, ga_time, race]

	for df in ga_dfs:
		df["Date"] = df["Date"].dt.strftime("%x")

	## Prepare interactive table
	columns_to_show = {"Date":'object', "Day":'int64', "County": 'object', "TotalCases":'int64', 
						"nConfirmed_Change": 'int64', "nDeaths_Change": 'int64', 
	                   "TotalDeaths": 'int64', "Infection_per_100k": 'int64', "Deaths_per_100k": 'int64', 
	                   "PctPopInfected": 'float64', "Fatality_Rate":"float64", "Population":'int64'}
	over_time = over_time.replace([np.inf, -np.inf], np.nan).fillna(0).astype(columns_to_show)
	display_table = over_time[columns_to_show.keys()]
	display_table.rename(columns={
	                        "TotalCases": "Cases",
	                        "TotalDeaths": "Deaths",
	                        "Infection_per_100k": "CasesPer100kPop",
	                        "Deaths_per_100k": "DeathsPer100kPop",
	                        "nConfirmed_Change": "DailyCaseChange",
	                        "nDeaths_Change": "DailyDeathsChange"
	                    }, inplace=True)
	display_table = display_table[display_table["Day"] == display_table["Day"].max()].reset_index(drop=True)

	data = {
		'over_time': over_time, 
		'ga_time': ga_time, 
		'age': age, 
		'deaths': deaths,
		'gender': gender, 
		'summary': summary, 
		'testing': testing,
		'race': race,
		'display_table': display_table,
		'ga_dfs': ga_dfs
	}

	return data

def options_and_controls():
	data = get_datasets()

	over_time = data['over_time']
	ga_time = data['ga_time']

	georgia_only = [{"label": "All Counties", "value": "All Counties"}]

	county_options = [{"label": str(ALL_COUNTIES[county]), "value": str(county)} for county in ALL_COUNTIES]

	stat_options = [{"label": str(value), "value":str(key)} for key, value in LABEL_STATS.items()]
	bar_stat_options = [{"label": str(value[0]), "value":str(key), "disabled": value[1]} for key, value in LABEL_STATS.items()] 

	# # Control for slider
	min_day = ga_time["Day"].min()
	max_day = ga_time["Day"].max()
	days = ga_time["Day"].astype(str).tolist()
	days.append(str(max_day))
	day_options = {days[i]: days[i] for i in range(len(days))} 

	layout = dict(
		autosize=True,
		# automargin=True,
		margin=dict(l=30, r=30, b=20, t=40),
		hovermode="closest",
		plot_bgcolor="#F9F9F9",
		paper_bgcolor="#F9F9F9",
		legend=dict(font=dict(size=10), orientation="h", valign='middle'),
	)
	
	options = {
		'georgia_only':georgia_only,
		'county_options':county_options,
		'day_options': day_options,
		'stat_options': stat_options,
		'bar_stat_options': bar_stat_options
	}

	controls = {
		'min_day': min_day,
		'max_day': max_day,
		'min_date': DATE_DICT[min_day],
		'max_date': DATE_DICT[max_day]
	}

	return options, controls, layout

####################################  Static Plots  #################################### 

## Map of Georgia
def make_ga_map():
	data = get_datasets()
	# [counties, summary] = destructure(data, 'over_time')
	over_time = data['over_time']
	values = over_time['TotalCases'].tolist()
	fips = over_time['fips'].tolist()

	endpts = list(np.mgrid[min(values):max(values):4j])
	colorscale = ["#030512","#1d1d3b","#323268","#3d4b94","#3e6ab0",
				  "#4989bc","#60a7c7","#85c5d3","#b7e0e4","#eafcfd"]

	ga_map = ff.create_choropleth(
		fips=fips, values=values, scope=['Georgia'], show_state_data=True,
		colorscale=colorscale, binning_endpoints=endpts, round_legend_values=True,
		plot_bgcolor='rgb(229,229,229)',
		paper_bgcolor='rgb(229,229,229)',
		legend_title='Population by County',
		county_outline={'color': 'rgb(255,255,255)', 'width': 0.5})
	ga_map.layout.template = None
	return ga_map

## Bar Plot Layout Function
def make_stacked_bar_plot(data,title,xaxis_title,yaxis_title):
	options, conrols, layout = options_and_controls()
	bar_layout = copy.deepcopy(layout)
	# bar_layout = dict(
		# legend=dict(valign='middle', orientation='h', x=0, y=-0.2),
		# font=dict(size=10, color=COLORS['dark_grey']),
		# barmode="stack",
		# )
	bar_layout["barmode"] = "stack"
	# bar_layout["height"] = 600
	bar_layout["title"] = title
	bar_layout["xaxis_title"] = xaxis_title
	bar_layout["yaxis_title"] = yaxis_title
	data=data
	figure = dict(data=data, layout=bar_layout)
	return figure

# Age Table for Display
def age_table():
	data = get_datasets()
	age = data['age']
	age.fillna(0, inplace=True)
	age["Ages_Total"] = age["Ages_Total"].round().astype(int)
	age["Ages_Infected_Total"] = age["Ages_Infected_Total"].round().astype(int)
	age["Ages_Death_Total"] = age["Ages_Death_Total"].round().astype(int)
	age.rename(columns={"Ages_Total": "Total", "Ages_Pct": "Pct", "Ages_Infected_Total": "TotalInfected",
					   "Ages_Inf_Pct": "PctInfected", "Ages_Death_Total": "TotalDeaths", "Ages_Death_Pct": "PctDeaths"}, inplace=True)
	return age

# Gender Table for Display
def gender_table():
	data = get_datasets()
	gender = data['gender']
	gender.fillna(0, inplace=True)
	gender["Gender_Num"] = gender["Gender_Num"].round().astype(int)
	gender["nDeaths"] = gender["nDeaths"].round().astype(int)
	gender["PctDeaths"] = round(gender["nDeaths"] / gender["nDeaths"].sum(),3)
	gender.rename(columns={"Gender_Num": "TotalSurvived", "Gender_Pct": "PctSurvived", "nDeaths": "TotalDeaths"}, inplace=True)
	gender = gender[["Gender", "TotalSurvived", "PctSurvived", "TotalDeaths", "PctDeaths", "Date"]]
	return gender

# Testing Table for Display
def testing_table():
	data = get_datasets()
	testing = data['testing']
	testing["NegativeTests"] = testing["TotalTests"] - testing["PositiveTests"]
	testing = testing[["LabType", "TotalTests", "PositiveTests", "NegativeTests", "Date"]]
	testing.rename(columns={"TotalTests": "Total", "PositiveTests": "Positive", "NegativeTests": "Negative"}, inplace=True)
	return testing

## Age Bar Plot
def age_bar_plot(age):
	age_data=[
		go.Bar(name='Confirmed Cases', x=age["Ages"], y=age["Total"], marker=dict(color = COLORS["dark_blue"])),
		go.Bar(name='Confirmed Deaths', x=age["Ages"], y=age["TotalDeaths"], marker=dict(color = COLORS["dark_yellow"]))
		]
	age_bar_plot = make_stacked_bar_plot(age_data, "GA Confirmed COVID-19 Cases by Age Group", "Age Group", "Number of Cases")
	return age_bar_plot

## Gender Bar Plot
def gender_bar_plot(gender):
	gender_data=[
		go.Bar(name='Confirmed Cases', x=gender["Gender"], y=gender["TotalSurvived"], marker=dict(color = COLORS["dark_blue"])),
		go.Bar(name='Confirmed Deaths', x=gender["Gender"], y=gender["TotalDeaths"], marker=dict(color = COLORS["dark_yellow"]))
		]
	gender_bar_plot = make_stacked_bar_plot(gender_data, "GA Confirmed COVID-19 Cases by Gender", "Gender", "Number of Cases")
	return gender_bar_plot

## Testing Bar Chart
def testing_bar_plot(testing):
	testing_data=[
		go.Bar(name='Negative Tests', x=testing["LabType"], y=testing["Negative"], marker=dict(color = COLORS["dark_blue"])),
		go.Bar(name='Positive Tests', x=testing["LabType"], y=testing["Positive"], marker=dict(color = COLORS["dark_yellow"]))
		]
	testing_plot = make_stacked_bar_plot(testing_data, "GA COVID-19 Testing", "Lab Type", "Number of Tests Completed")
	return testing_plot

## Summary Pie Chart
def summary_pie_chart():
	data = get_datasets()
	summary = data['summary']
	hospitalized, deaths = summary.iat[1,1], summary.iat[2,1]
	mild = summary.iat[0,1] - (hospitalized + deaths)
	summary_plot = go.Figure(data=[go.Pie(labels=["Mild Cases", "Hospitalized", "Deaths"], values=[mild, hospitalized, deaths])])
	summary_plot.update_traces(marker=dict(colors=COLORS['colors4']))
	summary_plot.update_layout(title="GA COVID-19 Cases Summary", 
		legend=dict(font=dict(size=10), valign='middle', orientation='h'), autosize=True,
		margin=dict(l=30, r=30, b=20, t=40), hovermode="closest", plot_bgcolor="#F9F9F9", paper_bgcolor="#F9F9F9"
	)
	return summary_plot

## Race Pie Chart
def make_race_pie_chart():
	data = get_datasets()
	race = data['race']
	race_table_colors = COLORS['colors4'][::-1]
	race_plot = go.Figure(data=[go.Pie(labels=race["Race"], values=race["Race_Num"])])
	race_plot.update_traces(marker=dict(colors=race_table_colors))
	race_plot.update_layout(title="GA COVID-19 Cases by Race", 
		legend=dict(font=dict(size=10), valign='middle', orientation='h'), autosize=True,
		margin=dict(l=30, r=30, b=20, t=40), hovermode="closest", plot_bgcolor="#F9F9F9", paper_bgcolor="#F9F9F9"
	)
	return race_plot

# Set up layout for application 
def application_layout():
	data = get_datasets()
	options, controls, layout = options_and_controls()

	summary = data['summary']
	display_table = data['display_table']

	testing = testing_table()
	age = age_table()
	gender = gender_table()
	race = data['race']

	min_day = controls['min_day']
	max_day = controls['max_day']
	day_options = options['day_options']
	stat_options = options['stat_options']
	min_date = controls['min_date']
	max_date = controls['max_date']

	layout = html.Div( 
		children=[

			dcc.Store(id="aggregate_data"),

			dcc.Store(id="main_graph_data"),

			# empty Div to trigger javascript file for graph resizing
			html.Div(id="output-clientside"),

			# Create header container

			html.Div(

				html.Div(
					[
						# title
						html.H1(
							children='Georgia COVID-19 Dashboard',
							style={'color': COLORS["text"],
									'marginBottom': '0px',
									'marginTop': '20px'}
						),

						# subtitle
						html.H2(
							children="Data Source: Georgia Department of Health",
							style={
								'color': COLORS["text"],
								'fontSize':'16px',
								'marginTop': '20px'}
						),   

						
					],
					className="center outer",
				),
				id='header',
				className='row flex_box ',
			),

			html.Div([
					html.Div([
								html.H3("About The Data", 
									style={'textAlign': "center"}),
								html.Hr(),
								html.P("""
									The first two confirmed instances of COVID-19 in Georgia were recorded on March 2nd, 2020 in Fulton County¹. 
									Although these are the first confirmed and recorded instances of the virus, it is possible that the virus was already circulating.
									Up until the end of March, only 16,181 tests had been conducted which is less than half of a percent of Georgia's roughly 4 million population.
									Although testing is now increasing, Georgia has lagged behind other states in its testing efforts and has some catch up to do². 
									""",
									style={"fontSize": "14px"}),
								html.Br([]),
								html.P("""
									This means that while the data is improving, it is not perfect. 
									The data gathered for this dashboard has been collected from the daily report released by the Georgia Department of Public Health³ along 
									with some population and county ranking data from the 2020 County Health Rankings⁴.
									Over time, the data collected has been improved. In addition to the case and death figures, there is now some high-level information regarding 
									demographics, severity of cases, the total number of tests completed, and greater detail on the Georgia deaths so far. 
									The dashboard is a work in progress and as more data is available, updates will be made.
									""",
									style={ "fontSize": "14px"}),
								],
								className="pretty_container info-box outer"
								),
					],
			className='row flex_box',
				),

			# Customization Options; Key stat Boxes, Graph with County Data Over Time

			html.Div(
				[
				html.Div(
					[
					# html.Div(
					# 	[
						html.H3("Cumulative COVID-19 Statistics", 
							style={'color': COLORS['text'], 'marginBottom': '20px', 'textAlign': 'center'}),
						html.Hr(),
						html.Div(
								[
									html.Div(
										[html.Span(["Confirmed", html.Br(), "Cases"]), html.H4(id="cases_text"), html.Span(id="case_date")],
										id="cases",
										className="mini_container",
									),
									html.Div(
										[html.Span(["Confirmed", html.Br(), "Deaths"]), html.H4(id="deaths_text"), html.Span(id="deaths_date")],
										id="deaths",
										className="mini_container",
									),
									html.Div(
										[html.Span(["Infections", html.Br(), "per 100k"]), html.H4(id="infection_text"), html.Span(id="infection_date")],
										id="infection_rate",
										className="mini_container",
									),
									html.Div(
										[html.Span(["Fatality", html.Br(), "Rate"]), html.H4(id="fatality_text"), html.Span(id="fatality_date")],
										id="fatality_rate",
										className="mini_container",
										style={'alignSelf': 'stretch'}
									),
									html.Div(
										[html.Span(["Case", html.Br(), "Increase"]), html.H4(id="case_increase_text"), html.Span(id="c_increase_date")],
										id="case_increase",
										className="mini_container",
									),
									html.Div(
										[html.Span(["Deaths", html.Br(), "Increase"]), html.H4(id="deaths_increase_text"), html.Span(id="d_increase_date")],
										id="deaths_increase",
										className="mini_container",
									),
								],
								id="info-container",
								className="row center flex_box",
							),
					html.Div(
						[
						html.Div(
							[
								html.Div([
										html.Br(),
										html.Details([
											html.Summary("Filter by Date"),
											html.Br(),
											html.Ul([
														html.Li("Begins day 1 of the Georgia outbreak (March 2nd, 2020)."),
														html.Li("Ends with the most recent data gathered (typically from the day prior)."),
														html.Li("To filter, use either the slider below OR drag and select the bars in the graph."),
														html.Li("Date filters will impact both the bar and line chart as well as the statistic boxes."),
														html.Li("""The last day in the filtered range will be the date used to calculate 
																the figures in the overhead boxes."""),
														html.Li("""The 'Case Increase' and 'Deaths Increase' figures are calculated as an increase since the day before the 
															date slider begins until the last date chosen in the slider"""),
														]),
											html.Hr(), 
											]),
										dcc.RangeSlider(
											id="day_slider",
											min=1,
											max=max_day,
											value=[0, max_day],
											tooltip="always_visible",
											marks={
												1: '03/02/20',
												14: '03/16/20',
												28: '03/30/20',
												42: '04/13/20',
												56: '04/27/20', 
												70: '05/11/20',
												84: '05/25/20'
												},
											className="dcc_control",
										),

										html.Br(),
										html.Details([
											html.Summary("Filter by Location"),
											html.Br(),
											html.Ul([
														html.Li("Location filters will impact both the bar and line chart as well as the statistic boxes."),
														html.Li("""While the cumulative data for the locations chosen will be shown in the summary boxes,
															you can also hover over sections of the bars to see county specific data."""),
														html.Li("""You can edit any pre-configured group except for 'All of Georgia' 
															which provides figures for all Georgia data combined already 
															(including 'Unknown' counties and 'Non-Georgia Resident' cases)."""),
														]),
											html.Hr(),
											]),
										dcc.RadioItems(
											id="county_group_selector",
											options=[
												{"label": "All of Georgia ", "value": "all"},
												{"label": "10 Counties with Highest Cases ", "value": "top_10"},
												{"label": "Family & Friends ", "value": "family"},                              
												{"label": "No County Assigned", "value": "unassigned"},
												{"label": "Pick a county ", "value": "custom"}
											],
											value="all",
											labelStyle={"display": "inline-block"},
											className="dcc_control",
										),
										dcc.Dropdown(
											id="county_options_menu",
											multi=True,
											value='All Counties',
											placeholder="Please select a county",
											className="dcc_control",
										),

										html.Br(),
										html.Details([
											html.Summary("Filter by Statistic"),
											html.Br(),
											html.Ul([
														html.Li("Statistic filters will only impact the graphs and have no effect on the statistic boxes."),
														html.Li("Note that rates per population are an average rather than a cumulative amount and therefore will not show up in the bar graph"),
														]),
											html.Hr()
											]),
										dcc.RadioItems(
											id="county_stat_selector",
											options=stat_options,
											value="TotalCases",
											labelStyle={"display": "inline-block"},
											className="dcc_control"
											),
										html.Div(id='output-container-confirmation', className='pretty_container inner'),
										],
										id="selector_filters"
										),  
								],
							style={'textAlign': 'left', 'flex': '110'}
						),

						html.Div(
							[
								html.Div([
									dcc.Tabs(id="main_graph_tabs", value="tab-1", parent_className="custom-tabs", 
										children= [
											dcc.Tab(label="Line Graph", value='tab-1', 
												className='custom-tab', selected_className='custom-tab--selected'),
											dcc.Tab(label="Bar Chart", value='tab-2',
												className='custom-tab', selected_className='custom-tab--selected'),
											# dcc.Tab(label="Logarithmic Graph", value='tab-3',
											# 	className='custom-tab', selected_className='custom-tab--selected'),
										]
									),
									html.Div(id="main_graph_tabs_content"),
									],
									className="pretty_container inner",
									id="pretty_count_graph"
									),
								
								],
								id="right-column",
							),
						],
						className="row container-display"
						),
					],
					className="pretty_container outer"
				),
			],
			className="row flex_box",
			),

			# Tabular Breakdowns of Charts with Data Tables

			html.Div([

				# Summary Data and Testing Data

				html.Div([
					html.H3("Georgia Summary Data",
						style={
							'color': COLORS['text'],
							'marginBottom': '20px',
							'textAlign': 'center'}
							),
					html.Hr(),
					dcc.Tabs(
						parent_className="custom-tabs",
						children=[
						dcc.Tab(
							label='Summary of Cases', 
							className='custom-tab',
							selected_className='custom-tab--selected',
							children=[
							html.Div([
								dcc.Tabs(
										children=[
									dcc.Tab(
										label="Summary Pie Chart", 
										className='custom-tab',
										selected_className='custom-tab--selected-child',
										children=[
											dcc.Graph(id="summary_pie_chart", className="graph_padding", figure=summary_pie_chart())]
												),
									dcc.Tab(
										label="Summary Data", 
										className='custom-tab',
										selected_className='custom-tab--selected-child',
										children=[
											dash_table.DataTable(
												id='summary_table',
												columns=[{"name": i, "id": i} for i in summary.columns],
												data=summary.to_dict('records'),
												style_as_list_view=True,
												style_cell={'padding': '5px','textAlign': 'left'},
												style_header={'backgroundColor': 'white','fontWeight': 'bold'},
												style_table={'overflowX': 'scroll'},
												),  
											dcc.Markdown("""Data from [Georgia Department of Public Health]
												(https://dph.georgia.gov/covid-19-daily-status-report)""")
											])
										],
										className="custom-tabs-container"
										),
									]),
								]),
						dcc.Tab(
							label="Testing Rates", 
							className='custom-tab',
							selected_className='custom-tab--selected',
							children=[
							html.Div([
								dcc.Tabs(
										children=[
									dcc.Tab(
										label="Testing Bar Chart", 
										className='custom-tab',
										selected_className='custom-tab--selected-child',
										children=[
											dcc.Graph(id="testing_pie_chart", className="graph_padding", figure=testing_bar_plot(testing))]
												),
									dcc.Tab(
										label="Testing Data", 
										className='custom-tab',
										selected_className='custom-tab--selected-child',
										children=[
											dash_table.DataTable(
												id='testing_table',
												columns=[{"name": i, "id": i} for i in testing.columns],
												data=testing.to_dict('records'),
												style_as_list_view=True,
												style_cell={'padding': '5px','textAlign': 'left'},
												style_header={'backgroundColor': 'white','fontWeight': 'bold'},
												style_table={'overflowX': 'scroll'},
												),  
											dcc.Markdown("""Data from [Georgia Department of Public Health]
												(https://dph.georgia.gov/covid-19-daily-status-report)""")
											])
										],
										className="custom-tabs-container"
										),
									]),
								]),
							]),
						],
						className="pretty_container",
						id="left-summary",
					),
				
				# Demographic Data

				html.Div([
					html.H3("Georgia Demographic Data",
						style={
							'color': COLORS['text'],
							'marginBottom': '20px',
							'textAlign': 'center'}
							),
					html.Hr(),
					dcc.Tabs(
						parent_className="custom-tabs",
						children=[
						dcc.Tab(
							label='Age', 
							className='custom-tab',
							selected_className='custom-tab--selected',
							children=[
							html.Div([
								dcc.Tabs(
										children=[
									dcc.Tab(
										label="Age Bar Chart", 
										className='custom-tab',
										selected_className='custom-tab--selected-child',
										children=[
											dcc.Graph(id="age_pie_chart", className="graph_padding", figure=age_bar_plot(age))]
												),
									dcc.Tab(
										label="Age Data", 
										className='custom-tab',
										selected_className='custom-tab--selected-child',
										children=[
											dash_table.DataTable(
												id='age_table',
												columns=[{"name": i, "id": i} for i in age.columns],
												data=age.to_dict('records'),
												style_as_list_view=True,
												style_cell={'padding': '5px','textAlign': 'left'},
												style_header={'backgroundColor': 'white','fontWeight': 'bold'},
												style_table={'overflowX': 'scroll'},
												),  
											dcc.Markdown("""Data from [Georgia Department of Public Health]
												(https://dph.georgia.gov/covid-19-daily-status-report)""")
											])
										],
										className="custom-tabs-container"
										),
									]),
								]),
						dcc.Tab(
							label="Gender", 
							className='custom-tab',
							selected_className='custom-tab--selected',
							children=[
							html.Div([
								dcc.Tabs(
										children=[
									dcc.Tab(
										label="Gender Bar Chart", 
										className='custom-tab',
										selected_className='custom-tab--selected-child',
										children=[
											dcc.Graph(id="gender_pie_chart", className="graph_padding", figure=gender_bar_plot(gender))]
												),
									dcc.Tab(
										label="Gender Data", 
										className='custom-tab',
										selected_className='custom-tab--selected-child',
										children=[
											dash_table.DataTable(
												id='gender_table',
												columns=[{"name": i, "id": i} for i in gender.columns],
												data=gender.to_dict('records'),
												style_as_list_view=True,
												style_cell={'padding': '5px','textAlign': 'left'},
												style_header={'backgroundColor': 'white','fontWeight': 'bold'},
												style_table={'overflowX': 'scroll'},
												),  
											dcc.Markdown("""Data from [Georgia Department of Public Health]
												(https://dph.georgia.gov/covid-19-daily-status-report)""")
											])
										],
										className="custom-tabs-container"
										),
									]),
								]),
						dcc.Tab(
							label="Race", 
							className='custom-tab',
							selected_className='custom-tab--selected',
							children=[
							html.Div([
								dcc.Tabs(
										children=[
									dcc.Tab(
										label="Race Bar Chart", 
										className='custom-tab',
										selected_className='custom-tab--selected-child',
										children=[
											dcc.Graph(id="race_pie_chart", className="graph_padding", figure=make_race_pie_chart())]
												),
									dcc.Tab(
										label="Race Data", 
										className='custom-tab',
										selected_className='custom-tab--selected-child',
										children=[
											dash_table.DataTable(
												id='race_table',
												columns=[{"name": i, "id": i} for i in race.columns],
												data=race.to_dict('records'),
												style_as_list_view=True,
												style_cell={'padding': '5px','textAlign': 'left'},
												style_header={'backgroundColor': 'white','fontWeight': 'bold'},
												style_table={'overflowX': 'scroll'},
												),  
											dcc.Markdown("""Data from [Georgia Department of Public Health]
												(https://dph.georgia.gov/covid-19-daily-status-report)""")
											])
										],
										className="custom-tabs-container"
										),
									]),
								]),
							]),
						],
						className="pretty_container",
						id="right-demographic",
					),
				],
				className="row flex_box",
				id="summary_graphs"
			),


			# County DataTable Here

			html.Div(
				children=[
					html.Div(
						children=[   
							html.Div(
								children=[

									html.H3("Georgia's Latest COVID-19 Figures by County", 
									style={
										'color': COLORS['text'],
										'marginBottom': '20px',
										'textAlign': 'center'}
										),
									html.Hr(),

									html.Div([
										html.Details(
											[   
												html.Summary("How to Use the Table"),
												html.H4("How To Use The Table",
													className="subcategory_text"
													),
													html.Ul([
														html.Li("""To filter on a column, enter either an operator and a value (for example, in "Cases", type '> 200') to get a list of counties with more than 200 cases
													or just type a value (for example, in "County", type 'Fulton'), which will filter the dataframe down to Fulton county only."""),
														html.Li("""Acceptable operators for filtering:"""),
															html.Ul([
																html.Li("Greater Than (>) or Less Than (<)"),
																html.Li("Greater Than or Equal to (>=) or Less Than or Equal to (<=)"),
																html.Li("Equal To (=) or Not Equal To (!=)"),
																]),
														html.Li("""It is best practice to type your filter within quotes, particularly if it has any spaces or special characters in it."""),
														html.Li("""To refresh the table after a filter, delete your filter text and press enter."""),
														html.Li("""To sort the data from highest to lowest, click on the arrows next to the column name. 
															Note that only one column can be sorted at a time."""),
														html.Li("""You can also select one (or multiple) of the columns by clicking on the box next to the column name. 
														This will create a bar chart below the table that shows the data for each county."""),
														html.Li("""You can also highlight specific counties in the graph by checking the box next to the county name in the table row.
															This will make them appear yellow in the graph(s) below.""")
														]),
													],
												),
										html.Br(),
											],
										),

									dash_table.DataTable(
										id='datatable-interactivity',
										columns=[{"name": i, "id": i, "selectable": True} for i in display_table.columns],
										data=display_table.to_dict('records'),
										filter_action="native",
										sort_action="native",
										sort_mode="single",
										sort_by=[{"column_id": "Cases", "direction": "desc"}],
										column_selectable="multi",
										row_selectable="multi",
										row_deletable=False,
										selected_columns=["CasesPer100kPop"],
										selected_rows=[],
										page_action="native",
										page_current=0,
										page_size=10,
										style_table={"overflowX": "scroll"},
										style_cell={'minWidth': '100px', 'maxWidth': '180px'},
										style_cell_conditional=[
											{
												'if': {'column_id': c},
												'textAlign': 'left'
											} for c in ["Date", "Day", "County"]
										],
										style_header={
											'backgroundColor': COLORS['light_grey'],
											'fontWeight': 'bold'
												}
											),
									html.Br(),
									html.Br(),
									html.Hr(),
									html.Div(id="datatable-interactivity-container", 
										className="pretty_container inner"),
									],
								),

							],
							className="pretty_container outer",
							# style=""
						),
					],
					className="row flex_box",
				),

				html.Footer( 

					html.Div(
						[
							html.H3(
								children='Additional Resources and References',
								style={
									'color': COLORS['text'],
									'marginBottom': '20px',
									'textAlign': 'center'}  
							),
							dcc.Tabs(
								[
								dcc.Tab(
									label="Additional Resources", 
									className='custom-tab',
									selected_className='custom-tab--selected-child',
									children=[
										html.Br(),
										html.Details([
											html.Summary("News"),
											html.Hr(),
											html.H4("News", className='subcategory_text'),
											html.Ul([
												html.Li(html.A("Live Updates From the New York Times Regarding Both US and Global News", href="https://www.nytimes.com/2020/04/08/us/coronavirus-live-updates.html")),
												html.Li(html.A("Atlanta Journal Constitution Coronavirus Coverage", href="https://www.ajc.com/news/coronavirus/")),
												html.Li(html.A("2020 Coronavirus Pandemic in Georgia (Wikipedia)", href="https://en.wikipedia.org/wiki/2020_coronavirus_pandemic_in_Georgia_(U.S._state)")),
												]),
											html.Hr(),
											]
										),
										html.Details([
											html.Summary("Data Visualizations and Predictive Analytics"),
											html.Hr(),
											html.H4("Data Visualizations and Predictive Analytics", className='subcategory_text'),
											html.Ul([
												html.Li(html.A("Coronavirus Projections Regarding Peaks, Hospital Capacity, and More (Country and State Level)", href="https://covid19.healthdata.org/united-states-of-america")),
												html.Li(html.A("The Weather Channel - Comprehensive Coronavirus Dashboard", href="https://accelerator.weather.com/bi/?perspective=dashboard&pathRef=.public_folders%2FCOVID19%2FDashboards%2FDS%2FCOVID-19%20%28Coronavirus%29%20Global%20Statistics&id=iC2B38B09B142481EB83935F6419CA837&ui_appbar=false&ui_navbar=false&objRef=iC2B38B09B142481EB83935F6419CA837&options%5Bcollections%5D%5BcanvasExtension%5D%5Bid%5D=com.ibm.bi.dashboard.canvasExtension&options%5Bcollections%5D%5BfeatureExtension%5D%5Bid%5D=com.ibm.bi.dashboard.core-features&options%5Bcollections%5D%5Bbuttons%5D%5Bid%5D=com.ibm.bi.dashboard.buttons&options%5Bcollections%5D%5Bwidget%5D%5Bid%5D=com.ibm.bi.dashboard.widgets&options%5Bcollections%5D%5BcontentFeatureExtension%5D%5Bid%5D=com.ibm.bi.dashboard.content-features&options%5Bcollections%5D%5BboardModel%5D%5Bid%5D=com.ibm.bi.dashboard.boardModelExtension&options%5Bcollections%5D%5BsaveServices%5D%5Bid%5D=com.ibm.bi.dashboard.saveServices&options%5Bcollections%5D%5BserviceExtension%5D%5Bid%5D=com.ibm.bi.dashboard.serviceExtension&options%5Bcollections%5D%5BlayoutExtension%5D%5Bid%5D=com.ibm.bi.dashboard.layoutExtension&options%5Bcollections%5D%5BvisualizationExtension%5D%5Bid%5D=com.ibm.bi.dashboard.visualizationExtensionCA&options%5Bcollections%5D%5BcolorSetExtensions%5D%5Bid%5D=com.ibm.bi.dashboard.colorSetExtensions&options%5Bconfig%5D%5BsmartTitle%5D=false&options%5Bconfig%5D%5BeditPropertiesLabel%5D=true&options%5Bconfig%5D%5BnavigationGroupAction%5D=true&options%5Bconfig%5D%5BenableDataQuality%5D=false&options%5Bconfig%5D%5BmemberCalculation%5D=false&options%5Bconfig%5D%5BassetTags%5D%5B%5D=dashboard&options%5Bconfig%5D%5BfilterDock%5D=true&options%5Bconfig%5D%5BshowMembers%5D=true&options%5Bconfig%5D%5BassetType%5D=exploration&options%5Bconfig%5D%5BgeoService%5D=CA&isAuthoringMode=false&boardId=iC2B38B09B142481EB83935F6419CA837")),
												]),
											html.Hr(),
											]
										),
										html.Details([
											html.Summary("Community Support"),
											html.Hr(),
											html.H4("Community Support", className='subcategory_text'),
											html.Ul([
												html.Li(html.A("Atlanta Coronavirus Resources (Travel Updates, Community Resources, Virtual Tourism and Events, etc.)", href="https://www.atlanta.net/coronavirus/resources/")),
												]),
											html.Hr(),
											]
										),
										html.Details([
											html.Summary("An Alternative... Good News in the Age of Coronavirus"),
											html.Hr(),
											html.H4("An Alternative... Good News in the Age of Coronavirus", className='subcategory_text'),
												html.Ul([
													html.Li(html.A("Good News Dashboard for COVID-19", href="https://www.inspiremore.com/coronavirus-good-news-dashboard")),
													]),
												html.Hr(),
												]
											),
										],
									),
								dcc.Tab(
									label="References",
									className='custom-tab',
									selected_className='custom-tab--selected-child',
									children=[
										html.Br(),
										html.Hr(),
										html.H4("Data Sources and References", className='subcategory_text'),
										html.Ol([
											html.Li(html.A("Georgia's first two confirmed COVID-19 cases (March 2, 2020)", href="https://www.wsbtv.com/news/local/first-cases-coronavirus-confirmed-georgia/4P22YK37OBF2ZIC5VY2YOX7KDE/")),
											html.Li(html.A("Georgia lags behind other states in terms of COVID-19 Testing (March 25, 2020)", href="https://www.ajc.com/news/local-govt--politics/timetable-for-widespread-virus-testing-amid-ongoing-test-scarcity/oKpCMimtpgDidMAoCThROO/")),
											html.Li(html.A("Georgia Department of Public Health (Gdph) COVID-19 Daily Status Report", href="https://dph.georgia.gov/covid-19-daily-status-report")),
											html.Li(html.A("2020 Georgia County Rankings Data", href="https://www.countyhealthrankings.org/app/georgia/2019/downloads")),
											],
										),
									],
								),
							],
						),                     
					],
					className="pretty_container outer",
				),
				# id='footer',
				className='row flex_box',
			),

		],


	id="mainContainer",
	style={"display": "flex", "flexDirection": "column"}
	)
	return layout


### HELPER FUNCTIONS
def filter_dataframe(df, day_slider, county_stat_selector=None, county=None):
	"""
	This function will filter the `over_time` or `ga_time` dataframes based on day chosen with the following options:
	- `county` if `over_time` is used (otherwise, should be 'None')
	-  `county_stat_selector` to filter on specific statistics (otherwise, should be 'None')
	"""
	dff = 0
	if county_stat_selector == None:
		# Pulls back full dataframe based on days chosen
		if county == None:
			dff = df[df['Day'].between(day_slider[0]+1, day_slider[1])]
					 
		# Pulls back full dataframe based on counties and days chosen
		else:
			dff = df[df["County"].isin(county)
				& (df["Day"] > day_slider[0])
				& (df["Day"] <= (day_slider[1]))
				]
	else:
		# Pulls back specific stats for Georgia as a whole (not by counties)
		if county == None:
			dff = df[[county_stat_selector, "Day"]][df['Day'].between(day_slider[0]+1, day_slider[1])]
			
		# Pulls back specific stats for chosen counties
		else:
			dff = df[[county_stat_selector, "County", "Day"]][
			df["County"].isin(county) 
			& (df["Day"] > day_slider[0])
			& (df["Day"] <= day_slider[1])           
			]

	return dff

# Used for adding emphasis to text
def emph(t, color=COLORS['text']):
	return html.B([t],style={'color':color})

# Format numbers with , as separator
def format_num(num):
	return ('{0:{grp}d}'.format(int(num), grp=','))

### CALLBACKS

def init_callbacks(app):
	data = get_datasets()
	options, controls, layout = options_and_controls()
	ga_time = data['ga_time']
	over_time = data['over_time']
	display_table = data['display_table']
	min_day = controls['min_day']
	max_day = controls['max_day']
	# all_counties_option = options['all_counties_option']
	county_options = options['county_options']
	georgia_only = options['georgia_only']

	app.clientside_callback(
    ClientsideFunction(namespace="clientside", function_name="resize"),
    Output("output-clientside", "children"),
    [Input("count_graph", "figure"), Input("line_graph", "figure")])

	# Disable 'All Counties' as an option if 'All of Georgia' filter is NOT chosen
	@app.callback(
	    dash.dependencies.Output('county_options_menu', 'options'),
	    [Input('county_group_selector', 'value')])

	def update_multi_options(value):
	    if value != "all":
	        return county_options
	    else:
	        return georgia_only

	@app.callback(
	    Output("aggregate_data", "data"),
	    [
	        Input("county_options_menu", "value"),
	        Input("day_slider", "value"),
	    ],
	)
	# Updates statistic boxes at top of dashboard
	def update_key_figures_text(county_options_menu, day_slider):
	    dff = 0
	    sum_cases = 0
	    sum_deaths = 0
	    c_increase = 0
	    d_increase = 0
	    avg_infection = 0
	    avg_fatality = 0
	    if day_slider[1] > ga_time["Day"].max():
	    	day_slider[1] = ga_time["Day"].max()
	    # Filters for entire state of Georgia
	    if county_options_menu == ["All Counties"]:
	        dff = filter_dataframe(ga_time, day_slider, None, None)
	        sum_cases = dff.loc[dff['Day'] == day_slider[1], 'TotalCases'].iloc[0]
	        sum_deaths = dff.loc[dff['Day'] == day_slider[1], 'TotalDeaths'].iloc[0]
	        c_increase = dff["nConfirmed_Change"].sum()
	        d_increase = dff["nDeaths_Change"].sum()
	        
	    # Filters by counties chosen
	    else:
	        dff = filter_dataframe(over_time, day_slider, None, county_options_menu)
	        sum_cases = dff[dff["Day"] == day_slider[1]]["TotalCases"].sum()
	        sum_deaths = dff[dff["Day"] == day_slider[1]]["TotalDeaths"].sum()
	        c_increase = dff["nConfirmed_Change"].sum()
	        d_increase = dff["nDeaths_Change"].sum()

	    if (sum_deaths is not 0) & (dff["Fatality_Rate"] is not 0):
	    	dff["Fatality_Rate"] = dff["Fatality_Rate"] * 100
	    	avg_fatality = dff[dff["Day"] == day_slider[1]]["Fatality_Rate"].values.sum() / len(county_options_menu)
	    	avg_fatality = str(round(avg_fatality,2)) + "%"

	    if (sum_cases is not 0) & (dff["Infection_per_100k"] is not 0): 
	        avg_infection = dff[dff["Day"] == day_slider[1]]["Infection_per_100k"].values.sum() / len(county_options_menu)
	        avg_infection = round(avg_infection)

	    day_before_slider = "03/02/2020"
	    if day_slider[0] > 1:
	    	day_before_slider = DATE_DICT.get(day_slider[0])
	    case_date = "As of: ", html.Br(), emph(DATE_DICT.get(day_slider[1]))
	    deaths_date = "As of: ", html.Br(), emph(DATE_DICT.get(day_slider[1]))
	    infection_date = "As of: ", html.Br(), emph(DATE_DICT.get(day_slider[1]))
	    fatality_date = "As of: ", html.Br(), emph(DATE_DICT.get(day_slider[1]))
	    c_increase_date = "Since:", html.Br(), emph(day_before_slider)
	    d_increase_date = "Since:", html.Br(), emph(day_before_slider)

	    return (format_num(sum_cases), format_num(sum_deaths), format_num(avg_infection), 
	    	avg_fatality, format_num(c_increase), format_num(d_increase), 
	    	case_date, deaths_date, infection_date, fatality_date, c_increase_date, d_increase_date)

	# Selectors -> key figures text
	@app.callback(
	    [
	        Output("cases_text", "children"),
	        Output("deaths_text", "children"),
	        Output("infection_text", "children"),
	        Output("fatality_text", "children"),
	        Output("case_increase_text", "children"),
	        Output("deaths_increase_text", "children"),
	        Output("case_date", "children"),
	        Output("deaths_date", "children"),
	        Output("infection_date", "children"),
	        Output("fatality_date", "children"),
	        Output("c_increase_date", "children"),
	        Output("d_increase_date", "children"),
	    ],
    	[Input("aggregate_data", "data")])

	def update_text(data):
		return data[0], data[1], data[2], data[3], data[4], data[5], data[6], data[7], data[8], data[9], data[10], data[11]

	# Radio -> multi
	@app.callback(
		Output("county_options_menu", "value"), 
		[Input("county_group_selector", "value")])

	def display_type(selector):
	    if selector == "all":
	        return ["All Counties"]
	    elif selector == "top_10":
	        unique_counties = over_time.drop_duplicates(subset="County", keep="last")
	        unique_counties = unique_counties[unique_counties["fips"] != 0]
	        top_10 = unique_counties.sort_values(by="TotalCases", ascending=False).head(10)
	        top_10 = top_10["County"].tolist()
	        return top_10
	    elif selector == 'unassigned':
	        return ['Unknown', 'Non-Georgia Resident']
	    elif selector == "family":
	        return ['Fulton', 'Cobb', 'Fannin', 'Walton', 'Rockdale', 'Gwinnett']
	    else:
	        return []

	@app.callback(Output('county_options_menu', 'style'), [Input('county_group_selector', 'value')])
	def hide_graph(input):
	    if input == "all":
	        return {'display':'none'}

	# Slider -> count graph
	@app.callback(Output("day_slider", "value"), [Input("count_graph", "selectedData")])
	def update_day_slider(count_graph_selected):

	    if count_graph_selected is None:
	        return [0, max_day]

	    nums = [int(point["pointNumber"]) for point in count_graph_selected["points"]]
	    return [min(nums) + 0, max(nums) + (min_day+1)]

	# Output container for range slider
	@app.callback(
		Output('output-container-confirmation', 'children'),
		[
			Input('day_slider', 'value'),
			Input('county_options_menu', 'value'),
			Input("county_stat_selector", "value"),
			Input("main_graph_tabs", "value")
		])

	def update_output(day_slider, county_options_menu, county_stat_selector, tab):
		if day_slider[1] > ga_time["Day"].max():
			day_slider[1] = ga_time["Day"].max()
		return_value = html.Span(["You have selected: ", emph(LABEL_STATS[county_stat_selector]), html.Br(),
								" Dates: ", emph(DATE_DICT.get(day_slider[0] + 1)), " - ", emph(DATE_DICT.get(day_slider[1])), html.Br(),
								" Days: ", emph(day_slider[0] + 1), " - ", emph(day_slider[1]), html.Br(),
								" Locations: ", emph(f"{county_options_menu}"),
								])
		if tab == 'tab-2' and any ([county_stat_selector == 'Infection_per_100k', county_stat_selector == 'Deaths_per_100k']):
			return_value = html.Span(["You have selected: ", emph(LABEL_STATS[county_stat_selector], color="red"), \
				" which is only available as a line graph as it is based on an average rather than a cumulative amount. \
				Please switch to the ", emph("Line Graph", color="red"), " tab to view these stats."])
		return return_value

	# Set dynamic table style
	@app.callback(
	    Output('datatable-interactivity', 'style_data_conditional'),
	    [Input('datatable-interactivity', 'selected_columns')]
	)

	def update_styles(selected_columns):
	    return [{
	        'if': { 'column_id': i },
	        'background_color': COLORS["light_blue"]
	    } for i in selected_columns]

	# Update graphs associated with table
	@app.callback(
	    Output('datatable-interactivity-container', "children"),
	    [Input('datatable-interactivity', "derived_virtual_data"),
	     Input('datatable-interactivity', "derived_virtual_selected_rows"),
	     Input('datatable-interactivity', "selected_columns")])
	def update_graphs(rows, derived_virtual_selected_rows, selected_columns):

	    if derived_virtual_selected_rows is None:
	        derived_virtual_selected_rows = []

	    dff = display_table if rows is None else pd.DataFrame(rows)

	    colors = [COLORS['dark_yellow'] if i in derived_virtual_selected_rows else COLORS['dark_blue']
	              for i in range(len(dff))]

	    return [
	        dcc.Graph(
	            id=column,
	            figure={
	                "data": [
	                    {
	                        "x": dff["County"],
	                        "y": dff[column],
	                        "type": "bar",
	                        "marker": {"color": colors},
	                    }
	                ],
	                "layout": {
	                    "xaxis": {"automargin": True},
	                    "yaxis": {
	                        "automargin": True,
	                        "title": {"text": column}
	                    },
	                    "height": 250,
	                    "margin": {"t": 10, "l": 10, "r": 10},
	                },
	            },
	        )
	        for column in selected_columns if column in dff
	    ]

		# Selectors -> count graph
	@app.callback(Output("main_graph_data", "data"),
	    [
	        Input("county_stat_selector", "value"),
	        Input("day_slider", "value"),
	        Input('main_graph_tabs', 'value'),
	        Input("county_options_menu", "value")
	    ]
	    )

	def make_count_figure(county_stat_selector, day_slider, tab, county_options_menu=None):
	    tab_1_data = []
	    tab_2_data = []
	    new_layout = copy.deepcopy(layout)

	    # if day_slider is None or county_options_menu is None:
	    # 	fig = dict(layout=layout_line)
	    # 	return fig

	    if any ([day_slider is None, county_options_menu is None]):
	    	return tab_1_data, tab_2_data, new_layout
	    elif tab == 'tab-2' and any ([county_stat_selector == 'Infection_per_100k', county_stat_selector == 'Deaths_per_100k']):
	    	return tab_1_data, tab_2_data, new_layout   	

	    else:
		    dff = filter_dataframe(over_time, day_slider, county_stat_selector, county_options_menu)
		    if county_options_menu == ["All Counties"]:
		        dff = filter_dataframe(ga_time, day_slider, county_stat_selector, None)

		    y_data = []
		    date_text = [value for key, value in DATE_DICT.items()][day_slider[0]:day_slider[1]]
		    day_text = [value for key, value in DAY_DICT.items()][day_slider[0]:day_slider[1]]
		    for county_name in county_options_menu:
		        if county_options_menu == ["All Counties"]:
		            y_data.append(dff[county_stat_selector])
		            date_text = [value for key, value in DATE_DICT.items()][day_slider[0]:day_slider[1]]
		            day_text = [value for key, value in DAY_DICT.items()][day_slider[0]:day_slider[1]]
		        else:
		            y_data.append(dff[county_stat_selector][dff["County"] == county_name])
		            date_text = [value for key, value in DATE_DICT.items()][day_slider[0]:day_slider[1]]
		            day_text = [value for key, value in DAY_DICT.items()][day_slider[0]:day_slider[1]]

		    colors = COLORS["colors8"]*10
		    hovertemplate='''<b>Date</b>: %{customdata}</b><br><b>Day of Outbreak</b>: %{text}<br>
		    <br><b>Location</b>: %{meta}<br><b>Value:</b>: %{y}<extra></extra>'''

		    for i in range(0, len(county_options_menu)):
		    	tab_1_data.append(go.Scatter(mode="lines+markers", marker_color=colors[i],
	                x=day_text,
	                y=y_data[i],
	                customdata = date_text,
	                text = day_text,
	                name = county_options_menu[i],
	                meta= county_options_menu[i],
	                hoverlabel={'align': 'left'},
	                hovertemplate=hovertemplate))
		    	# tab_2_data.append(go.Scatter(mode="markers",
	      #           x=day_text,
	      #           y=y_data[i],
	      #           # name="Count",
	      #           opacity=0,
	      #           hoverinfo="skip"))
		    	tab_2_data.append(go.Bar(name = county_options_menu[i], x=day_text, y=y_data[i], marker_color=colors[i],
	                customdata = date_text,
	                text = day_text,
	                meta= county_options_menu[i],
	                hoverlabel={'align': 'left'},
	                hovertemplate=hovertemplate))

		    new_layout["title"] = f"{LABEL_STATS[county_stat_selector]}"
		    new_layout["dragmode"] = "select"
		    new_layout["showlegend"] = True
		    new_layout["autosize"] = True
		    new_layout["barmode"] = "stack"

		    # figure = dict(data=data, layout=new_layout)
		    return tab_1_data, tab_2_data, new_layout

	@app.callback(Output('main_graph_tabs_content', 'children'),
              [
              Input('main_graph_tabs', 'value'),
              Input("main_graph_data", "data"),
              ]
          )
	def render_content(tab, data):
	    tab_1_data = data[0]
	    tab_2_data = data[1]
	    new_layout = data[2]
	    if tab == 'tab-1':
	        return html.Div(
	        			dcc.Graph(
	        				id="line_graph", 
	        				className="main_graphs graph_padding",
	        				figure={
	        					'data': tab_1_data,
	        					'layout': new_layout
	        					}
	        				), 
	        			className="GraphContainer")
	    elif tab == 'tab-2':
	        return html.Div(
	        			dcc.Graph(
	        				id="count_graph", 
	        				className="main_graphs graph_padding",
	        				figure={
	        					'data': tab_2_data,
	        					'layout': new_layout
	        					}
	        				), 
	        			className="GraphContainer")
	    # elif tab == 'tab-3':


### RUN DASHBOARD
# Main
def Add_Dash(server):
	external_stylesheets = [f'/static/css/styles.css',
							f'/static/css/s1.css']
	external_scripts = ['/static/scripts/resizing_script.js']
	app = dash.Dash(server=server, 
					external_stylesheets=external_stylesheets,
					external_scripts=external_scripts,
					routes_pathname_prefix='/',
					meta_tags=[{"name": "viewport", "content": "width=device-width"}])
	app.config.suppress_callback_exceptions = True
	app.layout = application_layout()
	init_callbacks(app)

	return app.server