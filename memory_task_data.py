import pandas as pd

def process_memory_task_data(file_path):
""" Creates a functiom that processes the Excel file to generate 4 outputs, each corresponding to its individual run with recognition and study phases """ 

  data = pd.read_excel(file_path)
  
  #Identifying when a new run starts 
  data['Run'] = (data['stimulus_start_time'].diff() < 0).cumsum() + 1

  #Loops through each run 
  for run in data['Run'].unique():
    # Filter rows for the current run
    run_data = data[data['Run'] == run]

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
        if row['Recog1_Resp.corr'] == 1:
          return 'Hit'
        else : return "Miss'

      #New / Lure Pics: 1 = Correct Rejection (CR), 0 = False Alarm (FA)
      #Combined Condition to group together New and Lure 
      elif row['Condition'] in ['New', 'Lure']:
        if row['Recog1_Resp.corr'] == 1:
          return 'CR'
        else: return 'FA'
    #axis=1 tells apply() function to run the function we created row by row 
    run_data['Signal_Detection_Type'] = run_data.apply(classify_signal_detection, axis=1)

    #--- Study Phase ----
    #Onset time when "NewImg" turns into "Studied"
    
