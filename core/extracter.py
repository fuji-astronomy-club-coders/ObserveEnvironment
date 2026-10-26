"""ASI の撮影メタデータを再帰的に収集し、CSV にまとめるモジュール。"""

from __future__ import annotations

import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Sequence

from utils import loadCsv2dList, save2dListCsv

LOGGER = logging.getLogger(__name__)
DEFAULT_CAP_OBJS = ("CapObj",)
DEFAULT_EXTS = ("ser", "AVI", "jpg", "tiff")


def extractmetadata(path: Path) -> dict[str, str]:
    """ASI が作成するテキストファイルからメタデータを抽出する。

    Parameters
    ----------
    path : pathlib.Path
        読み込むメタデータファイル。

    Returns
    -------
    dict[str, str]
        ``key=value`` 形式の行から抽出したメタデータ。
    """
    extracted_metadata: dict[str, str] = {}
    with path.open("r", encoding="utf-8-sig") as file:
        for line_number, line in enumerate(file, start=1):
            if "=" not in line:
                if line.strip():
                    LOGGER.warning("区切り文字 '=' がない行をスキップします: %s:%d", path, line_number)
                continue

            item, value = line.split("=", maxsplit=1)
            item = item.strip()
            if not item:
                LOGGER.warning("キーが空の行をスキップします: %s:%d", path, line_number)
                continue
            extracted_metadata[item] = value.strip()

    return extracted_metadata


def savemetadata(metadata: dict[str, object], output: Path) -> None:
    """既存 CSV にメタデータを 1 レコード追加する。

    既存レコードに存在しない列が追加された場合も、既存行の値を保持しつつ
    新しい列を空欄で補完する。

    Parameters
    ----------
    metadata : dict[str, object]
        追加するメタデータ。
    output : pathlib.Path
        出力 CSV のパス。
    """
    existing: list[list[object]] = []
    if output.exists() and output.is_file():
        existing = loadCsv2dList(output)

    if existing:
        old_headers = [str(header) for header in existing[0]]
        old_rows = existing[1:]
    else:
        old_headers = ["ID"]
        old_rows = []

    record = dict(metadata)
    record["ID"] = len(old_rows) + 1

    headers = list(old_headers)
    for key in record:
        if key not in headers:
            headers.append(key)

    rows: list[list[object]] = []
    for old_row in old_rows:
        old_record = dict(zip(old_headers, old_row))
        rows.append([old_record.get(header, "") for header in headers])
    rows.append([record.get(header, "") for header in headers])

    output.parent.mkdir(parents=True, exist_ok=True)
    save2dListCsv([headers, *rows], output)
    LOGGER.info("CSV にレコードを追加しました: %s (ID=%s)", output, record["ID"])


def is_valid_capobj_filename(
    filename: str,
    cap_objs: Sequence[str] = DEFAULT_CAP_OBJS,
    exts: Sequence[str] = DEFAULT_EXTS,
) -> bool:
    """天体撮影メタデータファイルの命名形式と日時を検証する。

    想定形式は ``YYYY-MM-DD-hhmm_frame-CapObj.ext.txt``。

    Parameters
    ----------
    filename : str
        判定対象のファイル名またはパス。
    cap_objs : Sequence[str], default ("CapObj",)
        ``CapObj`` 部分に許容する文字列。
    exts : Sequence[str], default ("ser", "AVI", "jpg", "tiff")
        撮影データ部分に許容する拡張子。

    Returns
    -------
    bool
        ファイル名と日時が形式に適合する場合は ``True``。
    """
    # Windows パスが POSIX 環境から渡された場合もファイル名を正しく抽出する。
    filename_only = filename.replace("\\", "/").rsplit("/", maxsplit=1)[-1]
    if not cap_objs or not exts:
        return False

    escaped_objs = "|".join(re.escape(obj) for obj in cap_objs)
    escaped_exts = "|".join(re.escape(ext) for ext in exts)
    pattern = (
        rf"^(\d{{4}}-\d{{2}}-\d{{2}}-\d{{4}})_"
        rf"(\d+)-({escaped_objs})\.({escaped_exts})\.txt$"
    )
    match = re.match(pattern, filename_only, re.IGNORECASE)
    if not match:
        return False

    try:
        datetime.strptime(match.group(1), "%Y-%m-%d-%H%M")
    except ValueError:
        return False
    return True


