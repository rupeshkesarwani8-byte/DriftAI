import AnalysisDetail from "./AnalysisDetail";
import FunctionMatches from "../components/FunctionMatches";

/** The saved analysis (as before) with the function-level section added underneath. */
export default function AnalysisPage() {
  return (
    <>
      <AnalysisDetail />
      <FunctionMatches />
    </>
  );
}