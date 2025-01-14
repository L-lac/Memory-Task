# 🧠 Memory Task Data Processing

## 🎲 Project Overview:
This project processes memory task data containing Recognition and Study phase information. The recognition phase contains all conditions, while the study phase only contains old and lure conditions. The script automates key processing tasks, such as identifying experimental runs, extracting metrics, and generating well-organized Excel outputs.

## 🛠️ Tools and Libraries Used:
1. pandas:
- Handles data loading, manipulation, and filtering.
- Provides robust tools for data transformations, such as calculating response times and filtering conditions.

2. openpyxl:
- Generates Excel outputs with advanced formatting, including merged headers and column alignment.

## 📂 How It Works:
1. Data Loading: reads the inputted file using pandas.
2. Run Detection: Identifies unique runs by analyzing stimulus_start_time. The onset time of each stimulus increases linearly, thus by detecting when there is a sudden "drop/reset" we can identify the start of a new run.
3. Recognition Phase Processing: Extracts material type, calculates response times, and applies signal detection theory classifications.
4. Study Phase Processing: Filters the recognition data for only the old and lure conditions, adds onset times (3 secs), extracts the material attributes, and recognition accuracy based on the recognition phase. 
5. Excel Outputs: Combines recognition and study phase results into a Excel file, unique to each run.

## 📜 Key Functions:
```python
def extract_material_type(row):
    if "object" in str(row).lower(): return "Object"
    elif "scene" in str(row).lower(): return "Scene"
    elif "pair" in str(row).lower(): return "Pair"
    else: return None
```
#### Purpose: identifies whether a stimulus is an object, scene, or pair
- Example input: object_1
- Output: object

```python
def signal_detection(row):
  if row['Condition'] == 'Old':
        return 'Hit' if row['Recog1_Resp.corr'] == 1 else 'Miss'
    elif row['Condition'] in ['New', 'Lure']:
        return 'CR' if row['Recog1_Resp.corr'] == 1 else 'FA'
    else: return None
```
#### Purpose: categorizes responses based on recognition accuracy 
- Old condition: Hit or Miss
- New/Lure: Correct Rejection (CR) or False Alarm (FA)

```python
def material_attribute(row):
  if row['Recog1_Resp.keys'] == 'num_8':
    if row['Material_Type'] == 'Object': return 'Living'
    if row['Material_Type'] == 'Scene': return 'Indoor'
    if row['Material_Type'] == 'Pair': return 'Likely'
  elif row['Recog1_Resp.keys'] == 'num_5':
    if row['Material_Type'] == 'Object': return 'Nonliving'
    if row['Material_Type'] == 'Scene': return 'Outdoor'
    if row['Material_Type'] == 'Pair': return 'Unlikely'
  return None
```
#### Purpose: Assigns material attribtues based on the material type 
- Object: 8 = living, 5 = nonliving
- Scene: 8 = inside, 5 = outside
- Pair: 8 = likely, 5 = unlikely

## 📬 Contact:
If you have any questions or feedback please contact Lena Lin 😊

