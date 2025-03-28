import os 
import glob
import pandas as pd
from openpyxl import Workbook
from openpyxl.utils.dataframe import dataframe_to_rows

#Detects the Mac running it and sets the base directory automatically
mac_username = os.popen("whoami").read().strip()
base_directory = f"/Users/{mac_username}/Documents/Experiment_Data/data"

#Asks user to input which participants they wish to process
selected_subjects = input("\nPlease Enter the Participant IDs you wish to process (separate with a comma) -> Ex: CBAS0001, CBAS0004: ").split(",")

def find_behavioral_files(beh_directory):
  """
  Finds the correct Recognition and Study phase files.
  - Recognition: Selects only the `.csv` file with `recog_final`.
  - Study: Selects only the `.csv` file with `study2`.
  """
  recog_files = sorted(glob.glob(os.path.join(beh_directory, "*_ObjectScenePairTask_local_recog_final_*.csv")))
  recog_file = next(
    (file for file in recog_files if not any(suffix in file for suffix in ["recogblocks", "recogrun", "recogtrial"])),
    None )

  study_files = sorted(glob.glob(os.path.join(beh_directory, "*_ObjectScenePairTask_local_study2_*.csv")))
  study_file = next(
    (file for file in study_files if not any(suffix in file for suffix in ["studyblock", "studytrial", "runs"])),
    None )

  return recog_file, study_file if recog_file and study_file else (None, None)

