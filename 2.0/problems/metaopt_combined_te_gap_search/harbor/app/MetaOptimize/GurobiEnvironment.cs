using System;
using System.IO;
using Gurobi;

namespace MetaOptimize
{
    internal class GurobiEnvironment
    {
        private static GRBEnv _env; // 1 instance == 1 license use, max 10 concurrent for all users!
        public static GRBEnv Instance
        {
            get
            {
                if (_env == null)
                {
                    // for 8.1 and later
                    _env = new GRBEnv(true);
                    try
                    {
                        _env.Start();
                    }
                    catch (GRBException e) when (e.Message.Contains("No Gurobi license found") || e.Message.Contains("Failed to connect"))
                    {
                        throw new Exception("Gurobi license error, please fix the IP above", e);
                    }
                }
                return _env;
            }
        }
    }
}