def compile_daily_metadata(
    folder_path: Path,
    output_csv: Path,
    cap_objs: Sequence[str] = DEFAULT_CAP_OBJS,
    exts: Sequence[str] = DEFAULT_EXTS,
    validate_filename: bool = True,
) -> None:
    """選択フォルダとすべてのサブフォルダのメタデータを CSV に集約する。

    ``.txt`` ファイルを再帰的に検索する。``validate_filename`` が真なら
    命名規則に合致するファイルのみ、偽ならファイル名を問わず解析する。
    処理状況と失敗内容はロガーへ出力する。

    Parameters
    ----------
    folder_path : pathlib.Path
        検索対象のルートフォルダ。
    output_csv : pathlib.Path
        集約結果を保存する CSV のパス。
    cap_objs : Sequence[str], default ("CapObj",)
        ファイル名の ``CapObj`` 部分に許容する文字列。
    exts : Sequence[str], default ("ser", "AVI", "jpg", "tiff")
        ファイル名に許容する撮影データの拡張子。
    validate_filename : bool, default True
        真の場合は従来の命名規則による検証を行う。偽の場合は
        ファイル名の形式に関係なく、すべての ``.txt`` を解析する。
    """
    folder_path = folder_path.expanduser().resolve()
    output_csv = output_csv.expanduser().resolve()

    if not folder_path.is_dir():
        LOGGER.error("ディレクトリが存在しないか、無効なパスです: %s", folder_path)
        return

    LOGGER.info("メタデータの検索を開始します: %s", folder_path)
    LOGGER.info(
        "ファイル名の命名規則チェック: %s",
        "有効" if validate_filename else "無効（すべての TXT を解析）",
    )
    LOGGER.info("出力先 CSV: %s", output_csv)

    files_seen = 0
    matched = 0
    processed = 0
    failed = 0

    # rglob により、選択フォルダ直下だけでなくサブフォルダも再帰的に検索する。
    # suffix を使うことで .TXT など大文字拡張子も対象にする。
    for file_path in sorted(folder_path.rglob("*")):
        if not file_path.is_file() or file_path.suffix.casefold() != ".txt":
            continue

        files_seen += 1
        if validate_filename and not is_valid_capobj_filename(
            file_path.name, cap_objs, exts
        ):
            LOGGER.debug("命名形式が一致しないためスキップします: %s", file_path)
            continue

        matched += 1
        LOGGER.info("処理中: %s", file_path)
        try:
            metadata: dict[str, object] = {
                "OriginalFilename": file_path.name,
                "OriginalPath": str(file_path.relative_to(folder_path)),
            }
            metadata.update(extractmetadata(file_path))
            savemetadata(metadata, output_csv)
            processed += 1
        except Exception as exc:
            failed += 1
            LOGGER.exception("ファイルの処理に失敗しました: %s (%s)", file_path, exc)

    LOGGER.info(
        "処理終了: txt=%d, 命名一致=%d, 成功=%d, 失敗=%d, スキップ=%d",
        files_seen,
        matched,
        processed,
        failed,
        files_seen - matched,
    )
    if matched == 0:
        if validate_filename:
            LOGGER.warning("命名規則に一致するメタデータファイルが見つかりませんでした。")
        else:
            LOGGER.warning("解析対象の TXT ファイルが見つかりませんでした。")


def configure_logging(log_path: Path) -> None:
    """コンソールと UTF-8 ログファイルへログを出力する。

    Parameters
    ----------
    log_path : pathlib.Path
        ログファイルの保存先。
    """
    log_path.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(log_path, encoding="utf-8"),
            logging.StreamHandler(),
        ],
        force=True,
    )


def main() -> int:
    """フォルダ選択ダイアログを表示し、メタデータ集約を実行する。

    Returns
    -------
    int
        正常終了時は 0、フォルダ選択キャンセル時は 1。
    """
    import tkinter as tk
    from tkinter import messagebox
    from tkinter.filedialog import askdirectory

    root = tk.Tk()
    root.withdraw()
    try:
        selected_folder = askdirectory(parent=root, title="メタデータを検索するフォルダを選択")
    finally:
        root.destroy()

    # キャンセル時にカレントディレクトリを誤って再帰処理しない。
    if not selected_folder:
        print("フォルダ選択がキャンセルされました。")
        return 1

    target_folder = Path(selected_folder).expanduser().resolve()
    # はい: 命名規則を適用、いいえ: 全 TXT を解析、キャンセル: 終了。
    root = tk.Tk()
    root.withdraw()
    try:
        filename_filter = messagebox.askyesnocancel(
            title="ファイル名の検証",
            message=(
                "ファイル名の命名規則を適用しますか？\n\n"
                "はい：従来の命名規則に一致する TXT のみ解析\n"
                "いいえ：ファイル名を問わず、すべての TXT を解析\n"
                "キャンセル：処理を終了"
            ),
            parent=root,
        )
    finally:
        root.destroy()

    if filename_filter is None:
        print("処理がキャンセルされました。")
        return 1

    configure_logging(target_folder / "extracter.log")
    output_name = f"{target_folder.name or 'metadata'}_daily_metadata.csv"
    daily_csv_output = target_folder / output_name
    LOGGER.info("選択フォルダ: %s", target_folder)
    compile_daily_metadata(
        target_folder,
        daily_csv_output,
        validate_filename=filename_filter,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
