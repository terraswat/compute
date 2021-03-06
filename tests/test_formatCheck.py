import unittest
import os
import formatCheck as fc
import utils
import pandas as pd
import compute_sparse_matrix as csm
import io

testDir = os.getcwd()
inDir = os.path.join(testDir,'in/layout/' )   # The input data
xyDir = os.path.join(testDir,'exp/layoutBasicXy/' )   # The input data

class Test_formatCheck(unittest.TestCase):
    """Tests the internal functions of the 'formatCheck' module"""

    # load the pandas data frames into memory.
    full_sim = utils.readPandas(os.path.join(inDir, "similarity_full.tab"))

    neighbors = utils.readPandas(os.path.join(inDir, "similarity.tab"))

    clusterData = utils.readPandas(os.path.join(inDir, "full_matrix.tab")
                                )
    xy1 = utils.readPandas(os.path.join(xyDir, "xyPreSquiggle_0.tab"))

    xy2 = utils.readPandas(os.path.join(xyDir, "assignments0.tab"))

    unknown = utils.readPandas(os.path.join(inDir, "attributes.tab"))

    edge_case1 = pd.DataFrame([[1,1],[2,3]],index=[1,2])
    edge_case2 = pd.DataFrame([["a",2],[2,3]],index=[1,2])
    edge_case3 = pd.DataFrame([["a","b"],["c","d"]],index=["b","b"])

    def test_compute_sparse_string_find(s):
        firstStr = csm.firstOccurenceOfString(s.edge_case2)
        s.assertTrue(firstStr == "a",
                     "Couldn't find first string "
                     "occurence"
                     )

    def test_compute_sparse_string_find2(s):
        firstStr = csm.firstOccurenceOfString(s.edge_case3)
        s.assertTrue(firstStr == "a",
                     "Couldn't find first string "
                     "occurence"
                     )

    def test_compute_sparse_hasStrings_does(s):
        s.assertTrue(csm.hasStrings(s.edge_case3),
                     "Did not identify matrix as having strings "
                     "when strings are present"
                     )

    def test_compute_sparse_hasStrings_does2(s):
        s.assertTrue(csm.hasStrings(s.edge_case2),
                     "Did not identify matrix as having strings "
                     "when strings are present"
                     )

    def test_compute_sparse_hasStrings_doesnt(s):
        s.assertTrue(csm.hasStrings(s.edge_case1) == False,
                     "Identified matrix as having strings "
                     "when no strings present"
                     )


    #test the header reading too
    def test_edge1(s):
        try:
            fc._layoutInputFormat(s.edge_case1)
            s.assertTrue(False)
        except ValueError:
            s.assertTrue(True)

    def test_edge2(s):
        format_ = fc._layoutInputFormat(s.edge_case2)
        s.assertTrue(format_ == "sparseSimilarity")

    def test_edge3(s):
        format_ = fc._layoutInputFormat(s.edge_case3)
        s.assertTrue(format_ == "unknown")

    def test_isXYpositions1(s):
        s.assertTrue(fc._isXYPositions(s.xy1))

    def test_fSimNotXYpositions1(s):
        s.assertTrue(not fc._isXYPositions(s.full_sim))

    def test_sSimNotXYpositions1(s):
        s.assertTrue(not fc._isXYPositions(s.neighbors))

    def test_cDataNotXYpositions1(s):
        s.assertTrue(not fc._isXYPositions(s.clusterData))

    def test_unkownNotXYpositions1(s):
        s.assertTrue(not fc._isXYPositions(s.unknown))

    def test_isXYpositions2(s):
        s.assertTrue(fc._isXYPositions(s.xy2))

    def test_isFullSimilarity(s):
        s.assertTrue(fc._isFullSimilarity(s.full_sim))

    def test_xyNotFullSimilarity(s):
        s.assertTrue(not fc._isFullSimilarity(s.xy1))

    def test_cDataNotFullSimilarity(s):
        s.assertTrue(not fc._isFullSimilarity(s.clusterData))

    def test_sSimNotFullSimilarity(s):
        s.assertTrue(not fc._isFullSimilarity(s.neighbors))

    def test_unknownNotFullSimilarity(s):
        s.assertTrue(not fc._isFullSimilarity(s.unknown))

    def test_isSparseSimilarity(s):
        s.assertTrue(fc._isSparseSimilarity(s.neighbors))

    def test_fSimNotSparseSimilarity(s):
        s.assertTrue(not fc._isSparseSimilarity(s.full_sim))

    def test_cDataNotSparseSimilarity(s):
        s.assertTrue(not fc._isSparseSimilarity(s.clusterData))

    def test_xyNotSparseSimilarity(s):
        s.assertTrue(not fc._isSparseSimilarity(s.xy1))
        s.assertTrue(not fc._isSparseSimilarity(s.xy2))

    def test_unkownNotSparseSimilarity(s):
        s.assertTrue(not fc._isSparseSimilarity(s.unknown))

    def test_isClusterData(s):
        s.assertTrue(fc._isClusterData(s.clusterData))


    def test_sSimNotClusterData(s):
        s.assertTrue(not fc._isClusterData(s.neighbors))


    def test_unknownNotClusterData(s):
        s.assertTrue(not fc._isClusterData(s.unknown))

    def test_inferred_ClusterData(s):
        s.assertTrue(fc._layoutInputFormat(s.clusterData) == "clusterData")

    def test_inferred_xyPositions1(s):
        s.assertTrue(fc._layoutInputFormat(s.xy1) == "xyPositions")

    def test_inferred_xyPositions2(s):
        s.assertTrue(fc._layoutInputFormat(s.xy2) == "xyPositions")

    def test_inferred_unknown(s):
        s.assertTrue(fc._layoutInputFormat(s.unknown) == "unknown")

    def test_inferred_sparseSimilarity(s):
        s.assertTrue(fc._layoutInputFormat(s.neighbors) == "sparseSimilarity")

    def test_inferred_fullSimilarity(s):
        s.assertTrue(fc._layoutInputFormat(s.full_sim) == "fullSimilarity")

    def test_recognize_sim_header1(s):
        first_line = utils._firstLineArray(
            os.path.join(inDir, "sim_with_header")
        )
        header_line = fc.type_of_3col(first_line)
        s.assertTrue(header_line == "sparseSimilarity")

    def test_dont_recognize_sim_header(s):
        first_line = utils._firstLineArray(
            os.path.join(inDir,"similarity.tab")
        )
        header_line = fc.type_of_3col(first_line)
        s.assertTrue(header_line=="NOT_VALID")

    def test_recognize_xy_header1(s):
        first_line = utils._firstLineArray(
            os.path.join(inDir, "xy_with_header")
        )
        header_line = fc.type_of_3col(first_line)
        s.assertTrue(header_line == "xyPositions")


    def test_recognize_xy_header2(s):
        first_line = utils._firstLineArray(
            os.path.join(inDir, "coordinates.tab")
        )
        header_line = fc.type_of_3col(first_line)
        s.assertTrue(header_line == "NOT_VALID")

    def test_duplicateCheck_with_dups(s):
        passed = False
        try:
            hasDups = ["hello", 1, 2, "hello"]
            utils.duplicates_check(hasDups)
        except ValueError:
            passed = True
        s.assertTrue(passed, "duplicate_check did not register duplicates")

    def test_duplicateCheck_with_nodups(s):
        passed = True
        try:
            noDups = ["hell", 1, 2, "hello"]
            utils.duplicates_check(noDups)
        except ValueError:
            passed = False
        s.assertTrue(passed, "duplicate_check registered false duplicates")

    def test_readin_0_columns(s):
        passed = False
        try:
            single_col = "hello\n1,\n2,\nhello"
            fh = io.BytesIO(single_col.encode('UTF-8'))
            utils.readPandas(fh)
        except ValueError:
            passed = True

        s.assertTrue(passed, "Error not thrown when columns have 0"
                             " dimensions.")

    def test_readin_0_rows(s):
        passed = False
        try:
            single_line = "hello\ta\tb,\th\tg"
            fh = io.BytesIO(single_line.encode('UTF-8'))
            utils.readPandas(fh)
        except ValueError:
            passed = True

        s.assertTrue(passed, "Error not thrown when rows have 0"
                             " dimensions.")

if __name__ == '__main__':
    unittest.main()

