import tempfile
import unittest
from pathlib import Path

import pandas as pd

from filter_shops import filter_shops


class FilterShopsTests(unittest.TestCase):
    def test_filters_deduplicates_and_skips_invalid_rows(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            directory = Path(temp_dir)
            input_path = directory / "source.csv"
            output_path = directory / "result.xlsx"
            pd.DataFrame(
                [
                    {"店铺名称": "目标店", "体验分": 4.35, "主营类目": "女装"},
                    {"店铺名称": "目标店", "体验分": 4.40, "主营类目": "服饰"},
                    {"店铺名称": "区间外", "体验分": 4.60},
                    {"店铺名称": "无效评分", "体验分": "未知"},
                ]
            ).to_csv(input_path, index=False, encoding="utf-8-sig")

            count = filter_shops(input_path, output_path)
            result = pd.read_excel(output_path)

            self.assertEqual(count, 1)
            self.assertEqual(result["店铺名称"].tolist(), ["目标店"])
            self.assertEqual(result["体验分"].tolist(), [4.35])
            self.assertEqual(result.loc[0, "主营类目"], "女装")
            self.assertEqual(result.loc[0, "带货达人/来源"], "授权数据源导入")

    def test_exports_empty_result_without_placeholder_rows(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            directory = Path(temp_dir)
            input_path = directory / "source.csv"
            output_path = directory / "result.xlsx"
            pd.DataFrame([{"店铺名称": "区间外", "体验分": 4.60}]).to_csv(
                input_path, index=False, encoding="utf-8-sig"
            )

            count = filter_shops(input_path, output_path)
            result = pd.read_excel(output_path)

            self.assertEqual(count, 0)
            self.assertTrue(result.empty)
            self.assertEqual(result.columns.tolist(), [
                "店铺名称",
                "体验分",
                "主营类目",
                "带货达人/来源",
                "店铺链接",
                "跟进状态",
            ])


if __name__ == "__main__":
    unittest.main()
