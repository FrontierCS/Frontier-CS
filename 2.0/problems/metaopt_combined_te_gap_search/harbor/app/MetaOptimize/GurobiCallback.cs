// <copyright file="KktOptimizationGenerator.cs" company="Microsoft">
// Copyright (c) Microsoft. All rights reserved.
// </copyright>

namespace MetaOptimize
{
    using System;
    using Gurobi;
    class GurobiCallback : GRBCallback
    {
        // TODO: need a comment that describes each of these parameters.
        private bool storeProgressEnabled = false;
        private GurobiStoreProgressCallback storeProgressCallback = null;
        private bool terminationCallbackEnabled = false;
        private GurobiTerminationCallback terminationCallback = null;
        private bool timeoutCallbackEnabled = false;
        private GurobiTimeoutCallback timeoutCallback = null;
        double presolvetime_ms = -1;

        // TODO: needs a comment that describes what this function does and what each input means.
        public GurobiCallback(
            GRBModel model,
            bool storeProgress = false,
            String dirname = null,
            String filename = null,
            double terminateNoImprovement_ms = -1,
            double timeout = 0)
        {
            if (storeProgress)
            {
                this.storeProgressEnabled = true;
                this.storeProgressCallback = new GurobiStoreProgressCallback(model, dirname, filename);
            }
            if (terminateNoImprovement_ms > 0)
            {
                this.terminationCallbackEnabled = true;
                this.terminationCallback = new GurobiTerminationCallback(model, terminateNoImprovement_ms);
            }
            if (timeout > 0)
            {
                this.timeoutCallbackEnabled = true;
                this.timeoutCallback = new GurobiTimeoutCallback(model, timeout);
            }
        }

        // TODO: needs many many more comments to help a user understand what is happening.
        protected override void Callback()
        {
            try
            {
                // Utils.AppendToFile(@"../logs/logs.txt", " where " + where);
                if (where == GRB.Callback.PRESOLVE)
                {
                    this.presolvetime_ms = GetDoubleInfo(GRB.Callback.RUNTIME) * 1000;
                    // Utils.AppendToFile(@"../logs/logs.txt", "measured presolve timer = " + presolvetime_ms);
                }
                else if (where == GRB.Callback.MESSAGE)
                {
                    // nothing to do.
                }
                else
                {
                    if (where == GRB.Callback.MIP || where == GRB.Callback.MIPSOL)
                    {
                        // TODO: not clear what the return value is here.
                        // TODO: cleanup and remove commented code.
                        double obj = -1;
                        if (where == GRB.Callback.MIP)
                        {
                            obj = GetDoubleInfo(GRB.Callback.MIP_OBJBST);
                        }
                        else
                        {
                            obj = GetDoubleInfo(GRB.Callback.MIPSOL_OBJ);
                        }
                        var currtime_ms = GetDoubleInfo(GRB.Callback.RUNTIME) * 1000;
                        // Utils.AppendToFile(@"../logs/logs.txt", "measured time = " + currtime_ms + " obj = " + obj);
                        if (this.storeProgressEnabled)
                        {
                            this.storeProgressCallback.CallCallback(obj, currtime_ms, presolvetime_ms);
                        }
                        if (this.terminationCallbackEnabled)
                        {
                            this.terminationCallback.CallCallback(obj);
                        }
                    }
                    if (this.timeoutCallbackEnabled)
                    {
                        this.timeoutCallback.CallCallback(where, presolvetime_ms,
                            storeLastIfTerminated: storeProgressEnabled, storeProgressCallback: storeProgressCallback);
                    }
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
        }

        private void ResetTermination()
        {
            if (this.terminationCallbackEnabled)
            {
                this.terminationCallback.ResetTermination();
            }
        }

        private void ResetProgressTimer()
        {
            if (this.storeProgressEnabled)
            {
                this.storeProgressCallback.ResetProgressTimer();
            }
        }

        private void ResetTimeout()
        {
            if (this.timeoutCallbackEnabled)
            {
                this.timeoutCallback.ResetTermination();
            }
        }

        public void ResetAll()
        {
            this.presolvetime_ms = 0;
            this.ResetProgressTimer();
            this.ResetTermination();
            this.ResetTimeout();
        }

        public void AppendToStoreProgressFile(double time_ms, double gap)
        {
            if (storeProgressEnabled)
            {
                this.storeProgressCallback.AppendToStoreProgressFile(time_ms, gap);
            }
        }
    }
}