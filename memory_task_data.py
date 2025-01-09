import os
import pandas as pd

file_path = "CBAS0004_ObjectScenePairTask_local_recog_final_2024-12-11_14h33.30.581.xlsx"
data = pd.read_excel(file_path)
#Creates ouput folder 
output_folder = "Memory_Task_Outputs"
os.makedirs(output_folder, exist_ok=True)

#Any empty boxes return a NaN --> to fix this we forward fill by assigning it to the last valid previously used time
data['stimulus_start_time'] = data['stimulus_start_time'].fillna(method='ffill')

#Identifying when a new run starts and assigns a number to each (1-4)
data['Run'] = 1
current_run = 1
#Starts from the second row
for row in range(1, len(data)):  
  #Increment run # by 1 if a reset is detected -> when the current time is < the previous time
  if data['stimulus_start_time'].iloc[row] < data['stimulus_start_time'].iloc[row - 1]:
    current_run += 1 
  #Assigns current run number to the row 
  data.loc[row, 'Run'] = current_run

#--- Processing Each Run ---  
for run in data['Run'].unique():
  #Filters each row for the current run 
  run_data = data[data['Run'] == run].copy()
  output_file_name = f"Run{int(run)}_Raw.xlsx"
  run_data.to_excel(output_file_name, index=False)
  
#--- Recognition Phase ---

#Extracts Material Type from CondsFile column 
def extract_material_type(row):
  if "object" in str(row).lower(): return "Object"
  elif "scene" in str(row).lower(): return "Scene"
  elif "pair" in str(row).lower(): return "Pair"
  else: return None

#Signal Detection Theory: 1 = correct response, 0 = incorrect  
def signal_detection(row):
  #Old pics: 1 = Hit, 0 = Miss
  if row['Condition'] == 'Old':
    return 'Hit' if row['Recog1_Resp.corr'] == 1 else 'Miss'

  #New / Lure Pics: 1 = Correct Rejection (CR), 0 = False Alarm (FA)
  #Combined Condition to group together New and Lure 
  elif row['Condition'] in ['New', 'Lure']:
    return 'CR' if row['Recog1_Resp.corr'] == 1 else 'FA'
  else: return None
#-----------------------------------------

#living/nonliving, indoor/outdoor, likely/unlikely 
#Part of Study Phase
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
  
#Processes each previously stored Excel file to generate final outputs 
for run in data['Run'].unique():
  run_file_name = f"Run{int(run)}_Raw.xlsx"
  run_data = pd.read_excel(run_file_name)
  
  #Processing functions + Calculating Response Time
  #axis=1 tells apply() function to run the function we created row by row 
  run_data['Material_Type'] = run_data['CondsFile'].apply(extract_material_type)
  run_data['Response_Time'] = run_data['stimulus_end_time'] - run_data['stimulus_start_time'] 
  run_data['Signal_Detection_Type'] = run_data.apply(signal_detection, axis=1)
  run_data['Material_Attribute'] = run_data.apply(material_attribute, axis=1) 

  #Rename stimulus_start_time to Onset_Time
  #Part of Study Phase 
  run_data.rename(columns={'stimulus_start_time': 'Onset_Time'}, inplace=True)

  #Specifying the output coloumns for the recognition and study phase
  output_columns = [
    'Material_Type', 'Response_Time', 'ConType',
    'Condition', 'Recog1_Resp.corr', 'Signal_Detection_Type',
    'Onset_Time', 'Material_Attribute']

  run_data = run_data[output_columns]

  #Saves the final output for the current run 
  processed_file_name = os.path.join(output_folder, f"Run{int(run)}_Memory_Task_Output.xlsx")
  run_data[output_columns].to_excel(processed_file_name, index=False)
  print(f"Saved: {processed_file_name}")

