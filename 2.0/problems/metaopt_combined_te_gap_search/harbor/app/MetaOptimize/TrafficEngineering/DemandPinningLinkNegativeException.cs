namespace MetaOptimize
{
    using System;
    using System.Collections.Generic;
    using System.Linq;
    /// <summary>
    /// shows that the pinned demands cause some links to be negative.
    /// </summary>
    [Serializable]
    public class DemandPinningLinkNegativeException : Exception
    {
        /// <summary>
        /// edge negative.
        /// </summary>
        public (string, string) Edge { get; }
        /// <summary>
        /// DP threshold.
        /// </summary>
        public double Threshold { get; }
        /// <summary>
        /// shows that the pinned demands cause some links to be negative.
        /// </summary>
        public DemandPinningLinkNegativeException(string message, (string, string) edge, double threshold)
            : base(message)
        {
            this.Edge = edge;
            this.Threshold = threshold;
        }
    }
}