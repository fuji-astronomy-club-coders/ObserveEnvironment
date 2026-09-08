from pathlib import Path

from utils import loadCsv2dList, save2dListCsv


def extractmetadata(path:Path) -> dict :
    """
    asiの作成するtxtファイルからメタデータをdict形式で抽出します
    """
    with open(str(path), 'r', encoding='utf-8') as f:
        lines = f.readlines()

    extracted_metadata = {}

    for i,line in enumerate(lines):
        if "=" not in line:
            print(f"無効な行としてskipします L{i}: {line}")
        else:
            item,value =line.split("=")
            extracted_metadata[item.strip()] = value.strip()

    return extracted_metadata

def savemetadata(metadata:dict, output:Path) -> None :
    """
    既存または新しいcsvにメタデータを書き込みます
    """
    clm,lin = 1,0
    transed_data=[[]]    
    exs_headers = ["ID"]
    if output.exists() and output.is_file():
        existing = loadCsv2dList(output)
        if existing : 
            exs_headers = existing[0]
            clm = len(exs_headers)
            exs_data=existing[1:]
            lin = len(exs_data)
            transed_data=[list(row) for row in zip(*exs_data)]

    metadata["ID"] = lin + 1

    new_headers = [k for k in metadata.keys() if k not in exs_headers]
    headers = exs_headers + list(new_headers)

    print("header",headers)
    new_clms = [[""] * lin for _ in range(len(headers) - clm)]
    data =  transed_data + new_clms
    for i,h in enumerate(headers):
        val = metadata.get(h,"")
        print("val",val)
        data[i].append(val)

    print("data",data)
    table = [headers] + [list(row) for row in zip(*data)]
    print("table",table)
    save2dListCsv(table,output)

if "__main__" == __name__ :
    filepath = Path(r"samples/01-17-LTsertext/2026-01-17-0203_9-CapObj.ser.txt")
    from pprint import pprint
    cr_metadata= extractmetadata(filepath)
    pprint(cr_metadata)

    outfilename = str(filepath.name.split(".",1)[0])+".csv"
    outputdir = Path("samples") / "result" / "metadata" 
    outputdir.mkdir(parents=True, exist_ok=True)
    savemetadata(cr_metadata,outputdir/outfilename)