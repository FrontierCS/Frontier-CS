// <copyright file="KktOptimizationGenerator.cs" company="Microsoft">
// Copyright (c) Microsoft. All rights reserved.
// </copyright>

namespace MetaOptimize
{
    using System;
    using System.Diagnostics;
    using Gurobi;
    class GurobiTerminationCallback : GRBCallback
    {
        private GRBModel model;
        private double prevObj;
        private Stopwatch timer;
        private double terminateNoImprovement_ms;

        // TODO: It does not seem like your checking for improvement? am I missiing something?
        // mostly confused because you call the variable terminateNoImprovement_ms but seems like it should just be terminate?
        public GurobiTerminationCallback(GRBModel model, double terminateNoImprovement_ms)
        {
            this.model = model;
            this.prevObj = double.NaN;
            this.timer = null;
            this.terminateNoImprovement_ms = terminateNoImprovement_ms;
        }

        protected override void Callback()
        {
            try
            {
                if (where == GRB.Callback.MIPNODE)
                {
                    var obj = GetDoubleInfo(GRB.Callback.MIPNODE_OBJBST);
                    CallCallback(obj);
                }
            }
            catch (GRBException e)
            {
                Console.WriteLine("Error code: " + e.ErrorCode);
                Console.WriteLine(e.Message);
                Console.WriteLine(e.StackTrace);
            }
            catch (Exception e)
            {
                Console.WriteLine("Error during callback");
                Console.WriteLine(e.StackTrace);
            }
            throw new Exception("Should not enter this function.");
        }

        public void CallCallback(double obj)
        {
            if (this.timer == null || Double.IsNaN(prevObj))
            {
                prevObj = obj;
                this.timer = Stopwatch.StartNew();
            }
            if (Math.Abs(obj - prevObj) > 0.01)
            {
                prevObj = obj;
                this.timer = Stopwatch.StartNew();
            }
            if (this.timer.ElapsedMilliseconds > terminateNoImprovement_ms)
            {
                this.model.Terminate();
            }
        }

        public void ResetTermination()
        {
            this.prevObj = double.NaN;
            this.timer = null;
        }
    }
}