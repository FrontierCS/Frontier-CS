#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <cstdlib>
#include <ctime>

using namespace std;

// Function to perform a query
long long query(int u, int d) {
    if (d <= 0) return 0; // Should not happen based on logic
    cout << "? " << u << " " << d << endl;
    long long res;
    cin >> res;
    return res;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int h;
    if (!(cin >> h)) return 0;

    int n = (1 << h) - 1;

    // Special case for small h
    if (h == 2) {
        // n = 3
        // Query all 3 nodes with d=1
        long long q1 = query(1, 1);
        long long q2 = query(2, 1);
        long long q3 = query(3, 1);
        
        // Sum of all q_i is 3S - f_root - 2*f_leaves
        // But for h=2, logic is simple.
        // One node is root (degree 2), two are leaves (degree 1).
        // If u is root, q(u,1) = f_leaf1 + f_leaf2.
        // If u is leaf, q(u,1) = f_root.
        // We have two leaves, so we get f_root twice.
        // We get f_leaf1 + f_leaf2 once.
        // Sum q1+q2+q3 = 2*f_root + f_leaf1 + f_leaf2 = S + f_root.
        // We need S.
        // We can identify which one is root?
        // Root has neighbors at dist 1 (leaves). Leaves have max dist 1 (to root) in tree of height 1?
        // Wait, h=2 means root at depth 0, leaves at depth 1.
        // Max dist from root is 1. Max dist from leaf is 2 (to other leaf).
        // Check max dist?
        // Query(u, 2). If > 0, u is leaf.
        // For h=2, max dist is 2.
        long long d2_1 = query(1, 2);
        long long f_root = 0;
        if (d2_1 == 0) { // Node 1 is root
             // q1 = f_leaf1 + f_leaf2
             // q2 = f_root (since 2 is leaf)
             // q3 = f_root
             f_root = q2; // or q3
        } else {
             // Node 1 is leaf
             f_root = q1;
        }
        long long S = q1 + q2 + q3 - f_root;
        cout << "! " << S << endl;
        return 0;
    }

    // General case
    // Strategy:
    // 1. Calculate Q_total = sum_{u=1 to n} query(u, 1).
    //    Q_total = 3*S - f_root - 2*S_leaves.
    // 2. Find root r.
    // 3. Use r to find W_i (sum of weights at level i) for i=1..h-1.
    //    S_leaves = W_{h-1}.
    //    S = f_root + sum(W_i).
    // 4. Solve for f_root using equations.

    long long Q_total = 0;
    for (int u = 1; u <= n; ++u) {
        Q_total += query(u, 1);
    }

    // Find root
    // We try random nodes and check if they can be root.
    // Root has max distance h-1.
    // We check condition query(u, h) == 0.
    // Most nodes have max dist >= h.
    // To be safe against false positives (though unlikely with large h), we can check query(u, h-1) > 0.
    
    int root = -1;
    srand(time(0));
    vector<int> p(n);
    iota(p.begin(), p.end(), 1);
    random_shuffle(p.begin(), p.end());

    // Optimization: Check h first.
    for (int u : p) {
        long long val = query(u, h);
        if (val == 0) {
            // Potential root. Verify with h-1 (should be > 0 if h > 1)
            // Actually for h=2, h-1=1. query(u, 2)=0.
            // If val == 0, it means height <= h-1. Only root satisfies this.
            root = u;
            break;
        }
    }

    // Calculate W_i
    vector<long long> W(h, 0); // W[0] is f_root (unknown), W[1]..W[h-1] known
    long long sum_W_known = 0;
    for (int d = 1; d < h; ++d) {
        W[d] = query(root, d);
        sum_W_known += W[d];
    }
    
    long long S_leaves = W[h - 1];
    
    // Equation:
    // Q_total = 3*S - f_root - 2*S_leaves
    // S = f_root + sum_W_known
    // Q_total = 3*(f_root + sum_W_known) - f_root - 2*S_leaves
    // Q_total = 2*f_root + 3*sum_W_known - 2*S_leaves
    // 2*f_root = Q_total - 3*sum_W_known + 2*S_leaves
    
    long long rhs = Q_total - 3 * sum_W_known + 2 * S_leaves;
    long long f_root = rhs / 2;
    
    long long S = f_root + sum_W_known;
    
    cout << "! " << S << endl;

    return 0;
}