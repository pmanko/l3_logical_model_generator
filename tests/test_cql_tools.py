# Generated by CodiumAI
import datetime
import os
import re
from who_l3_smart_tools.core.cql_tools.cql_file_generator import CqlFileGenerator
from who_l3_smart_tools.core.cql_tools.cql_resource_generator import CqlResourceGenerator
from who_l3_smart_tools.core.cql_tools.cql_template_generator import CqlTemplateGenerator
import pandas as pd
import unittest
import stringcase

class TestCqlTools(unittest.TestCase):
    def test_generate_cql_indicator_scaffolds(self):
        input_indicators = "tests/data/l2/test_indicators.xlsx"
        input_dd = "tests/data/l2/test_dd.xlsx"
        output_dir = "tests/output/cql/templates/"
           
        # Make sure output directory exists
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        generator = CqlTemplateGenerator(input_indicators, input_dd)

        generator.generate_cql_scaffolds()

        generator.print_to_files(output_dir)

        assert os.path.exists(os.path.join(output_dir, "HIVIND2Logic.cql"))


    def test_generate_concepts_cql(self):
        input_indicators = "tests/data/l2/test_indicators.xlsx"
        input_dd = "tests/data/l2/test_dd.xlsx"
        output_dir = "tests/output/cql/files/"

        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        generator = CqlFileGenerator(input_indicators, input_dd)

        generator.generate_cql_concept_library(output_dir=output_dir)

        assert os.path.exists(os.path.join(output_dir, "HIVConcepts.cql"))


class TestCqlResourceGenerator(unittest.TestCase):
    def setUp(self):
        # since we're comparing text, it's useful to have large diffs
        self.maxDiff=5000

        # Load example CQL from data directory
        cql_file_path = "tests/data/example_cql_HIV27.cql"
        indicator_file_path = "tests/data/indicator_dak_input_MINI.xlsx"

        # Load content and close file
        with open(cql_file_path, "r") as cql_file:
            self.cql_content = cql_file.read()

        indicator_file = pd.read_excel(
            indicator_file_path, sheet_name="Indicator definitions"
        )

        self.indicator_row = indicator_file[indicator_file['DAK ID'] == 'HIV.IND.27'].head(1).squeeze()

        self.generator = CqlResourceGenerator(self.cql_content, {
            self.indicator_row['DAK ID']: self.indicator_row
        })

    def test_parse_cql_with_valid_content(self):
        parsed_cql = self.generator.parsed_cql

        self.assertIsNotNone(parsed_cql)
        self.assertEqual(parsed_cql["library_name"], "HIV.IND.27")
        self.assertIn("stratifiers", parsed_cql.keys())
        self.assertIn("denominator", parsed_cql.keys())
        self.assertIn("numerator", parsed_cql.keys())
        self.assertIn("populations", parsed_cql.keys())
        self.assertGreater(len(parsed_cql["stratifiers"]), 0)
        # self.assertGreater(len(parsed_cql["populations"]), 0)
        self.assertIsNotNone(parsed_cql["denominator"])
        self.assertIsNotNone(parsed_cql["numerator"])

    def test_generate_library_fsh(self):
        library_fsh = self.generator.generate_library_fsh().strip()

        output_file = "tests/output/fsh/HIV27_library.fsh"

        if os.path.exists(output_file):
            os.remove(output_file)
        with open(output_file, "w") as f:
            f.write(library_fsh)

        expected_lib_file = f"tests/data/example_fsh/HIV27_library.fsh"
        with open(expected_lib_file, "r") as expected_lib_fsh_file:
            expected_library_fsh = expected_lib_fsh_file.read().rstrip()

        self.assertIsNotNone(library_fsh)
        self.assertEqual(expected_library_fsh, library_fsh)

    def test_generate_measure_fsh(self):
        p = self.generator.parsed_cql
        measure_fsh = self.generator.generate_measure_fsh()

        assert measure_fsh is not None

        output_file = f"tests/output/fsh/{stringcase.alphanumcase(p["library_name"])}_measure.fsh"

        if os.path.exists(output_file):
            os.remove(output_file)
        with open(output_file, "w") as f:
            f.write(measure_fsh.strip())

        expected_measure_file = "tests/data/example_fsh/HIV27_measure.fsh"
        with open(expected_measure_file, "r") as expected_measure_file:
            expected_measure_fsh = expected_measure_file.read().rstrip()
        # The date is always the date the measure was generated, so we need to update it
        expected_measure_fsh = expected_measure_fsh.replace(
            '* date = "2024-06-14"',
            f'* date = "{datetime.datetime.now(datetime.timezone.utc).date():%Y-%m-%d}"'
        )

        self.assertIsNotNone(measure_fsh)
        self.assertEqual(expected_measure_fsh, measure_fsh)

class TestCqlGeneratorOnAllFiles(unittest.TestCase):

    def test_resource_gen_for_all(self):
        input_directory = "tests/data/cql/"
        indicator_file_path = "tests/data/l2/test_indicators.xlsx"

        indicator_file = pd.read_excel(
            indicator_file_path, sheet_name="Indicator definitions"
        )

        # Create lookup dictionary by indicator DAK ID
        indicator_dict = {}
        for i, row in indicator_file.iterrows():
            indicator_dict[row["DAK ID"]] = row

        # Create output dir if not exists
        output_directory = os.path.join("tests", "output", "fsh")
        if not os.path.exists(output_directory):
            os.makedirs(output_directory)
        for subfolder in ["measures", "libraries"]:
            if not os.path.exists(os.path.join(output_directory, subfolder)):
                os.makedirs(os.path.join(output_directory, subfolder))


        # For each cql file, generate library resources. Only generate measures for
        # cql files with corresponding indicator definitions.
        for cql_file in os.listdir(input_directory):
            cql_file_path = os.path.join(input_directory, cql_file)

            # Skip if not a file
            if not os.path.isfile(cql_file_path):
                continue

            # Load content and close file
            cql_file = open(cql_file_path, "r")
            cql_content = cql_file.read()
            cql_file.close()

            generator = CqlResourceGenerator(cql_content, indicator_dict)

            # Create Library file and save to file
            library_fsh = generator.generate_library_fsh()
            if library_fsh:
                file_name = f"{stringcase.alphanumcase(generator.get_library_name())}"
                if generator.is_indicator():
                    file_name += "Logic"
                file_name += ".fsh"
                output_file = os.path.join(output_directory, "libraries", file_name)
                with open(output_file, "w") as f:
                    f.write(library_fsh)

            # Create Measure file and save to file
            measure_fsh = generator.generate_measure_fsh()
            if measure_fsh:
                output_file = os.path.join(output_directory, "measures", f"{stringcase.alphanumcase(generator.get_library_name())}.fsh")
                with open(output_file, "w") as f:
                    f.write(measure_fsh)

if __name__ == "__main__":
    unittest.main()
