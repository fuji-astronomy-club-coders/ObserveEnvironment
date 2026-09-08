
from pathlib import Path

def extractMetadata(path:Path) -> dict :
    with open(str(Path),'r') as f:
        lines = f.readline()

    metadata = {}

    for i,line in enumerate(lines):
        if "=" not in line:
            print(f"無効な行としてskipします L{i}: {line}")
        else:
            item,value =line.split("=")
            metadata[item.strip()] = value.strip()

    return metadata

if "__main__" == __name__ :
    filepath = Path(r"samples/01-17-LTsertext/2026-01-17-0203_9-CapObj.ser.txt")
    from pprint import pprint
    pprint(extractMetadata(filepath))
