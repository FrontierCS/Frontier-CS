// <copyright file="KktOptimizationGenerator.cs" company="Microsoft">
// Copyright (c) Microsoft. All rights reserved.
// </copyright>

namespace MetaOptimize
{
    using System;
    using System.Diagnostics;
    using Gurobi;
    class GurobiTimeoutCallback : GRBCallback
    {
        private GRBModel model;
        private Stopwatch timer;
        private double timeout;
        private double presolvetime_ms = -1;

        public GurobiTimeoutCallback(GRBModel model, double timeout) {
            this.model = model;
            this.timer = null;
            this.timeout = timeout;
            if (this.timeout <= 0) {
                this.timeout = Double.PositiveInfinity;
            }
        }

        protected override void Callback()
        {
            try {
                if (where == GRB.Callback.PRESOLVE) {
                    presolvetime_ms = GetDoubleInfo(GRB.Callback.RUNTIME) * 1000;
                } else {
                    CallCallback(where, presolvetime_ms);
                }
            } catch (GRBException e) {
                Console.WriteLine("Error code: " + e.ErrorCode);
                Console.WriteLine(e.Message);
                Console.WriteLine(e.StackTrace);
            } catch (Exception e) {
                Console.WriteLine("Error during callback");
                Console.WriteLine(e.StackTrace);
            }
            throw new Exception("Should not enter this function.");
        }
        public void CallCallback(int where, double presolvetime_ms,
            bool storeLastIfTerminated = false, GurobiStoreProgressCallback storeProgressCallback = null)
        {
            if (where == GRB.Callback.PRESOLVE) {
                this.timer = null;
                return;
            }
            if (where != GRB.Callback.MIP && this.timer == null) {
                return;
            }
            if (this.timer == null) {
                Console.WriteLine("Starting the timeout timer");
                this.timer = Stopwatch.StartNew();
            }
            double currTime_ms = timer.ElapsedMilliseconds;
            if (currTime_ms > timeout) {
                // Utils.AppendToFile(@"../logs/logs.txt", "terminating after = " + currTime_ms);
                Console.WriteLine("Terminating After = " + currTime_ms + ", presolve time = " + presolvetime_ms);
                if (storeLastIfTerminated) {
                    storeProgressCallback.WriteLastLineBeforeTermination(currTime_ms);
                }
                this.model.Terminate();
            }
        }
        public void ResetTermination()
        {
            this.presolvetime_ms = 0;
            this.timer = null;
        }
    }
}