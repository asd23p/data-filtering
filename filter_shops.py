import argparse
from pathlib import Path
from typing import Sequence

import pandas as pd


SCORE_MIN = 4.20
SCORE_MAX = 4.50
OUTPUT_EXCEL = "抖店体验分精准线索库.xlsx"
REQUIRED_COLUMNS = ("店铺名称", "体验分")
OUTPUT_COLUMNS = (
    "店铺名称",
    "体验分",
    "主营类目",
    "带货达人/来源",
    "店铺链接",
    "跟进状态",
)


def read_source(input_path: Path) -> pd.DataFrame:
    suffix = input_path.suffix.lower()
    if suffix == ".csv":
        return pd.read_csv(input_path, encoding="utf-8-sig")
    if suffix == ".xlsx":
        return pd.read_excel(input_path)
    raise ValueError("输入文件只支持 .csv 或 .xlsx 格式。")


def filter_shops(
    input_path: Path,
    output_path: Path,
    score_min: float = SCORE_MIN,
    score_max: float = SCORE_MAX,
) -> int:
    if score_min > score_max:
        raise ValueError("最低体验分不能高于最高体验分。")

    shops = read_source(input_path)
    missing_columns = [column for column in REQUIRED_COLUMNS if column not in shops.columns]
    if missing_columns:
        raise ValueError(f"输入文件缺少必需列：{', '.join(missing_columns)}")

    shops["店铺名称"] = shops["店铺名称"].astype("string").str.strip()
    shops["体验分"] = pd.to_numeric(shops["体验分"], errors="coerce")

    invalid_rows = shops["店铺名称"].isna() | shops["店铺名称"].eq("") | shops["体验分"].isna()
    invalid_count = int(invalid_rows.sum())
    if invalid_count:
        print(f"已跳过 {invalid_count} 行：店铺名称为空或体验分不是有效数字。")

    shops = shops.loc[~invalid_rows].copy()
    shops = shops.loc[shops["体验分"].between(score_min, score_max, inclusive="both")].copy()

    defaults = {
        "主营类目": "待查",
        "带货达人/来源": "授权数据源导入",
        "店铺链接": "",
        "跟进状态": "待加微",
    }
    for column, default in defaults.items():
        if column not in shops.columns:
            shops[column] = default
        else:
            shops[column] = shops[column].fillna(default)

    shops = shops.loc[:, OUTPUT_COLUMNS].drop_duplicates(subset=["店铺名称"], keep="first")
    shops.to_excel(output_path, index=False)
    return len(shops)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="筛选由授权平台或数据服务导出的店铺 CSV/XLSX 文件。"
    )
    parser.add_argument(
        "--input",
        required=True,
        type=Path,
        help="授权数据源导出的 .csv 或 .xlsx 文件",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(OUTPUT_EXCEL),
        help=f"结果 Excel 文件路径（默认：{OUTPUT_EXCEL}）",
    )
    parser.add_argument("--score-min", type=float, default=SCORE_MIN, help="最低体验分")
    parser.add_argument("--score-max", type=float, default=SCORE_MAX, help="最高体验分")
    args = parser.parse_args(argv)

    if not args.input.is_file():
        parser.error(f"找不到输入文件：{args.input}")

    try:
        count = filter_shops(args.input, args.output, args.score_min, args.score_max)
    except (OSError, ImportError, ValueError) as error:
        parser.error(str(error))

    print(f"已导出 {count} 家符合条件的店铺：{args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
