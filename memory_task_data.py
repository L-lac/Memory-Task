import pandas as pd

file_path = "CBAS0004_ObjectScenePairTask_local_recog_final_2024-12-11_14h33.30.581.xlsx"
data = pd.read_excel(file_path)

#Identifying when a new run starts and assigns a number to each (1-4)
data['Run'] = 1
current_run = 1
print("Differences between consecutive stimulus_start_time values:")
print(data['stimulus_start_time'].diff())
#Starts from the second row
for row in range(1, len(data)):  
  previous_time = data['stimulus_start_time'].iloc[row - 1]
  current_time = data['stimulus_start_time'].iloc[row]
  if current_time < previous_time:
    print(f"New run detected at row {row}: {current_time} (previous: {previous_time})")
    #Increment run # by 1 if a reset is detected -> when the current time is < the previous time
    current_run += 1 
  #Assigns current run number to the row 
  data.loc[row, 'Run'] = current_run
  
print(f"Unique runs detected: {data['Run'].unique()}")
print("First 20 rows of data with Run column:")
print(data[['stimulus_start_time', 'Run']].head(20))

#Debugging
data.to_excel("Full_Data_With_Runs.xlsx", index=False)
print("Saved data with run numbers to Full_Data_With_Runs.xlsx")

#--- Processing Each Run ---  
for run in data['Run'].unique():
  #Filters each row for the current run 
  run_data = data[data['Run'] == run].copy()
  output_file_name = f"Run{int(run)}_Raw.xlsx"
  run_data.to_excel(output_file_name, index=False)
  print(f"Saved: {output_file_name}")

  
  #--- Recognition Phase ---

  #Extracts Material Type from CondsFile column 
  def extract_material_type(row):
    if "object" in str(row).lower():
      return "Object"
    elif "scene" in str(row).lower():
      return "Scene"
    elif "pair" in str(row).lower():
      return "Pair"
    else:
      return None
  #runs the function we created above 
  run_data['Material_Type'] = run_data['CondsFile'].apply(extract_material_type)
    
  #Calculating Response Time
  run_data['Response_Time'] = run_data['stimulus_end_time'] - run_data['stimulus_start_time']

  #Signal Detection Theory: 1 = correct response, 0 = incorrect  
  def signal_detection(row):
    #Old pics: 1 = Hit, 0 = Miss
    if row['Condition'] == 'Old':
      return 'Hit' if row['Recog1_Resp.corr'] == 1 else 'Miss'

    #New / Lure Pics: 1 = Correct Rejection (CR), 0 = False Alarm (FA)
    #Combined Condition to group together New and Lure 
    elif row['Condition'] in ['New', 'Lure']:
      return 'CR' if row['Recog1_Resp.corr'] == 1 else 'FA'
    else:
      return None
        
  #axis=1 tells apply() function to run the function we created row by row 
  run_data['Signal_Detection_Type'] = run_data.apply(signal_detection, axis=1)
  

  #--- Study Phase ----

  #Onset time when "NewImg" turns into "Studied" --> 2nd stimulus_start_time of each run 
  run_data['Onset_Time'] = None
  run_data.loc[run_data.index[1], 'Onset_Time'] = run_data['stimulus_start_time'].iloc[1]
    
  #living/nonliving, indoor/outdoor, likely/unlikely 
  def material_attribute(row):
    """Classifies if the material attribute is 8=living / 5=nonliving, 8=indoor / 5=outdoor, or 8=likely / 5=unlikely 
    based on if the Material_Type is an Object, Scene, or Pair. """
    
    #When the numer = 8
    if row['Recog1_Resp.keys'] == 'num_8':
      if row['Material_Type'] == 'Object':  
        return 'Living'
      elif row['Material_Type'] == 'Scene':  
        return 'Indoor'
      elif row['Material_Type'] == 'Pair':  
        return 'Likely'

    #When the number = 5
    elif row['Recog1_Resp.keys'] == 'num_5':
      if row['Material_Type'] == 'Object':  
        return 'Nonliving'
      elif row['Material_Type'] == 'Scene': 
        return 'Outdoor'
      elif row['Material_Type'] == 'Pair': 
        return 'Unlikely'
    return None
    
  #Creates Material_Attribute column 
  run_data['Material_Attribute'] = run_data.apply(material_attribute, axis=1)

  #Specifying the output coloumns for the recognition and study phase
  output_columns = [
    'Material_Type', 'Response_Time', 'ConType',
    'Condition', 'Recog1_Resp.corr', 'Signal_Detection_Type',
    'Onset_Time', 'Material_Attribute']

  #Saves the data for the current run into an Excel file
  processed_file_name = f"Run{int(run)}_Memory_Task_Output.xlsx"
  run_data[output_columns].to_excel(processed_file_name, index=False)
  print(f"Saved: {processed_file_name}")

