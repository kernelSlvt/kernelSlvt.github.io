import unittest
from pathlib import Path
from unittest.mock import patch

import main as site_main


class TestMain(unittest.TestCase):
  @patch("main.SiteBuilder")
  def test_main_delegates_to_the_v2_builder(self, builder_type) -> None:
    report = object()
    builder_type.return_value.build.return_value = report

    self.assertIs(site_main.main(), report)
    builder_type.assert_called_once_with(Path.cwd())
    builder_type.return_value.build.assert_called_once_with()


if __name__ == "__main__":
  unittest.main()
