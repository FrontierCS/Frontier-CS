// <copyright file="PathComparer.cs" company="Microsoft">
// Copyright (c) Microsoft. All rights reserved.
// </copyright>

namespace MetaOptimize
{
    using System.Collections.Generic;

    /// <summary>
    /// A custom path comparer.
    /// </summary>
    public class PathComparer : IEqualityComparer<string[]>
    {
        /// <summary>
        /// Equality between paths.
        /// </summary>
        /// <param name="x">The first path.</param>
        /// <param name="y">The second path.</param>
        /// <returns>True or false.</returns>
        public bool Equals(string[] x, string[] y)
        {
            if (x.Length != y.Length)
            {
                return false;
            }

            for (int i = 0; i < x.Length; i++)
            {
                if (x[i] != y[i])
                {
                    return false;
                }
            }

            return true;
        }

        /// <summary>
        /// Hashcode for a path.
        /// </summary>
        /// <param name="obj">The path.</param>
        /// <returns>An int hashcode.</returns>
        public int GetHashCode(string[] obj)
        {
            int hash = 7;
            foreach (string x in obj)
            {
                hash = hash * 31 + x.GetHashCode();
            }

            return hash;
        }
    }
}