#Process each participant selected 
for subject in selected_subjects:
  subject = subject.strip()
  subject_path = os.path.join(base_directory, subject, "Time1")

  #Makes sure `Time1` exists, ignore `Time2`
  if not os.path.exists(subject_path):
    print(f"Skipping {subject} - No 'Time1' folder found.")
    continue

  #Locate `beh/` folder inside `Time1`
  beh_folder = os.path.join(subject_path, "beh")
  if not os.path.exists(beh_folder):
    print(f"Skipping {subject} - 'beh' folder not found.")
    continue

  #Find the Recognition & Study files
  recog_file, study_file = find_behavioral_files(beh_folder)
  if not recog_file or not study_file:
    print(f"Skipping {subject} - Missing required input files in {beh_folder}")
    continue

  print(f"\nProcessing {subject} - Recognition: {recog_file}, Study: {study_file}")

  #Creating output folders in beh
  output_folder = os.path.join(beh_folder, "Memory_Task_Outputs")
  timing_folder = os.path.join(beh_folder, "Memory_Task_Timing_Files")
  os.makedirs(output_folder, exist_ok=True)
  os.makedirs(timing_folder, exist_ok=True)

  #Load the input recognition and study files 
  data = pd.read_csv(recog_file, encoding='utf-8-sig')
  study_input_data = pd.read_csv(study_file, encoding='utf-8-sig')
  study_input_data.columns = study_input_data.columns.str.strip().str.lower()

  #Any empty boxes return a NaN --> to fix this we forward fill by assigning it to the last valid previously used time
  data['stimulus_start_time'] = data['stimulus_start_time'].ffill()

  #Identifying when a new run starts and assigns a number to each
  data['Run'] = 1
  current_run = 1

  #Increment run # by 1 if a reset is detected -> when the current time is < the previous time
  for row in range(1, len(data)):  
    if data['stimulus_start_time'].iloc[row] < data['stimulus_start_time'].iloc[row - 1]:
      current_run += 1 
      #Assigns current run number to the row 
      data.loc[row, 'Run'] = current_run

  #Extracts Material Type from CondsFile column 
  def extract_material_type(row):
    if "object" in str(row).lower(): return "Object"
    elif "scene" in str(row).lower(): return "Scene"
    elif "pair" in str(row).lower(): return "Pair"
    else: return None

  #Determines the condition based on the NewImg and ConType columns 
  def determine_condition(row):
    if pd.isna(row['NewImg']): return None
    if row['NewImg'] == 'New': return 'New'
    if row['NewImg'] == 'Studied':
        if row['ConType'] == 1: return 'Old'
        if row['ConType'] > 1: return 'Lure'
    return None
    
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
    
    #When the number = 8
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

  def extract_stimulus_start_time(imagefile):
    #Skips over the empty ones + extracts the Obj, Scn, Pair ID from Imagefile 
    if pd.isna(imagefile): return None
    parts = imagefile.split("/")
    if len(parts) > 1:
      image_id = parts[-1].split("_")[0]  
    else: return None
   #Matches the ID to the one in Recognition phase, if it is a match -> extract stimulus_start_time from input study file    
    matched_row = study_input_data[study_input_data['imagefile'].astype(str).str.contains(image_id, regex=False, na=False)]
    if not matched_row.empty: 
      return matched_row['stimulus_start_time'].dropna().values[0] if 'stimulus_start_time' in study_input_data.columns else None
    return None  
  
  #Processes each run to generate final outputs 
  for run in data['Run'].unique():
    run_data = data[data['Run'] == run].copy()
  
    #Processing functions + Calculating Response Time
    #axis=1 tells apply() function to run the function we created row by row 
    run_data['Condition'] = run_data.apply(determine_condition, axis=1)
    run_data['Material_Type'] = run_data['CondsFile'].apply(extract_material_type)
    run_data['Duration'] = run_data['stimulus_end_time'] - run_data['stimulus_start_time'] 
    run_data['Signal_Detection_Type'] = run_data.apply(signal_detection, axis=1)
    run_data['Material_Attribute'] = run_data.apply(material_attribute, axis=1) 

    #Rename stimulus_start_time to Onset_Time 
    run_data.rename(columns={'stimulus_start_time': 'Onset_Time'}, inplace=True)

    #Calculate Recognition Accuracy 
    run_data = recognition_accuracy(run_data)
    run_data.rename(columns={'Recog1_Resp.corr': 'Recognition_Accuracy'}, inplace=True)
  
    #Specifying columns for Recognition Phase
    recognition_columns = ['Material_Type', 'NewImg', 'ImageFile', 'ConType', 'Condition', 'Recognition_Accuracy', 'Onset_Time', 'Duration', 'Signal_Detection_Type', 'Material_Attribute']
  
    #---- Study Phase Processing ----
    study_data = run_data[run_data['NewImg'] == 'Studied'].copy()
    study_data['Duration'] = 3  # Study Onset Time is Always 3 Seconds
  
    study_data.columns = study_data.columns.str.strip()
    #Extract stimulus_start_time for study phase
    study_data['stimulus_start_time'] = study_data['ImageFile'].apply(extract_stimulus_start_time)
  
    study_columns = ['Material_Type', 'NewImg', 'ImageFile', 'stimulus_start_time', 'Duration', 'Condition', 'Recognition_Accuracy', 'Signal_Detection_Type', 'Material_Attribute']

    #Saves the recogntiion phase output of current run 
    recog_file_name = os.path.join(output_folder, f"Run{int(run)}_Recognition.xlsx")
    wb_recog = Workbook()
    ws_recog = wb_recog.active
    ws_recog.title = "Recognition Phase"
    ws_recog.append(recognition_columns)
    
    for row in dataframe_to_rows(run_data[recognition_columns], index=False, header=False):
      ws_recog.append(row)
    
    wb_recog.save(recog_file_name)

    #Saves study phase output for current run 
    study_file_name = os.path.join(output_folder, f"Run{int(run)}_Study.xlsx")
    wb_study = Workbook()
    ws_study = wb_study.active
    ws_study.title = "Study Phase"
    ws_study.append(study_columns)
    
    for row in dataframe_to_rows(study_data[study_columns], index=False, header=False):
      ws_study.append(row)

    wb_study.save(study_file_name)
  print("The study and recognition phase outputs have been generated! 😊")

  #Generate Timing Files
  runs = [1, 2, 3, 4]
  phases = ["Recognition", "Study"]
  material_types = {"Object": "Obj", "Scene": "Scn", "Pair": "Pair"}
  conditions = {
    "Hit": ["Hit"],
    "Miss": ["Miss"],
    "CR": ["CR"],
    "FA": ["FA"],
    "All_Correct": ["Hit", "CR"],
    "All_Wrong": ["Miss", "FA"],
  }

  for run in runs:
    for phase in phases:
      file_name = os.path.join(output_folder, f"Run{run}_{phase}.xlsx")
      if not os.path.exists(file_name): continue

      df = pd.read_excel(file_name)
      required_columns = {'Material_Type', 'Signal_Detection_Type', 'Duration'}
      if phase == "Study": required_columns.add('stimulus_start_time')
      else: required_columns.add('Onset_Time')

      if not required_columns.issubset(df.columns): continue

      for material, short_name in material_types.items():
        material_df = df[df['Material_Type'] == material]
        for condition, condition_values in conditions.items():
          filtered_df = material_df[material_df['Signal_Detection_Type'].isin(condition_values)]

          timing_file = os.path.join(timing_folder, f"{phase}_Run{run}_{short_name}_{condition}.txt")
          with open(timing_file, "w") as f:
            if not filtered_df.empty:
              for _, row in filtered_df.iterrows():
                onset_time = row['stimulus_start_time'] if phase == "Study" else row['Onset_Time']
                parametric_modulation = row['Recognition_Accuracy'] if pd.notna(row['Recognition_Accuracy']) else "missing"
                f.write(f"{onset:.3f} {row['Duration']:.3f} 1\n")

  print("Timing files created! 🥳 ")
