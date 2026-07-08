app_name = "boardgame_cafe"
app_title = "Board Game Cafe"
app_publisher = "Sathvik"
app_description = "Table and game management app for any board game themed cafe"
app_email = "nsathvik2007@gmail.com"
app_license = "mit"

# Apps
# ------------------

# required_apps = []

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "boardgame_cafe",
# 		"logo": "/assets/boardgame_cafe/logo.png",
# 		"title": "Board Game Cafe",
# 		"route": "/boardgame_cafe",
# 		"has_permission": "boardgame_cafe.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/boardgame_cafe/css/boardgame_cafe.css"
# app_include_js = "/assets/boardgame_cafe/js/boardgame_cafe.js"

# include js, css files in header of web template
# web_include_css = "/assets/boardgame_cafe/css/boardgame_cafe.css"
# web_include_js = "/assets/boardgame_cafe/js/boardgame_cafe.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "boardgame_cafe/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "boardgame_cafe/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "boardgame_cafe.utils.jinja_methods",
# 	"filters": "boardgame_cafe.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "boardgame_cafe.install.before_install"
# after_install = "boardgame_cafe.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "boardgame_cafe.uninstall.before_uninstall"
# after_uninstall = "boardgame_cafe.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "boardgame_cafe.utils.before_app_install"
# after_app_install = "boardgame_cafe.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "boardgame_cafe.utils.before_app_uninstall"
# after_app_uninstall = "boardgame_cafe.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "boardgame_cafe.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
# 	"ToDo": "custom_app.overrides.CustomToDo"
# }

# Document Events
# ---------------
# Hook on document methods and events

# doc_events = {
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
# 	}
# }

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"boardgame_cafe.tasks.all"
# 	],
# 	"daily": [
# 		"boardgame_cafe.tasks.daily"
# 	],
# 	"hourly": [
# 		"boardgame_cafe.tasks.hourly"
# 	],
# 	"weekly": [
# 		"boardgame_cafe.tasks.weekly"
# 	],
# 	"monthly": [
# 		"boardgame_cafe.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "boardgame_cafe.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "boardgame_cafe.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "boardgame_cafe.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["boardgame_cafe.utils.before_request"]
# after_request = ["boardgame_cafe.utils.after_request"]

# Job Events
# ----------
# before_job = ["boardgame_cafe.utils.before_job"]
# after_job = ["boardgame_cafe.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"boardgame_cafe.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

# Translation
# ------------
# List of apps whose translatable strings should be excluded from this app's translations.
# ignore_translatable_strings_from = []

permission_query_conditions = {
    "Customer Session": "boardgame_cafe.board_game_cafe.doctype.customer_session.customer_session.get_permission_query_conditions",
    "Game Checkout": "boardgame_cafe.board_game_cafe.doctype.game_checkout.game_checkout.get_permission_query_conditions",
    "Food Order": "boardgame_cafe.board_game_cafe.doctype.food_order.food_order.get_permission_query_conditions",
}

