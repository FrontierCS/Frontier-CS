// <copyright file="KktOptimizationGenerator.cs" company="Microsoft">
// Copyright (c) Microsoft. All rights reserved.
// </copyright>

namespace MetaOptimize
{
    using System;
    using Gurobi;
    class GurobiStoreProgressCallback : GRBCallback
    {
        private GRBModel model;
        private String dirname;
        private String filename;
        private double timeBias = 0.0;
        private double presolvetime_ms = -1;
        private double bstObj = Double.NegativeInfinity;
        private double lastTime = -1;

        public GurobiStoreProgressCallback(GRBModel model, String dirname, String filename)
        {
            this.model = model;
            this.dirname = dirname;
            this.filename = filename;
            Utils.CreateFile(dirname, filename, removeIfExist: false);
            Console.WriteLine("will store the progress in dir: " + this.dirname + " on file " + this.filename);
            // this.presolvetimer = null;
            Utils.AppendToFile(this.dirname, this.filename, 0 + ", " + 0);
        }

        protected override void Callback()
        {
            try
            {
                if (where == GRB.Callback.PRESOLVE)
                {
                    this.presolvetime_ms = GetDoubleInfo(GRB.Callback.RUNTIME) * 1000;
                }
                else if (where == GRB.Callback.MIP)
                {
                    var obj = GetDoubleInfo(GRB.Callback.MIP_OBJBST);
                    var currtime_ms = GetDoubleInfo(GRB.Callback.RUNTIME);
                    CallCallback(obj, currtime_ms, this.presolvetime_ms);
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

        public void CallCallback(double objective, double currtime_ms, double presolvetime_ms)
        {
            this.bstObj = Math.Max(this.bstObj, objective);
            double time = timeBias + currtime_ms - presolvetime_ms;
            Utils.AppendToFile(dirname, filename, time + ", " + this.bstObj);
            this.lastTime = time;
        }

        public void WriteLastLineBeforeTermination(double finaltime_ms)
        {
            // Utils.AppendToFile(@"../logs/logs.txt", " last time = " + lastTime + " final time = " + finaltime_ms);
            finaltime_ms += timeBias;
            if (finaltime_ms > lastTime)
            {
                Utils.AppendToFile(dirname, filename, finaltime_ms + ", " + this.bstObj);
                this.lastTime = finaltime_ms;
            }
        }

        public void AppendToStoreProgressFile(double time_ms, double gap)
        {
            if (time_ms > lastTime)
            {
                this.bstObj = Math.Max(this.bstObj, gap);
                Utils.AppendToFile(dirname, filename, time_ms + ", " + this.bstObj);
                this.lastTime = time_ms;
            }
        }

        public void ResetProgressTimer()
        {
            this.presolvetime_ms = 0;
            this.timeBias = Double.Parse(Utils.readLastLineFile(this.dirname, this.filename).Split(", ")[0]);
            Utils.AppendToFile(dirname, filename, "========= Reset Called ========");
            // Utils.AppendToFile(@"../logs/logs.txt", "time bias = " + timeBias);
        }
    }
}