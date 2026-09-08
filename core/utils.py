import csv

def save2dListCsv(data_2d, filepath):
    """
    2DリストをCSVファイルとして保存します。
    
    :param data_2d: 保存する2Dリスト (例: [['A', 'B'], [1, 2]])
    :param filepath: 保存先のファイルパス
    """
    with open(filepath, mode='w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerows(data_2d)

def loadCsv2dList(filepath):
    """
    CSVファイルを読み込んで2Dリストとして返します。
    
    :param filepath: 読み込むファイルパス
    :return: 2Dリスト (各要素は文字列)
    """
    with open(filepath, mode='r', encoding='utf-8') as f:
        reader = csv.reader(f)
        return [row for row in reader]