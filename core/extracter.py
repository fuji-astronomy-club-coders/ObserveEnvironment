import re
from datetime import datetime
from pathlib import Path

from utils import loadCsv2dList, save2dListCsv


def extractmetadata(path: Path) -> dict:
    """
    asiの作成するtxtファイルからメタデータをdict形式で抽出します
    """
    with open(str(path), "r", encoding="utf-8") as f:
        lines = f.readlines()

    extracted_metadata = {}

    for i, line in enumerate(lines):
        if "=" not in line:
            print(f"無効な行としてskipします L{i}: {line}")
        else:
            item, value = line.split("=")
            extracted_metadata[item.strip()] = value.strip()

    return extracted_metadata


def savemetadata(metadata: dict, output: Path) -> None:
    """
    既存または新しいcsvにメタデータを書き込みます
    """
    clm, lin = 1, 0
    transed_data = [[]]
    exs_headers = ["ID"]
    if output.exists() and output.is_file():
        existing = loadCsv2dList(output)
        if existing:
            exs_headers = existing[0]
            clm = len(exs_headers)
            exs_data = existing[1:]
            lin = len(exs_data)
            transed_data = [list(row) for row in zip(*exs_data)]

    metadata["ID"] = lin + 1

    new_headers = [k for k in metadata.keys() if k not in exs_headers]
    headers = exs_headers + list(new_headers)

    print("header", headers)
    new_clms = [[""] * lin for _ in range(len(headers) - clm)]
    data = transed_data + new_clms
    for i, h in enumerate(headers):
        val = metadata.get(h, "")
        print("val", val)
        data[i].append(val)

    print("data", data)
    table = [headers] + [list(row) for row in zip(*data)]
    print("table", table)
    save2dListCsv(table, output)

def is_valid_capobj_filename(
    filename: str, 
    cap_objs: list[str] = ["CapObj"], 
    exts: list[str] = ["ser", "AVI", "jpg", "tiff"]
) -> bool:
    """
    天体撮影メタデータファイルの命名形式に適合しているかを判定する。
    想定フォーマット: YYYY-MM-DD-hhmm_frame-CapObj.ext.txt
    
    :param filename: 判定対象のファイル名（パスが含まれていてもファイル名部分を取り出して判定）
    :param cap_objs: CapObj部分の許容文字列リスト
    :param exts: 拡張子（ser, AVI等）の許容文字列リスト
    :return: 形式に適合していればTrue、さもなければFalse
    """
    # パスが含まれている場合はファイル名のみを取得
    filename_only = filename.split("/")[-1].split("\\")[-1]
    
    # 特殊文字のエスケープ処理とOR条件の構築
    escaped_objs = [re.escape(obj) for obj in cap_objs]
    escaped_exts = [re.escape(ext) for ext in exts]
    
    objs_pattern = "|".join(escaped_objs)
    exts_pattern = "|".join(escaped_exts)
    
    # 正規表現パターンの作成
    # 1. YYYY-MM-DD-hhmm (日付・時刻)
    # 2. _([0-9]+) (フレーム番号等の数字)
    # 3. -(CapObj) (キャプチャオブジェクト指定)
    # 4. .(ext).txt (拡張子および固定の.txt)
    pattern = rf"^(\d{{4}}-\d{{2}}-\d{{2}}-\d{{4}})_(\d+)-({objs_pattern})\.({exts_pattern})\.txt$"
    
    match = re.match(pattern, filename_only, re.IGNORECASE)
    if not match:
        return False
    
    # 日時部分を取り出して実在する日時か検証（例: 2月30日などを除外）
    dt_str = match.group(1)
    try:
        datetime.strptime(dt_str, "%Y-%m-%d-%H%M")
    except ValueError:
        return False
        
    return True

def compile_daily_metadata(
    folder_path: Path, 
    output_csv: Path, 
    cap_objs: list[str] = ["CapObj"], 
    exts: list[str] = ["ser", "AVI", "jpg", "tiff"]
) -> None:
    """
    指定されたフォルダ内の撮影メタデータファイル(.txt)をすべて読み込み、
    一つのCSVファイルにまとめます。
    
    :param folder_path: メタデータファイルが格納されている1日分のフォルダのパス
    :param output_csv: 出力するCSVファイルのパス
    :param cap_objs: CapObj部分の許容文字列リスト
    :param exts: 拡張子（ser, AVI等）の許容文字列リスト
    """
    if not folder_path.exists() or not folder_path.is_dir():
        print(f"ディレクトリが存在しないか、無効なパスです: {folder_path}")
        return

    # フォルダ内のすべての.txtファイルを取得
    for file_path in folder_path.glob("*.txt"):
        if is_valid_capobj_filename(file_path.name, cap_objs, exts):
            cr_metadata={}
            
            cr_metadata.update({"OriginalFilename":file_path.name,"":""})
            cr_metadata.update(extractmetadata(file_path))
            
            savemetadata(cr_metadata, output_csv)
            
if "__main__" == __name__:
    """   
    # 既存の単一ファイル処理のテスト
    filepath = Path(r"samples/01-17-LTsertext/2026-01-17-0203_9-CapObj.ser.txt")
    from pprint import pprint

    cr_metadata = extractmetadata(filepath)
    pprint(cr_metadata)

    outfilename = str(filepath.name.split(".", 1)[0]) + ".csv"
    outputdir = Path("samples") / "result" / "metadata"
    outputdir.mkdir(parents=True, exist_ok=True)
    savemetadata(cr_metadata, outputdir / outfilename)
    """
    from tkinter.filedialog import askdirectory
    # 追加した一括処理のテスト
    target_folder = Path(askdirectory()).absolute()
    daily_csv_output = target_folder / f"{target_folder}_daily_metadata.csv"
    compile_daily_metadata(target_folder, daily_csv_output)