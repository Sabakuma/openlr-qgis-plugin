import myMapReader
from openlr import binary_decode
from openlr_dereferencer import decode
from typing import cast

def test_openlr_decoder(user: str, password: str, dbname: str, encoded_location: str):
    try:
        # ユーザー名、パスワード、およびデータベース名を使用してMyMapReaderを初期化
        rdr = myMapReader.MyMapReader(user=user, password=password, dbname=dbname)
        
        # エンコードされたOpenLRロケーションをデコード
        ref = binary_decode(encoded_location)
        res = decode(reference=ref, reader=rdr)
        
        # デコード結果を出力
        for r in res.lines:
            tmp = cast(myMapReader.MyLine, r)
            print(f"ID: {tmp.id}, FRC: {tmp.frc}, FOW: {tmp.fow}, Length: {tmp.length}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    # ユーザー入力を受け付ける
    test_user = input("Enter DB user: ")
    test_password = input("Enter DB password: ")
    test_dbname = input("Enter DB name: ")
    encoded_location = input("Enter encoded OpenLR location: ")
    
    # テスト関数を実行
    test_openlr_decoder(user=test_user, password=test_password, dbname=test_dbname, encoded_location=encoded_location)
