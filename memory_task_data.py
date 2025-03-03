import os 
import pandas as pd
import tempfile 
import re
from openpyxl import Workbook
from openpyxl.utils.dataframe import dataframe_to_rows
from openpyxl.styles import Alignment

#File Paths (Time being, will update using globs module) 
recognition_file_path = "CBAS0004_ObjectScenePairTask_local_recog_final_2024-12-11_14h33.30.581.xlsx"
study_file_path = "CBAS0004_ObjectScenePairTask_local_study2_2024-12-11_13h44.35.528.csv"

#Processing data
recognition_data = pd.read_excel(recognition_file_path)
study_data = pd.read_csv(study_file_path)

#Creates ouput folder 
output_folder = "Memory_Task_Outputs"
os.makedirs(output_folder, exist_ok=True)

#Any empty boxes return a NaN --> to fix this we forward fill by assigning it to the last valid previously used time
recognition_data['stimulus_start_time'] = recognition_data['stimulus_start_time'].ffill()

#Identifying when a new run starts and assigns a number to each
recognition_data['Run'] = 1
current_run = 1

#Increment run # by 1 if a reset is detected -> when the current time is < the previous time
for row in range(1, len(recognition_data)):  
  if recognition_data['stimulus_start_time'].iloc[row] < recognition_data['stimulus_start_time'].iloc[row - 1]:
    current_run += 1 
  #Assigns current run number to the row 
  recognition_data.loc[row, 'Run'] = current_run

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

#Calculates Recognition Accuracy by comparing the responses from 'Recog1_Resp.keys' to 'corrAns1'  
def recognition_accuracy(run_data):
  #Substitute '1' with 'num_8' and '2' with 'num_5'
  run_data['Recog1_Resp.keys'] = run_data['Recog1_Resp.keys'].replace({1: 'num_8', 2: 'num_5'})
  #Compare Recog1_Resp.keys with corrAns1 and assign 1 for match, 0 for mismatch
  run_data['Recog1_Resp.corr'] = (run_data['Recog1_Resp.keys'] == run_data['corrAns1']).astype(int)
  #Skip over invalid trials -> "None" 
  run_data.loc[run_data['Recog1_Resp.keys'].isna(), 'Recog1_Resp.corr'] = None
  return run_data
  
#Searches for a Obj, Scn, or Pair ID within ImageFile column of study phase and then matches it to Recognition
#Uses re module to search for strings in a file path (study phase ImageFile column) then matches it to Recognition
def extract_id(filepath):
  match = re.search(r'(Obj\d+|Scn\d+|Pair\d+)', str(filepath), re.IGNORECASE)
  return match.group(1) if match else None
  
#Creates ID column in both datasets using the re module to match later 
recognition_data['ItemID'] = recognition_data['ImageFile'].apply(extract_id)
study_data['ItemID'] = study_data['ImageFile'].apply(extract_id)

#Processes each run to generate final outputs 
for run in recognition_data['Run'].unique():
  run_data = recognition_data[recognition_data['Run'] == run].copy()
  
  #Processing functions + Calculating Response Time
  #axis=1 tells apply() function to run the function we created row by row 
  run_data['Material_Type'] = run_data['CondsFile'].apply(extract_material_type)
  run_data['Duration'] = run_data['stimulus_end_time'] - run_data['stimulus_start_time'] 
  run_data['Signal_Detection_Type'] = run_data.apply(signal_detection, axis=1)
  run_data['Material_Attribute'] = run_data.apply(material_attribute, axis=1) 

  #Rename stimulus_start_time to Onset_Time 
  run_data.rename(columns={'stimulus_start_time': 'Onset_Time'}, inplace=True)

  #Calculate Recognition Accuracy 
  run_data = recognition_accuracy(run_data)
  
  #Specifying columns for Recognition Phase
  recognition_columns = ['Material_Type', 'NewImg', 'ImageFile', 'ItemID', 'ConType', 'Condition', 'Onset_Time', 'Duration', 'Signal_Detection_Type', 'Material_Attribute']
  
  #---- Study Phase Processing ----

  run_study_data = study_data.copy()
  #Renmes stimulus_start_time to Onset_Time
  run_study_data.rename(columns={'stimulus_start_time': 'Onset_Time'}, inplace=True)
  #Study phase duration is always 3 secs
  run_study_data['Duration'] = 3
  
  #Matches study images with recognition phase
  merged_study_data = run_study_data.merge(
    run_data[['NewImg', 'ImageFile','ItemID', 'Material_Type','Condition', 'Signal_Detection_Type', 'Material_Attribute', 'Recog1_Resp.corr']],
    on='ItemID', how='left', suffixes=('_study', '_recog'))

  #Renames recognition accuracy column for study phase
  merged_study_data.rename(columns={'Recog1_Resp.corr': 'Recognition_Accuracy'}, inplace=True)

  #Specifying columns for Study Phase  
  study_columns = ['ImageFile_study', 'ItemID', 'Material_Type', 'Onset_Time', 'Duration', 'Condition', 'Recognition_Accuracy', 'Signal_Detection_Type', 'Material_Attribute']

  #Saves the final output for the current run 
  processed_file_name = os.path.join(output_folder, f"Run{int(run)}_Memory_Task_Output.xlsx")
  
  #--- Using openpyxl to format the headers ---

  wb = Workbook()
  ws = wb.active

  #Creating "Recognition Phase" header + Fixing the formatting 
  recognition_start_col = 1  
  ws.merge_cells(start_row=1, start_column=recognition_start_col, end_row=1, end_column=len(recognition_columns))
  ws.cell(row=1, column=recognition_start_col, value="Recognition Phase")
  ws.cell(row=1, column=recognition_start_col).alignment = Alignment(horizontal='center')

  
  #Using a nested for loop to add Recognition Phase Data created in pandas
 for num_row, row_data in enumerate(dataframe_to_rows(run_data[recognition_columns], index=False, header=True), start=2):
  for num_col, value in enumerate(row_data, start=recognition_start_col):
    ws.cell(row=num_row, column=num_col, value=value)


  #Creating "Study Phase" header + Leaves gap between two phases 
  study_start_col = len(recognition_columns) + 3  
  ws.merge_cells(start_row=1, start_column=study_start_col, end_row=1, end_column=study_start_col + len(study_columns) - 1)
  ws.cell(row=1, column=study_start_col, value="Study Phase")
  ws.cell(row=1, column=study_start_col).alignment = Alignment(horizontal='center')

  #Adding in Study Phase data
  for num_row, row_data in enumerate(dataframe_to_rows(merged_study_data, index=False, header=True), start=2):
    for num_col, value in enumerate(row_data, start=study_start_col):
      ws.cell(row=num_row, column=num_col, value=value)


  #Saving the workbook
  wb.save(processed_file_name)
  print(f"Saved output for Run {run} with openpyxl: {processed_file_name}")

