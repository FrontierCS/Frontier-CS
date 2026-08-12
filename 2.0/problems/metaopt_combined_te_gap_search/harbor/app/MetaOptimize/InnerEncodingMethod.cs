namespace MetaOptimize
{
    /// <summary>
    /// The method for encoding inner problem.
    /// TODO: change the name of the file to match the name of class.
    /// </summary>
    public enum InnerRewriteMethodChoice
    {
        /// <summary>
        /// use kkt encoding.
        /// </summary>
        KKT,
        /// <summary>
        /// do the primal dual.
        /// </summary>
        PrimalDual,
    }
}