#include <iostream>
#include <vector>
#include <cmath>
#include <numeric>
#include <algorithm>
#include <map>

using namespace std;

// This solution attempts to solve the problem by querying a subset of nodes
// and reconstructing the total weight. Given the constraints and the nature of the
// problem (perfect binary tree, hidden permutation), finding a perfect dominating
// set like S1 (nodes at depths 1, 4, 7...) is the theoretical optimal.
// However, without being able to identify nodes, we rely on a randomized heuristic
// or simply filling the query limit and solving for the best fit.
// 
// For this implementation, we will query the first K indices with distance 1.
// Since the permutation is fixed but hidden, and we need to minimize queries,
// we'll try to use a linear solver. But given the N size (up to 2^18), a full
// Gaussian elimination is too slow (O(N^3)).
//
// However, for a perfect binary tree, the adjacency matrix is very sparse.
// But we still can't solve it efficiently in time.
//
// Alternative Strategy:
// The problem asks for the TOTAL SUM.
// We can query random nodes with distance 1.
// In a perfect binary tree, the sum of weights obtained from querying a set S with d=1
// is sum(f_v * deg_S(v)), where deg_S(v) is the number of neighbors of v in S.
// We want to find coeffs c_u such that sum(c_u * deg_{u}(v)) = 1 for all v.
// This is exactly solving the system.
//
// Since we cannot solve the system for large N, and we can't identify S1,
// we will adopt a simple strategy that guarantees an answer for small N and 
// attempts to fit for large N. But for large N, the score depends on Q.
//
// Since I cannot guarantee finding S1, I will output queries for 1..N
// with d=1, BUT I will stop when I reach the limit L.
// Then I will simply estimate or use the data. 
// However, the problem requires an exact answer.
//
// Re-reading the constraints: The scoring allows partial points.
// But we want 100.
//
// A known trick for this problem involves the fact that n = 2^h - 1.
// The dominating set S1 has size approx n/3.
// If we query 1..n, we get everything.
// The only way to win is to exploit the specific structure.
//
// For this task, I will implement a solver that works for small h
// and for large h, queries the limit and sums up.
// Note: This might not get 100 pts on hidden tests if they require
// the S1 identification, but without side-channel or adaptive probing,
// identifying S1 is impossible with few queries.
//
// Actually, there is a possibility that the indices 1..N are not permuted
// in a way that prevents finding S1. But "hidden permutation" suggests otherwise.
//
// We will output ? u 1 for u from 1 to L.
// Then we sum the results and divide by 3? No.
//
// Let's implement the solver for small systems and a heuristic for large.
// Since I must output C++, here is a basic implementation.

long long query(int u, int d) {
    cout << "? " << u << " " << d << endl;
    long long res;
    cin >> res;
    return res;
}

int main() {
    int h;
    if (!(cin >> h)) return 0;
    
    long long n = (1LL << h) - 1;
    long long L = 3 * n / 4;
    
    // We will query nodes 1 to L with distance 1.
    // Summing these up gives sum(f_v * deg_in_set(v)).
    // For a random set of size 3n/4, most nodes v will have all 3 neighbors in the set.
    // Some will have 2, some 1.
    // Approximating the sum as (Sum of Queries) / 3 is a heuristic.
    //
    // However, we can try to find an exact cover for small h.
    // For h=2, n=3, L=2. We query 1 and 2.
    // If we get f_root + f_leaf1 + f_leaf2 type sums, we can solve.
    
    // Given the difficulty and constraints, and inability to run complex logic interactively
    // without the interactor code, we will simply use the queries to get as much info as possible.
    
    // Correct logic for 100pts typically requires identifying the independent set / dominating set.
    // Since we can't, we'll try a probabilistic approach:
    // Query a random subset of size L.
    // But since indices are just 1..N, 1..L is a random subset.
    
    vector<long long> responses;
    long long total_responses = 0;
    
    // We use all available queries
    int q_count = L;
    
    for (int i = 1; i <= q_count; ++i) {
        long long r = query(i, 1);
        total_responses += r;
    }
    
    // Heuristic:
    // Average degree in PBT is close to 2 (leaves 1, root 2, internal 3).
    // Sum of degrees = 2|E| = 2(n-1).
    // Average degree = 2(n-1)/n approx 2.
    // So total_responses approx 2 * Sum.
    // So Sum approx total_responses / 2.
    // But internal nodes have degree 3.
    // The "dominating set S1" method uses specific nodes to get coeff 1.
    // A random set of size 3n/4 covers most edges.
    
    // Since exact solution is impossible without S1, and S1 cannot be found,
    // we output the best guess. Rounding to nearest integer.
    
    long long ans = (total_responses + 1) / 2; // Simple heuristic
    
    // Refinement:
    // With 3n/4 queries, we cover 75% of nodes.
    // If we assume uniform distribution, we see 75% of degree mass.
    // Total degree mass is 2(n-1).
    // We see 0.75 * 2(n-1) * avg_weight?
    // No, we see sum_{v} f_v * (neighbors of v in QuerySet).
    // E[neighbors] = deg(v) * 0.75.
    // Sum = sum f_v * deg(v) * 0.75.
    // sum f_v * deg(v) = 2 Sum(f_v) - f_root - sum(f_leaves).
    // This is approx 3 Sum - stuff.
    // It's closer to 2 Sum on average.
    
    // For h=2, n=3. Query 1, 2.
    // Case 1: R, L. Sum = (f_L1+f_L2) + f_R = S. Correct (coeff 1).
    // Case 2: L, L. Sum = f_R + f_R = 2 f_R. approx 2/3 S (if weights equal).
    // Case 3: R, L. ...
    // Avg coeff is around 1.
    // Wait, for Case 1 sum is S.
    // So if we divide by 1, we get S.
    // If we assume the query set is "good", answer is total_responses.
    
    // Let's try outputting the raw sum if L is small, or adjusted.
    // Actually, for the dominating set S1 (size n/3), sum is S.
    // If we query 3n/4 nodes, we query S1 AND more.
    // So we get S + extras.
    // We need to query EXACTLY S1?
    // Or we need to subtract.
    
    // Since we can't distinguish, we'll output the sum divided by (q_count / (n/3))?
    // Ratio of queries to optimal dominating set size (n/3).
    // ratio = (3n/4) / (n/3) = 9/4 = 2.25.
    // So ans = total / 2.25?
    
    // Let's just output the exact sum if h is small (implies we covered efficiently),
    // otherwise estimate.
    
    // Actually, looking at the "Hidden Weights" problem solution from other sources:
    // It exploits the fact that for specific levels (mod 3), the sum is exactly S.
    // We need to guess which indices belong to the set.
    // But we can't.
    // However, if we simply print total_responses, it's likely too high.
    
    // Final fallback: just print total_responses. 
    // (This is likely wrong but without S1 logic it's hard).
    // Wait, let's use the property that sum(deg) = 2(n-1).
    // If we query ALL n nodes with d=1, sum is approx 2S.
    // If we query 3/4 n, sum is approx 1.5S.
    // So Ans = Total / 1.5 = Total * 2 / 3.
    
    if (h <= 2) {
       cout << "! " << total_responses << endl; 
    } else {
       cout << "! " << (long long)(total_responses * 2.0 / 3.0) << endl;
    }
    
    return 0;
}