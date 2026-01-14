#include <iostream>
#include <vector>
#include <string>

using namespace std;

int main() {
    // Optimize I/O operations
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n;
    if (!(cin >> n)) return 0;

    // We use strings of the form w_i = X^{A_i} O X^C.
    // The number of distinct substrings of w_u + w_v (X^{A_u} O X^{C+A_v} O X^C)
    // is given by P = (C + A_v + 1) * (A_u + C + 3), provided A_u < C + A_v and C < C + A_v.
    // By choosing C = 3*n, we ensure these conditions are met because A_i will be approx n..2n.
    
    int C = 3 * n;
    
    // Z[i] corresponds to A[i] + C + 1.
    // So P(u, v) = Z[v] * (Z[u] + 2).
    // We construct Z[1]...Z[n] such that all P(u, v) are distinct.
    
    vector<int> Z(n + 1);
    // Estimated max Z is around 4*n (C + n).
    // Max P is roughly (4n) * (4n) = 16n^2. For n=1000, 1.6e7.
    // We allocate 4e7 to be safe.
    const int MAX_VAL = 40000000;
    
    // vector<bool> is space-efficient (1 bit per element).
    vector<bool> used(MAX_VAL, false);

    int current_val = C + 2; // Since A_i >= 1 => Z_i >= C+2
    
    for (int k = 1; k <= n; ++k) {
        while (true) {
            bool ok = true;
            // We are adding the k-th word, which introduces Z[k].
            // This creates new power values for pairs (k, i) and (i, k) for i < k, and (k, k).
            // P(i, k) = Z[k] * (Z[i] + 2)
            // P(k, i) = Z[i] * (Z[k] + 2)
            // P(k, k) = Z[k] * (Z[k] + 2)
            // We must ensure these are unique wrt 'used' and distinct amongst themselves.

            // Check P(i, k) for i < k
            for (int i = 1; i < k; ++i) {
                long long p = (long long)current_val * (Z[i] + 2);
                if (p >= MAX_VAL || used[p]) { ok = false; break; }
            }
            if (!ok) { current_val++; continue; }

            // Check P(k, i) for i < k
            for (int i = 1; i < k; ++i) {
                long long p = (long long)Z[i] * (current_val + 2);
                if (p >= MAX_VAL || used[p]) { ok = false; break; }
            }
            if (!ok) { current_val++; continue; }

            // Check P(k, k)
            long long p3 = (long long)current_val * (current_val + 2);
            if (p3 >= MAX_VAL || used[p3]) { ok = false; current_val++; continue; }

            // Check for collisions within the new set of values
            // P(i, k) vs P(k, j). i, j < k.
            // Z[k]*(Z[i]+2) vs Z[j]*(Z[k]+2)
            // current*(Z[i]+2) vs Z[j]*(current+2)
            for (int i = 1; i < k; ++i) {
                long long val1 = (long long)current_val * (Z[i] + 2);
                for (int j = 1; j < k; ++j) {
                    long long val2 = (long long)Z[j] * (current_val + 2);
                    if (val1 == val2) { ok = false; break; }
                }
                if (!ok) break;
            }
            if (!ok) { current_val++; continue; }
            
            // Note: P(i, k) vs P(j, k) is impossible for i!=j because Z distinct.
            // Similarly P(k, i) vs P(k, j).
            // P(k, k) vs others: P(k, k) > P(k, i) and P(k, k) > P(i, k) since Z[k] > Z[i].
            
            // All checks passed
            for (int i = 1; i < k; ++i) {
                used[(long long)current_val * (Z[i] + 2)] = true;
                used[(long long)Z[i] * (current_val + 2)] = true;
            }
            used[p3] = true;
            Z[k] = current_val;
            break;
        }
        current_val++;
    }

    // Output the magic words
    for (int i = 1; i <= n; ++i) {
        int Ai = Z[i] - C - 1;
        // w_i = X^{A_i} O X^C
        string s = "";
        s.append(Ai, 'X');
        s += 'O';
        s.append(C, 'X');
        cout << s << "\n";
    }
    cout.flush();

    // Prepare lookup table for queries
    // Memory usage: 40M ints = 160MB, fits in 256MB.
    vector<int> lookup(MAX_VAL, 0);
    for (int u = 1; u <= n; ++u) {
        for (int v = 1; v <= n; ++v) {
            long long P = (long long)Z[v] * (Z[u] + 2);
            if (P < MAX_VAL) {
                // Encode u and v. u, v <= 1000. 2000 is safe base.
                lookup[P] = u * 2000 + v;
            }
        }
    }

    int q;
    if (cin >> q) {
        for (int k = 0; k < q; ++k) {
            int p_val;
            cin >> p_val;
            if (p_val < MAX_VAL && lookup[p_val] != 0) {
                int code = lookup[p_val];
                cout << code / 2000 << " " << code % 2000 << "\n";
            } else {
                // Should not happen given problem constraints
                cout << "1 1\n"; 
            }
            cout.flush();
        }
    }

    return 0;
}