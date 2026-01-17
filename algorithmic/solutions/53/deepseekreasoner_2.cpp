#include <iostream>
#include <vector>
#include <functional>
#include <algorithm>
#include <cassert>

using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int t;
    cin >> t;
    while (t--) {
        int n;
        cin >> n;

        // Choose k = 1
        cout << 1 << endl;

        // Query identity permutation
        cout << "?";
        for (int i = 1; i <= n; ++i) cout << " " << i;
        cout << endl;
        int base;
        cin >> base;

        vector<int> D(n + 1); // D[x] for x >= 2
        for (int x = 2; x <= n; ++x) {
            // Construct permutation Q_x: swap 1 and x
            cout << "? " << x;
            for (int i = 2; i < x; ++i) cout << " " << i;
            cout << " 1";
            for (int i = x + 1; i <= n; ++i) cout << " " << i;
            cout << endl;
            int ans;
            cin >> ans;
            D[x] = ans - base;
        }

        // Now try all possibilities for p1 and r1
        bool found = false;
        for (int p1 = 2; p1 <= n && !found; ++p1) {
            for (int r1 = 2; r1 <= n && !found; ++r1) {
                // Compute C[i] for i = 2..n
                vector<int> C(n + 1);
                bool ok = true;
                for (int i = 2; i <= n; ++i) {
                    int val = (p1 > i ? 1 : 0) + (r1 < i ? 1 : 0) - D[i];
                    if (val < 0 || val > 2) {
                        ok = false;
                        break;
                    }
                    C[i] = val;
                }
                if (!ok) continue;

                // Initialize arrays
                vector<int> p(n + 1, -1), inv(n + 1, -1);
                vector<bool> used_idx(n + 1, false), used_val(n + 1, false);

                // Fixed assignments
                p[1] = p1;
                inv[p1] = 1;
                used_idx[1] = true;
                used_val[p1] = true;

                // p[r1] = 1
                if (p[r1] != -1 && p[r1] != 1) continue;
                if (inv[1] != -1 && inv[1] != r1) continue;
                p[r1] = 1;
                inv[1] = r1;
                used_idx[r1] = true;
                used_val[1] = true;

                // Depth-first search to assign the remaining positions
                function<bool()> dfs = [&]() -> bool {
                    // Find the smallest unassigned index (>=2)
                    int i = -1;
                    for (int j = 2; j <= n; ++j) {
                        if (!used_idx[j]) {
                            i = j;
                            break;
                        }
                    }
                    if (i == -1) {
                        // All indices assigned, verify all conditions
                        for (int j = 2; j <= n; ++j) {
                            int val = (p[j] > j ? 1 : 0) + (inv[j] < j ? 1 : 0);
                            if (val != C[j]) return false;
                        }
                        return true;
                    }

                    // Try possible values for p[i]
                    for (int v = 1; v <= n; ++v) {
                        if (used_val[v] || v == i) continue;

                        // Check condition for i with this v
                        bool inv_i_known = (inv[i] != -1);
                        int known_part_i = (v > i ? 1 : 0);
                        int required_i = C[i] - known_part_i;
                        if (required_i < 0 || required_i > 1) continue;
                        if (inv_i_known) {
                            int j = inv[i];
                            if ((j < i ? 1 : 0) != required_i) continue;
                        } else {
                            // Check existence of a suitable j for inv[i]
                            bool exists = false;
                            for (int j = 2; j <= n; ++j) {
                                if (!used_idx[j] && (j < i ? 1 : 0) == required_i) {
                                    exists = true;
                                    break;
                                }
                            }
                            if (!exists) continue;
                        }

                        // Check condition for index v (if p[v] known)
                        bool pv_known = (p[v] != -1);
                        if (pv_known) {
                            int val_v = (p[v] > v ? 1 : 0) + (i < v ? 1 : 0);
                            if (val_v != C[v]) continue;
                        } else {
                            int known_part_v = (i < v ? 1 : 0);
                            int required_v = C[v] - known_part_v;
                            if (required_v < 0 || required_v > 1) continue;
                        }

                        // Make assignment
                        p[i] = v;
                        inv[v] = i;
                        used_idx[i] = true;
                        used_val[v] = true;

                        if (dfs()) return true;

                        // Backtrack
                        p[i] = -1;
                        inv[v] = -1;
                        used_idx[i] = false;
                        used_val[v] = false;
                    }
                    return false;
                };

                if (dfs()) {
                    // Verify against all queries
                    bool valid = true;

                    // Verify identity query
                    int calc_base = 0;
                    for (int i = 2; i <= n; ++i)
                        if (p[i] > i) calc_base++;
                    if (calc_base != base) valid = false;

                    // Verify each Q_x query
                    for (int x = 2; x <= n && valid; ++x) {
                        vector<int> q(n + 1);
                        q[1] = x;
                        for (int i = 2; i < x; ++i) q[i] = i;
                        q[x] = 1;
                        for (int i = x + 1; i <= n; ++i) q[i] = i;

                        int cnt = 0;
                        for (int i = 2; i <= n; ++i) {
                            int val = p[q[i]];
                            // find position of val in q
                            int pos = -1;
                            for (int j = 1; j <= n; ++j)
                                if (q[j] == val) { pos = j; break; }
                            if (pos > i) cnt++;
                        }
                        if (cnt != base + D[x]) { valid = false; break; }
                    }

                    if (valid) {
                        cout << "!";
                        for (int i = 1; i <= n; ++i) cout << " " << p[i];
                        cout << endl;
                        found = true;
                        break;
                    }
                }
            }
        }
        // Ensure output is flushed
        cout.flush();
    }
    return 0;
}