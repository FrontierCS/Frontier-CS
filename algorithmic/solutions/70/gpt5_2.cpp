#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int t;
    if (!(cin >> t)) return 0;
    for (int tc = 0; tc < t; ++tc) {
        int n, m, start, base;
        cin >> n >> m >> start >> base;
        for (int i = 0; i < m; ++i) {
            int u, v;
            cin >> u >> v;
        }
        
        int prev_deg = -1; // degree of the vertex we came from (for backtrack avoidance)
        while (true) {
            string tok;
            if (!(cin >> tok)) return 0;
            if (tok == "AC" || tok == "F") {
                // Map finished
                prev_deg = -1;
                break;
            }
            int d = stoi(tok);
            vector<int> deg(d), flag(d);
            for (int i = 0; i < d; ++i) {
                cin >> deg[i] >> flag[i];
            }
            
            // Decide move:
            // 1) Prefer any unvisited neighbor (flag == 0), pick one with max degree.
            // 2) If none, pick visited neighbor with degree != prev_deg and maximal degree.
            // 3) If none, pick visited neighbor with maximal degree.
            int best_idx = 0;
            int best_deg = -1;
            bool found_unvisited = false;
            for (int i = 0; i < d; ++i) {
                if (flag[i] == 0) {
                    if (!found_unvisited || deg[i] > best_deg) {
                        found_unvisited = true;
                        best_deg = deg[i];
                        best_idx = i;
                    }
                }
            }
            if (!found_unvisited) {
                int best_idx_nb = -1, best_deg_nb = -1;
                for (int i = 0; i < d; ++i) {
                    if (flag[i] == 1 && deg[i] != prev_deg) {
                        if (deg[i] > best_deg_nb) {
                            best_deg_nb = deg[i];
                            best_idx_nb = i;
                        }
                    }
                }
                if (best_idx_nb != -1) {
                    best_idx = best_idx_nb;
                } else {
                    // Fall back: pick visited neighbor with maximum degree
                    int best_idx_any = 0, best_deg_any = -1;
                    for (int i = 0; i < d; ++i) {
                        if (deg[i] > best_deg_any) {
                            best_deg_any = deg[i];
                            best_idx_any = i;
                        }
                    }
                    best_idx = best_idx_any;
                }
            }
            
            cout << (best_idx + 1) << endl;
            cout.flush();
            prev_deg = d; // current degree becomes previous degree for the next step
        }
    }
    return 0;
}