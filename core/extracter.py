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

if "__main__" == __name__ :
    filepath = Path(r"samples/01-17-LTsertext/2026-01-17-0203_9-CapObj.ser.txt")
    from pprint import pprint
    cr_metadata= extractmetadata(filepath)
    pprint(cr_metadata)
