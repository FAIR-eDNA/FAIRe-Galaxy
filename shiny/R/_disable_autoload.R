# app.R sources the files in this folder itself, after setting the app's folder (faire.app_dir). This
# file stops Shiny also loading them on its own before that (it does so for any R/ folder), which left
# the demonstration data's folder empty when the app was started with Run App in RStudio or
# shiny::runApp().
