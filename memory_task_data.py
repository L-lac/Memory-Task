import pandas as pd

file_path = "CBAS0004_ObjectScenePairTask_local_recog_final_2024-12-11_14h33.30.581.xlsx"
def process_memory_task_data(file_path):
""" Creates a functiom that processes the Excel file to generate 4 outputs, each corresponding to its individual run with recognition and study phases """ 
  
  data = pd.read_excel(file_path)
  
  #Identifying when a new run starts and assigns a number to each (1-4)
  data['Run'] = (data['stimulus_start_time'].diff() < 0).cumsum() + 1


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
  data['Material_Type'] = data['CondsFile'].apply(extract_material_type)
    
  #Calculating Response Time
  data['Response_Time'] = data['stimulus_end_time'] - data['stimulus_start_time']

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
  data['Signal_Detection_Type'] = data.apply(signal_detection, axis=1)


  #--- Study Phase ----

  #Onset time when "NewImg" turns into "Studied" --> 2nd stimulus_start_time of each run 
  data['Onset_Time'] = None
  for run in data['Run'].unique():
    #Filters data for the current run
    run_data = data[data['Run'] == run]

    #Gets the stimulus_start_time for the second stimulus
    sorted_times = run_data['stimulus_start_time'].sort_values().unique()
    onset_time = sorted_times[1]  

    #Assigns value to the Onset_Time column of this run
    data.loc[(data['Run'] == run) & (data['stimulus_start_time'] == onset_time), 'Onset_Time'] = onset_time
  
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
  data['Material_Attribute'] = data.apply(classify_material_attribute, axis=1)

  #--- Separating Data By Run ---
  for run in data['Run'].unique():
    # Filter rows for the current run
    run_data = data[data['Run'] == run]

    #Specifying the output coloumns for the recognition and study phase
    output_columns = [
      'Material_Type', 'Response_Time', 'ConType',
      'Condition', 'Recog1_Resp.corr', 'Signal_Detection_Type',
      'Onset_Time', 'Material_Attribute']

    # Save the data for the current run into an Excel file
    output_file_name = f"Run{int(run)}_Memory_Task_Output.xlsx"
    run_data.to_excel(output_file_name, index=False)
    print(f"Saved: {output_file_name}")

#Calling the main function that executes everything 
process_memory_task_data(file_path)
