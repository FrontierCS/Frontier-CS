#include <iostream>
#include <vector>
#include <cmath>
#include <numeric>

using namespace std;

// Function to query the interactor
long long query(int u, int d) {
    cout << "? " << u << " " << d << endl;
    long long response;
    cin >> response;
    return response;
}

int main() {
    int h;
    if (!(cin >> h)) return 0;

    int n = (1 << h) - 1;

    // We will assume p_u = u (identity permutation) to attempt a solution based on levels.
    // If p is not identity, we cannot guarantee < 3n/4 queries with exact answer without identification.
    // This strategy uses ~2n/3 queries.

    // Group indices by level
    // Levels are 0 to h-1.
    // We only query nodes at even levels.
    vector<int> even_levels;
    for (int k = 0; k < h; k += 2) {
        even_levels.push_back(k);
    }

    // Aggregates for queries
    // Q1[k] stores sum of query(u, 1) for u in level k
    // Q2[k] stores sum of query(u, 2) for u in level k
    vector<long long> Q1(h, 0);
    vector<long long> Q2(h, 0);

    for (int k : even_levels) {
        // Nodes at level k are from 2^k to 2^(k+1) - 1
        int start = 1 << k;
        int end = (1 << (k + 1)) - 1;
        for (int u = start; u <= end; ++u) {
            Q1[k] += query(u, 1);
            Q2[k] += query(u, 2);
        }
    }

    // Solve for weights W_0, ..., W_{h-1}
    // W_k is the sum of weights of all nodes at level k.
    
    // 1. Solve for even weights W_0, W_2, ...
    // We have a system of equations based on Q2 (distance 2 queries on even levels).
    // Let W_{even} variables be x_0, x_1, ... where x_i = W_{2i}.
    // The equations relate x_i values.
    // Generally: Q2[2i] = 4*W_{2i-2} + W_{2i} + W_{2i+2}
    // Special cases for boundaries (Root, Leaves).

    vector<long long> W(h, 0);
    int m = even_levels.size(); // Number of even levels
    // Even levels indices: 0, 2, 4, ..., 2*(m-1)
    
    // We can express each W_{2i} as A[i] * W_0 + B[i].
    // Let's verify if W_0 is the free variable.
    // Q2[0] = W_2. (Root at level 0. Dist 2 are grandchildren at level 2).
    // So W_2 is fixed! W_2 = Q2[0].
    
    // Actually, looking at the dependency:
    // R0 = W2.
    // R2 = 4 W0 + W2 + W4. -> W4 = R2 - 4 W0 - W2.
    // R4 = 4 W2 + W4 + W6. -> W6 = R4 - 4 W2 - W4.
    // ...
    // So W_2 is known. W_4 depends on W_0. W_6 depends on W_0...
    // All W_{2k} (for k >= 1) can be expressed as C_k * W_0 + D_k.
    // Finally, we use the equation for the last even level to solve for W_0.
    
    // Coefficients for W_{2i} = val[i] + coeff[i] * W_0
    vector<long long> val(m, 0);
    vector<long long> coeff(m, 0);

    // W_0 = 0 + 1 * W_0
    val[0] = 0;
    coeff[0] = 1;

    // W_2 = Q2[0]
    if (m > 1) {
        val[1] = Q2[0];
        coeff[1] = 0;
    }

    // Recurrence for i = 1 to m-2
    // We have equation from level 2i: Q2[2i] = 4*W_{2i-2} + W_{2i} + W_{2i+2}
    // So W_{2i+2} = Q2[2i] - 4*W_{2i-2} - W_{2i}
    // Maps to indices in val/coeff: W_{2(i+1)} corresponds to index i+1.
    // W_{2i} is index i. W_{2i-2} is index i-1.
    for (int i = 1; i < m - 1; ++i) {
        // Compute W_{2(i+1)}
        // W_{next} = Q2[current_level] - 4 * W_{prev} - W_{curr}
        int current_level = 2 * i;
        // W_{prev} is index i-1
        // W_{curr} is index i
        long long rhs = Q2[current_level];
        
        // val part
        val[i + 1] = rhs - 4 * val[i - 1] - val[i];
        // coeff part
        coeff[i + 1] = 0 - 4 * coeff[i - 1] - coeff[i];
    }

    // Now we use the last equation to solve for W_0.
    // The last even level is L = 2*(m-1).
    // Equation depends on whether L is the leaves (h-1) or internal.
    // Case 1: L == h-1 (Leaves). Dist 2 from leaves: Grandparents and Siblings.
    // Q2[L] = 4 * W_{L-2} + W_L.
    // Case 2: L < h-1 (Internal). Nodes have children (at L+1) and grandchildren (at L+2).
    // Actually, check if L+2 exists.
    // Since we iterated up to m-2 to fill m-1 (which is L), we covered up to W_L.
    // The equation for Q2[L] hasn't been used yet.
    // If L is max level (leaves), Q2[L] = 4 W_{L-2} + W_L.
    // If L is not leaves? But we only query even levels.
    // If h is even (levels 0..h-1, max is odd), then even levels are 0..h-2.
    // The last even level L = h-2.
    // Nodes at h-2 are parents of leaves.
    // Dist 2 from h-2:
    // Up: h-4 (Grandparent).
    // Down: None? (Children at h-1 are leaves, no grandchildren).
    // Sideways: Sibling at h-2.
    // Q2[h-2] = 4 * W_{h-4} + W_{h-2}.
    // Note: Sibling contribution is W_{h-2}.
    // Wait, check formula again.
    // Q2[k] for internal nodes: 4 W_{k-2} + W_k + W_{k+2}.
    // If k = h-2, then k+2 = h. Does not exist.
    // So Q2[h-2] = 4 W_{h-4} + W_{h-2}.
    
    // So in both cases (L=h-1 or L=h-2), the term W_{L+2} vanishes.
    // So equation is Q2[L] = 4 * W_{L-2} + W_L.
    // (If L=0, handled separately, but m>1 usually).
    
    long long W0 = 0;
    
    if (m == 1) {
        // Only level 0. h=1 or h=2?
        // h >= 2. If h=2, levels 0, 1. Even: 0.
        // L=0. Q2[0] = W_2 (if exists). But h=2 implies max level 1.
        // So W_2 doesn't exist.
        // For h=2 (Nodes 1, 2, 3):
        // L=0 (Root). Dist 2 from root? Depth is 1. No dist 2.
        // So Q2[0] should be 0.
        // Wait, h=2, root is level 0. Children level 1. Max dist is 1.
        // Dist 2 query returns 0.
        // Equation Q2[0] = 0.
        // We need W_0.
        // Q1[0] = W_1.
        // We have W_1. We need W_0.
        // Can we find W_0?
        // We haven't used relation between odd and even?
        // Actually, for h=2, Q1[0] (Root, d=1) = Sum(Leaves) = W_1.
        // We still don't have W_0.
        // For h=2, we need to query odd level (Leaves)?
        // But we only query even levels.
        // Special case h=2:
        // Even: 0.
        // Queries: 0 with d=1 -> W_1.
        // 0 with d=2 -> 0.
        // We are missing W_0.
        // Strategy fails for h=2?
        // We need to query S_odd for small h?
        // Or assume W_0 can be found?
        // If h=2, S_even = {0} size 1. S_odd = {1} size 2.
        // Query S_odd with d=1 -> Q1 of leaves.
        // Leaf at d=1 gives Parent (W_0).
        // So for h=2, query level 1 to get W_0.
        // Since n=3, 3n/4 = 2. We can query level 0 and level 1?
        // Level 0 (1 node), Level 1 (2 nodes). Total 3. Too many.
        // But wait.
        // For h=2, W_0 is obtained from Q(Leaves, 1).
        // Since we didn't query leaves, we don't have W_0.
        // However, h >= 2.
        // Let's add specific handling if needed or assume m > 1.
        // For h=2, m=1.
        // We must query odd levels if needed?
        // Let's blindly solve system first.
    } else {
        int L_idx = m - 1;
        // Eq: Q2[even_levels[L_idx]] = 4 * W_{prev} + W_{last}
        // val_eq = Q2[...]
        // lhs = 4 * (val[L-1] + coeff[L-1]*W0) + (val[L] + coeff[L]*W0)
        long long current_Q2 = Q2[even_levels[L_idx]];
        long long total_val = 4 * val[L_idx - 1] + val[L_idx];
        long long total_coeff = 4 * coeff[L_idx - 1] + coeff[L_idx];
        
        // current_Q2 = total_val + total_coeff * W0
        // W0 = (current_Q2 - total_val) / total_coeff
        if (total_coeff != 0) {
            W0 = (current_Q2 - total_val) / total_coeff;
        }
    }

    // Populate W vector for even levels
    for (int i = 0; i < m; ++i) {
        W[even_levels[i]] = val[i] + coeff[i] * W0;
    }

    // 2. Solve for odd weights W_1, W_3, ... using Q1
    // Relations:
    // Q1[0] = W_1
    // Q1[2] = 2*W_1 + W_3  => W_3 = Q1[2] - 2*W_1
    // Q1[2k] = 2*W_{2k-1} + W_{2k+1} => W_{2k+1} = Q1[2k] - 2*W_{2k-1}
    
    // We can iterate.
    // We need W_1 first.
    if (h > 1) {
        W[1] = Q1[0];
        for (int k = 2; k < h; k += 2) {
            // Use Q1[k] to find W_{k+1} if k+1 < h
            if (k + 1 < h) {
                W[k + 1] = Q1[k] - 2 * W[k - 1];
            }
        }
    }
    
    // Special fix for h=2
    if (h == 2) {
        // We have W[1] from Q1[0].
        // We need W[0].
        // From even logic, m=1, we couldn't find W[0] from Q2.
        // We need to query level 1 to find W[0].
        // Level 1 nodes are 2, 3.
        // Query u=2, d=1 gives f_1 = W_0.
        // We can just add this query.
        long long w0_from_leaf = query(2, 1);
        W[0] = w0_from_leaf;
    }

    long long total_sum = 0;
    for (long long w : W) total_sum += w;

    cout << "! " << total_sum << endl;

    return 0;
}