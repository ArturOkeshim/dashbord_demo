import pandas as pd
from pathlib import Path

def main(filename):
    path = Path(filename)
    data = pd.read_excel(path)
    
    num_rows = len(data)
    start_data = []
    extracted_data = []
    obj = ""
    line = ""
    list_of_lines = ["50.01","50.02","51"]
    list_of_obj = ["МПЦ"]
    for row in range(num_rows):
        
        cell_text = str(data.iloc[row,0]).strip()

        if cell_text in list_of_lines:
            line = cell_text
            start_debet_sub = data.iloc[row,2]
            start_credit_sub = data.iloc[row,3]
            start_data.append({
                "line": cell_text,
                "debet": start_debet_sub,
                "credit": start_credit_sub
            })

        if cell_text in list_of_obj:
            obj = cell_text
            start_debet_obj = data.iloc[row,2]
            start_credit_obj = data.iloc[row,3]
            start_data.append({
                "line": line,
                "obj": obj,
                "debet": start_debet_obj,
                "credit": start_credit_obj
            })

        if "Обороты за" in cell_text:
            search_item_index = 1
            item = data.iloc[row-search_item_index,0]

            while pd.isna(item) or str(item).strip() == "" or "Обороты за" in str(item):
                search_item_index +=1
                item = data.iloc[row-search_item_index,0]

            date_str = cell_text.replace("Обороты за","").strip()
            date = pd.to_datetime(date_str, format="%d.%m.%y", errors="coerce")

            debet =  data.iloc[row+1,2]
            credit = data.iloc[row+1,3]

            extracted_data.append({
                "line":line,
                "obj":obj,
                "item":item,
                "date":date,
                "debet":debet,
                "credit":credit,
            })

    return extracted_data, start_data

#if data.iloc[row,1] == "Оборот":        


if __name__ == "__main__":

    all_turnover = []
    all_start = []
    filenames = ["50_МПЦ.xls","51_МПЦ.xls"]

    for filename in filenames:
        turnover, start = main(filename=filename)
        all_turnover.extend(turnover)
        all_start.extend(start)

    df_turnover = pd.DataFrame(all_turnover)
    df_start = pd.DataFrame(all_start)

    with pd.ExcelWriter("report.xlsx", engine="openpyxl") as writer:
        df_turnover.to_excel(writer, sheet_name="Оборот", index=False)
        df_start.to_excel(writer, sheet_name="Начальное сальдо", index=False)
