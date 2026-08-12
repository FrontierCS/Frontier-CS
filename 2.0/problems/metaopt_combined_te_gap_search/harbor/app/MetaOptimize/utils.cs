namespace MetaOptimize
{
    using System;
    using System.Collections.Generic;
    using System.Diagnostics;
    using System.IO;
    using System.Linq;
    using Newtonsoft.Json;
    /// <summary>
    /// Implements a utility function with some .
    /// </summary>
    /// TODO: this file needs to be broken up into multiple different classes.
    /// You need a logger class and also a class that provides demand utils...
    /// Your lumping everything together here.
    public static class Utils
    {
        /// <summary>
        /// appends the given line to the end of file.
        /// </summary>
        public static void AppendToFile(string dirname, string filename, string line)
        {
            AppendToFile(Path.Combine(dirname, filename), line);
        }

        /// <summary>
        /// appends the given line to the end of file.
        /// </summary>
        public static void AppendToFile(string path, string line)
        {
            if (!File.Exists(path))
            {
                throw new System.Exception("file " + path + " does not exist!");
            }
            using (StreamWriter file = new (path, append: true))
            {
                file.WriteLine(line);
            }
        }

        /// <summary>
        /// creates the file in the given directory.
        /// </summary>
        public static string CreateFile(string dirname, string filename, bool removeIfExist)
        {
            string path = Path.Combine(dirname, filename);
            Directory.CreateDirectory(dirname);
            if (removeIfExist)
            {
                RemoveFile(dirname, filename);
            }
            using (File.Create(path))
            {
            }
            return path;
        }

        /// <summary>
        /// creates the file in the given directory.
        /// </summary>
        public static string CreateFile(string path, bool removeIfExist)
        {
            var filename = Path.GetFileName(path);
            var dirname = Path.GetDirectoryName(path);
            Directory.CreateDirectory(dirname);
            if (removeIfExist)
            {
                RemoveFile(dirname, filename);
            }
            using (File.Create(path))
            {
            }
            return path;
        }

        /// <summary>
        /// creates the file in the given directory.
        /// </summary>
        public static string CreateFile(string path, bool removeIfExist, bool addFid)
        {
            var filename = Path.GetFileName(path);
            var extension = Path.GetExtension(filename);
            var filenameWoE = Path.GetFileNameWithoutExtension(filename);
            filename = filenameWoE + "_" + GetFID() + extension;
            var dirname = Path.GetDirectoryName(path);
            Directory.CreateDirectory(dirname);
            if (removeIfExist)
            {
                RemoveFile(dirname, filename);
            }
            path = Path.Combine(dirname, filename);
            using (File.Create(path))
            {
            }
            return path;
        }

        /// <summary>
        /// remove the file if exists.
        /// </summary>
        public static void RemoveFile(string dirname, string filename)
        {
            string path = Path.Combine(dirname, filename);
            RemoveFile(path);
        }

        /// <summary>
        /// remove the file if exists.
        /// </summary>
        public static void RemoveFile(string path)
        {
            if (File.Exists(path))
            {
                File.Delete(path);
            }
        }

        /// <summary>
        /// return some fid based on the date of today.
        /// </summary>
        public static string GetFID()
        {
            string fid = DateTime.Now.Year + "_" + DateTime.Now.Month + "_" + DateTime.Now.Day + "_" + DateTime.Now.Hour + "_" + DateTime.Now.Minute + "_" +
                DateTime.Now.Second + "_" + DateTime.Now.Millisecond;
            return fid;
        }

        /// <summary>
        /// write line to consule if verbose = true.
        /// </summary>
        public static void WriteToConsole(string line, bool verbose)
        {
            if (verbose)
            {
                Console.WriteLine(line);
            }
        }
        /// <summary>
        /// write line to consule if verbose = true.
        /// </summary>
        public static void WriteToConsole(string line, int verbose)
        {
            if (verbose > 0)
            {
                Console.WriteLine(line);
            }
        }

        /// <summary>
        /// log state.
        /// </summary>
        public enum LogState
        {
            /// <summary>
            /// info.
            /// </summary>
            INFO,
            /// <summary>
            /// warning.
            /// </summary>
            WARNING,
            /// <summary>
            /// error.
            /// </summary>
            ERROR,
        }
        /// <summary>
        /// logger for storing output.
        /// </summary>
        /// TODO: make sure the prints you create use this.
        public static void logger(string line, bool verbose, LogState state = LogState.INFO)
        {
            string output = "";
            switch (state)
            {
                case LogState.INFO:
                    output += "[INFO]";
                    break;
                case LogState.WARNING:
                    output += "[WARNING]";
                    break;
                case LogState.ERROR:
                    output += "[ERROR]";
                    break;
                default:
                    throw new Exception("state value is not valid");
            }
            output += " " + line;
            WriteToConsole(output, verbose);
        }
        /// <summary>
        /// logger for storing output.
        /// </summary>
        public static void logger(string line, int verbose, LogState state = LogState.INFO)
        {
            if (verbose > 0)
            {
                logger(line, true, state);
            }
        }

        /// <summary>
        /// store progress if store progress is true.
        /// </summary>
        public static void StoreProgress(string path, string line, bool storeProgress)
        {
            if (storeProgress)
            {
                Utils.AppendToFile(path, line);
            }
        }

        /// <summary>
        /// write set of paths to the file.
        /// </summary>
        public static void readPathsFromFile(string pathToFile, Dictionary<int, Dictionary<(string, string), string[][]>> output)
        {
            if (!File.Exists(pathToFile))
            {
                return;
            }
            var readPaths = JsonConvert.DeserializeObject<Dictionary<int, Dictionary<string, string[][]>>>(File.ReadAllText(pathToFile));
            foreach (var (k, paths) in readPaths)
            {
                output[k] = new Dictionary<(string, string), string[][]>();
                foreach (var (pair, path) in paths)
                {
                    var spair = pair.Split("_");
                    output[k][(spair[0], spair[1])] = path;
                }
            }
        }

        /// <summary>
        /// write paths to file.
        /// </summary>
        public static void writePathsToFile(string pathToWrite, Dictionary<int, Dictionary<(string, string), string[][]>> output)
        {
            if (File.Exists(pathToWrite))
            {
                throw new Exception("path to file to store the paths exist!!");
            }
            var dirname = Path.GetDirectoryName(pathToWrite);
            if (!Directory.Exists(dirname))
            {
                Directory.CreateDirectory(dirname);
            }
            var storeOutput = new Dictionary<int, Dictionary<string, string[][]>>();
            foreach (var (key, paths) in output)
            {
                storeOutput[key] = new Dictionary<string, string[][]>();
                foreach (var (pair, path) in output[key])
                {
                    storeOutput[key][pair.Item1 + "_" + pair.Item2] = path;
                }
            }
            string serializedjson = JsonConvert.SerializeObject(storeOutput);
            File.WriteAllText(pathToWrite, serializedjson);
        }

        /// <summary>
        /// write demands to file.
        /// </summary>
        public static void writeDemandsToFile(string pathToWrite, IDictionary<(string, string), double> demand)
        {
            if (File.Exists(pathToWrite))
            {
                throw new Exception("path to file to store the paths exist!!");
            }
            var dirname = Path.GetDirectoryName(pathToWrite);
            if (!Directory.Exists(dirname))
            {
                Directory.CreateDirectory(dirname);
            }
            string serializedjson = JsonConvert.SerializeObject(demand);
            File.WriteAllText(pathToWrite, serializedjson);
        }

        /// <summary>
        /// read last line of file.
        /// </summary>
        public static string readLastLineFile(string dirname, string filename)
        {
            string path = Path.Combine(dirname, filename);
            if (!File.Exists(path))
            {
                throw new Exception("File does not exist!");
            }
            return File.ReadLines(path).Last();
        }

        /// <summary>
        /// assign zero demand the empty pairs.
        /// </summary>
        public static void setEmptyPairsToZero(Topology topology, Dictionary<(string, string), double> demands)
        {
            foreach (var pair in topology.GetNodePairs())
            {
                if (!demands.ContainsKey(pair))
                {
                    demands[pair] = 0;
                }
                else if (demands[pair] <= 0)
                {
                    demands[pair] = 0;
                }
            }
        }

        /// <summary>
        /// assign zero demand the empty pairs.
        /// </summary>
        public static void setEmptyHistoryToZero(Topology topology, int historyLen, Dictionary<(int, string, string), double> historicDemands)
        {
            for (int h = 0; h < historyLen; h++)
            {
                foreach (var pair in topology.GetNodePairs())
                {
                    if (!historicDemands.ContainsKey((h, pair.Item1, pair.Item2)))
                    {
                        historicDemands[(h, pair.Item1, pair.Item2)] = 0;
                    }
                    else if (historicDemands[(h, pair.Item1, pair.Item2)] <= 0)
                    {
                        historicDemands[(h, pair.Item1, pair.Item2)] = 0;
                    }
                }
            }
        }

        /// <summary>
        /// Takes in the expected solution of the heuristic and the optimal problem and checks if the encoders return the same results.
        /// </summary>
        /// TODO: seems like this is right now very specific to the TE problem. We should make it more general.
        /// TODO: there is a lot of refactoring we need to do here.
        public static void checkSolution<TVar, TSolution>(Topology topology, IEncoder<TVar, TSolution> heuristicEncoder,
            IEncoder<TVar, TSolution> optimalEncoder, double hResult, double oResult,
            Dictionary<(string, string), double> demands, string solverN = "", PathType pathType = PathType.KSP,
            Dictionary<(string, string), string[][]> selectedPaths = null,
            Dictionary<(int, string, string), double> historicDemands = null,
            double sensitivity = 0.001)
        {
            heuristicEncoder.Solver.CleanAll();
            var encodingHeuristic = heuristicEncoder.Encoding(topology, inputEqualityConstraints: demands,
                noAdditionalConstraints: true, pathType: pathType, selectedPaths: selectedPaths, historicInputConstraints: historicDemands);
            var solverSolutionHeuristic = heuristicEncoder.Solver.Maximize(encodingHeuristic.MaximizationObjective);
            var optimizationSolutionHeuristic = (TEOptimizationSolution)heuristicEncoder.GetSolution(solverSolutionHeuristic);

            optimalEncoder.Solver.CleanAll();
            var encodingOptimal = optimalEncoder.Encoding(topology, inputEqualityConstraints: demands,
                noAdditionalConstraints: true, pathType: pathType, selectedPaths: selectedPaths, historicInputConstraints: historicDemands);
            var solverSolutionOptimal = optimalEncoder.Solver.Maximize(encodingOptimal.MaximizationObjective);
            var optimizationSolutionOptimal = (TEOptimizationSolution)optimalEncoder.GetSolution(solverSolutionOptimal);
            Console.WriteLine($"optimal-{solverN} = {optimizationSolutionOptimal.MaxObjective}, heuristic-{solverN}={optimizationSolutionHeuristic.MaxObjective}");
            Debug.Assert(IsApproximately(hResult, optimizationSolutionHeuristic.MaxObjective, sensitivity));
            Debug.Assert(IsApproximately(oResult, optimizationSolutionOptimal.MaxObjective, sensitivity));
        }

        /// <summary>
        /// Determines if two values are approximately equal.
        /// </summary>
        /// <param name="expected">The expected value.</param>
        /// <param name="actual">The actual value.</param>
        /// <param name="threshold">A configurable threshold parameter.</param>
        /// <returns>True if their difference is below the threshold.</returns>
        public static bool IsApproximately(double expected, double actual, double threshold = 0.001)
        {
            if (actual == 0)
            {
                return expected < threshold;
            }
            // Console.WriteLine(expected + " " + actual + " " + Math.Abs(expected - actual) / actual);
            return Math.Abs(expected - actual) / Math.Abs(actual) < threshold;
        }
        /// <summary>
        /// Determines if a number is approximately equal to a number in a set.
        /// </summary>
        /// <param name="setNumbers">a set of numbers.</param>
        /// <param name="target">target number to search for.</param>
        /// <param name="threshold">A configurable threshold parameter.</param>
        /// <returns>True if the difference is below the threshold.</returns>
        public static bool IsApproximatelyInSet(ISet<float> setNumbers, float target, double threshold = 0.001)
        {
            var listNumbers = setNumbers.ToArray();
            foreach (var number in listNumbers)
            {
                if (IsApproximately(target, number, threshold))
                {
                    return true;
                }
            }
            return false;
        }
    }
}