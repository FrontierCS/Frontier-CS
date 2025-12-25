#include <bits/stdc++.h>
using namespace std;

int main() {
    vector<vector<string>> possible;
    int n = 100;
    int m = 0;

    // Add vertex 1
    possible.clear();
    vector<string> g(101, string(101, '0'));
    possible.push_back(g);
    m = 1;

    // Add vertex 2, two possibles
    possible.clear();
    vector<string> g0(101, string(101, '0'));
    g0[1][2] = g0[2][1] = '0';
    possible.push_back(g0);
    vector<string> g1(101, string(101, '0'));
    g1[1][2] = g1[2][1] = '1';
    possible.push_back(g1);
    m = 2;

    for (int newv = 3; newv <= n; ++newv) {
        // Query ? 1 i newv for i=2 to m
        vector<int> q(m + 1, 0);
        for (int i = 2; i <= m; ++i) {
            cout << "? 1 " << i << " " << newv << endl;
            fflush(stdout);
            int s;
            cin >> s;
            q[i] = s;
        }

        // Check if extra needed
        int num_prev = possible.size();
        vector<bool> needs_extra(num_prev, false);
        bool do_extra = false;
        for (int p = 0; p < num_prev; ++p) {
            bool all_one = true;
            for (int i = 2; i <= m; ++i) {
                int a1i = possible[p][1][i] - '0';
                int si = q[i] - a1i;
                if (si < 0 || si > 2) {
                    all_one = false;
                    break;
                }
                if (si != 1) all_one = false;
            }
            needs_extra[p] = all_one;
            if (all_one) do_extra = true;
        }

        int extra_resp = -1;
        if (do_extra && m >= 3) {
            cout << "? 2 3 " << newv << endl;
            fflush(stdout);
            cin >> extra_resp;
        }

        // Create new possible
        vector<vector<string>> new_possible;
        for (int p = 0; p < num_prev; ++p) {
            // Compute s
            vector<int> s(m + 1, 0);
            bool valid = true;
            for (int i = 2; i <= m; ++i) {
                int a1i = possible[p][1][i] - '0';
                s[i] = q[i] - a1i;
                if (s[i] < 0 || s[i] > 2) {
                    valid = false;
                    break;
                }
            }
            if (!valid) continue;

            // Check if ambiguous
            bool ambig = true;
            for (int i = 2; i <= m; ++i) {
                if (s[i] != 1) ambig = false;
            }

            vector<int> x(m + 1, -1);
            if (ambig) {
                if (m < 3) {
                    // Special for m=2, add two
                    vector<string> new_adj = possible[p];
                    // x1=0, x2=1
                    new_adj[1][newv] = new_adj[newv][1] = '0';
                    new_adj[2][newv] = new_adj[newv][2] = '1';
                    new_possible.push_back(new_adj);
                    // x1=1, x2=0
                    new_adj = possible[p];
                    new_adj[1][newv] = new_adj[newv][1] = '1';
                    new_adj[2][newv] = new_adj[newv][2] = '0';
                    new_possible.push_back(new_adj);
                    continue;
                } else {
                    // Use extra
                    int a23 = possible[p][2][3] - '0';
                    int t = extra_resp - a23;
                    if (t < 0 || t > 2 || (t != 0 && t != 2)) continue;
                    if (t == 0) {
                        x[1] = 1;
                        for (int i = 2; i <= m; ++i) x[i] = 0;
                    } else {
                        x[1] = 0;
                        for (int i = 2; i <= m; ++i) x[i] = 1;
                    }
                    // Check match
                    bool ok = true;
                    for (int i = 2; i <= m; ++i) {
                        if (x[1] + x[i] != 1) ok = false;
                    }
                    if (!ok) continue;
                }
            } else {
                // Non-ambiguous
                int min_s = 3, max_s = -1;
                for (int i = 2; i <= m; ++i) {
                    min_s = min(min_s, s[i]);
                    max_s = max(max_s, s[i]);
                }
                bool set_ok = false;
                if (min_s == 0) {
                    if (max_s <= 1) {
                        x[1] = 0;
                        for (int i = 2; i <= m; ++i) x[i] = s[i];
                        set_ok = true;
                    }
                } else if (min_s == 2 && max_s == 2) {
                    x[1] = 1;
                    for (int i = 2; i <= m; ++i) x[i] = 1;
                    set_ok = true;
                } else if (min_s == 1 && max_s == 2) {
                    x[1] = 1;
                    for (int i = 2; i <= m; ++i) x[i] = s[i] - 1;
                    set_ok = true;
                }
                if (!set_ok) continue;
                // Check all x in 0,1
                bool ok = true;
                for (int i = 1; i <= m; ++i) {
                    if (x[i] < 0 || x[i] > 1) ok = false;
                }
                if (!ok) continue;
                // Check match s
                ok = true;
                for (int i = 2; i <= m; ++i) {
                    if (s[i] != x[1] + x[i]) ok = false;
                }
                if (!ok) continue;
            }

            // Valid x, create new_adj
            vector<string> new_adj = possible[p];
            for (int i = 1; i <= m; ++i) {
                new_adj[i][newv] = '0' + x[i];
                new_adj[newv][i] = '0' + x[i];
            }
            new_adj[newv][newv] = '0';
            new_possible.push_back(new_adj);
        }
        possible = new_possible;
        m = newv;

        // Resolve if multiple
        while (possible.size() > 1 && m >= 3) {
            // Find distinguishing triple
            bool found = false;
            int a = -1, b = -1, c = -1;
            for (int i1 = 1; i1 <= m && !found; ++i1) {
                for (int i2 = i1 + 1; i2 <= m && !found; ++i2) {
                    for (int i3 = i2 + 1; i3 <= m && !found; ++i3) {
                        set<int> sums_set;
                        for (const auto& gg : possible) {
                            int sum = (gg[i1][i2] - '0') + (gg[i1][i3] - '0') + (gg[i2][i3] - '0');
                            sums_set.insert(sum);
                        }
                        if (sums_set.size() > 1) {
                            found = true;
                            a = i1; b = i2; c = i3;
                        }
                    }
                }
            }
            if (!found) {
                // Should not happen, take first
                possible.resize(1);
                break;
            }
            // Query
            cout << "? " << a << " " << b << " " << c << endl;
            fflush(stdout);
            int resp;
            cin >> resp;
            // Filter
            vector<vector<string>> temp;
            for (const auto& gg : possible) {
                int sum = (gg[a][b] - '0') + (gg[a][c] - '0') + (gg[b][c] - '0');
                if (sum == resp) temp.push_back(gg);
            }
            possible = temp;
        }
    }

    // Output
    cout << "!" << endl;
    for (int i = 1; i <= 100; ++i) {
        cout << possible[0][i].substr(1, 100) << endl;
    }
    fflush(stdout);
    return 0;
}