import os
import pandas as pd
from openpyxl import Workbook
from openpyxl.utils.dataframe import dataframe_to_rows
from openpyxl.styles import Alignment

file_path = "CBAS0004_ObjectScenePairTask_local_recog_final_2024-12-11_14h33.30.581.xlsx"
data = pd.read_excel(file_path)
#Creates ouput folder 
output_folder = "Memory_Task_Outputs"
os.makedirs(output_folder, exist_ok=True)

#Any empty boxes return a NaN --> to fix this we forward fill by assigning it to the last valid previously used time
data['stimulus_start_time'] = data['stimulus_start_time'].fillna(method='ffill')

#Identifying when a new run starts and assigns a number to each
data['Run'] = 1
current_run = 1

#Increment run # by 1 if a reset is detected -> when the current time is < the previous time
for row in range(1, len(data)):  
  if data['stimulus_start_time'].iloc[row] < data['stimulus_start_time'].iloc[row - 1]:
    current_run += 1 
  #Assigns current run number to the row 
  data.loc[row, 'Run'] = current_run

#Separates each run into its own Excel file for future processing 
for run in data['Run'].unique():
  run_data = data[data['Run'] == run].copy()
  run_file_name = os.path.join(output_folder, f"Run{int(run)}_Raw.xlsx")
  run_data.to_excel(run_file_name, index=False)
  print(f"Saved raw data for Run {run} to {run_file_name}")

#Extracts Material Type from CondsFile column 
def extract_material_type(row):
  if "object" in str(row).lower(): return "Object"
  elif "scene" in str(row).lower(): return "Scene"
  elif "pair" in str(row).lower(): return "Pair"
  else: return None

#Signal Detection Theory: Based on Recog1_Resp.corr column -> 1 = correct response, 0 = incorrect  
def signal_detection(row):
  
  #Old pics: 1 = Hit, 0 = Miss
  if row['Condition'] == 'Old':
    return 'Hit' if row['Recog1_Resp.corr'] == 1 else 'Miss'

  #New / Lure Pics: 1 = Correct Rejection (CR), 0 = False Alarm (FA)
  #Combined Condition to group together New and Lure 
  elif row['Condition'] in ['New', 'Lure']:
    return 'CR' if row['Recog1_Resp.corr'] == 1 else 'FA'
  else: return None

#Determines if the material type is living/nonliving, indoor/outdoor, or likely/unlikely 
def material_attribute(row):
  """Classifies if the material attribute is 8=living / 5=nonliving, 8=indoor / 5=outdoor, or 8=likely / 5=unlikely 
  based on if the Material_Type is an Object, Scene, or Pair. """
    
  #When the numer = 8
  if row['corrAns1'] == 'num_8':
    if row['Material_Type'] == 'Object': return 'Living'
    if row['Material_Type'] == 'Scene': return 'Indoor'
    if row['Material_Type'] == 'Pair': return 'Likely'

  #When the number = 5
  elif row['corrAns1'] == 'num_5':
    if row['Material_Type'] == 'Object': return 'Nonliving'
    if row['Material_Type'] == 'Scene': return 'Outdoor'
    if row['Material_Type'] == 'Pair': return 'Unlikely'
  return None
  
#Processes each run to generate final outputs 
for run in data['Run'].unique():
  run_file_name = os.path.join(output_folder, f"Run{int(run)}_Raw.xlsx")  # This creates the full path
  print(f"Reading raw file: {run_file_name}")  # Debugging log to confirm the file path
  run_data = pd.read_excel(run_file_name)
  
  #Processing functions + Calculating Response Time
  #axis=1 tells apply() function to run the function we created row by row 
  run_data['Material_Type'] = run_data['CondsFile'].apply(extract_material_type)
  run_data['Response_Time'] = run_data['stimulus_end_time'] - run_data['stimulus_start_time'] 
  run_data['Signal_Detection_Type'] = run_data.apply(signal_detection, axis=1)
  run_data['Material_Attribute'] = run_data.apply(material_attribute, axis=1) 

  #Rename stimulus_start_time to Onset_Time 
  run_data.rename(columns={'stimulus_start_time': 'Onset_Time'}, inplace=True)

  #Specifying columns for Recognition Phase
  recognition_columns = [
    'Material_Type', 'NewImg', 'ConType', 'Condition', 'Onset_Time', 'Response_Time', 'Signal_Detection_Type', 'Material_Attribute' ]
  
  #---- Study Phase Processing ----

  #Filters Recognition data to exclude all rows corresponding to new images and derives recognition accuracy based on data within the recognition phase 
  study_data = run_data[run_data['NewImg'] == 'Studied'].copy()

  #Renames Recog1_Resp.corr column to Recognition_Accuracy 
  study_data.rename(columns={'Recog1_Resp.corr': 'Recognition_Accuracy'}, inplace=True)
  
  #Onset time is always 3 secs
  study_data['Onset_Time'] = 3  

  #Specifying columns for Study Phase  
  study_columns = [
    'NewImg', 'Onset_Time', 'Condition', 'Recognition_Accuracy', 'Signal_Detection_Type', 'Material_Attribute' ]

  #Saves the final output for the current run 
  processed_file_name = os.path.join(output_folder, f"Run{int(run)}_Memory_Task_Output.xlsx")
  
  #--- Using openpyxl to format the headers ---

  wb = Workbook()
  ws = wb.active

  #Creating the "Recognition Phase" header + Adding the columns created in Pandas
  ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=len(recognition_columns))
  ws.append(["Recognition Phase"])
  ws.cell(row=1, column=1).alignment = Alignment(horizontal='center')
  
  for row in dataframe_to_rows(run_data[recognition_columns], index=False, header=True):
    ws.append(row)

  #Creating "Study Phase" header + loading in columns 
  study_start_col = len(recognition_columns) + 1
  ws.merge_cells(start_row=1, start_column=study_start_col, end_row=1, end_column=study_start_col + len(study_columns) - 1)
  ws.append(["Study Phase"])
  ws.cell(row=1, column=study_start_col).alignment = Alignment(horizontal='center')
    
  for row in dataframe_to_rows(study_data[study_columns], index=False, header=True):
    ws.append(row)

  #Saving the workbook
  wb.save(processed_file_name)
  print(f"Saved combined output for Run {run} with headers: {processed_file_name}")

