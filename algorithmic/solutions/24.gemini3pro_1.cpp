#include <iostream>
#include <vector>
#include <algorithm>
#include <string>

using namespace std;

// Global matrix to store the graph
int C[2005][2005];
int n;

// Function to calculate the number of cyclic color switches in a cycle
int count_switches(const vector<int>& p) {
    int sw = 0;
    int sz = p.size();
    if (sz < 2) return 0;
    for (int i = 0; i < sz; ++i) {
        int u = p[i];
        int v = p[(i + 1) % sz];
        int next_u = p[(i + 1) % sz];
        int next_v = p[(i + 2) % sz];
        if (C[u][v] != C[next_u][next_v]) {
            sw++;
        }
    }
    return sw;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    while (cin >> n) {
        // Reading the matrix
        // The input format specifies n integers per line, but sample shows no spaces.
        // We read as characters to be safe for both cases.
        for (int i = 1; i <= n; ++i) {
            for (int j = 1; j <= n; ++j) {
                char c;
                cin >> c;
                C[i][j] = c - '0';
            }
        }

        if (n == 0) continue; 

        // Construct a cycle with at most 2 color switches
        vector<int> cycle;
        cycle.push_back(1);

        // Current cyclic switches count
        int current_switches = 0;

        for (int i = 2; i <= n; ++i) {
            int sz = cycle.size();
            bool inserted = false;

            // Try to insert vertex i into the cycle to maintain <= 2 switches
            for (int j = 0; j < sz; ++j) {
                // We consider inserting i between u and v
                // u is cycle[j], v is cycle[(j+1)%sz]
                // Predecessor of u is pre, Successor of v is post
                
                // For sz=1, handled separately or by logic if careful
                if (sz == 1) {
                    cycle.insert(cycle.begin() + j + 1, i);
                    // For size 2 (1, i), edges are (1,i) and (i,1). Same color. Switches=0.
                    current_switches = 0;
                    inserted = true;
                    break;
                }

                int u = cycle[j];
                int v = cycle[(j + 1) % sz];
                int pre = cycle[(j - 1 + sz) % sz];
                int post = cycle[(j + 2) % sz];

                // Calculate the change in switches
                // Switches removed: at u (between pre->u and u->v) and at v (between u->v and v->post)
                int lost = 0;
                if (C[pre][u] != C[u][v]) lost++;
                if (C[u][v] != C[v][post]) lost++;

                // Switches added: at u (pre->u, u->i), at i (u->i, i->v), at v (i->v, v->post)
                int gained = 0;
                if (C[pre][u] != C[u][i]) gained++;
                if (C[u][i] != C[i][v]) gained++;
                if (C[i][v] != C[v][post]) gained++;

                if (current_switches - lost + gained <= 2) {
                    cycle.insert(cycle.begin() + j + 1, i);
                    current_switches = current_switches - lost + gained;
                    inserted = true;
                    break;
                }
            }
        }

        // Now we have a valid cycle. We need to find the rotation that gives the 
        // lexicographically smallest almost monochromatic permutation.
        // "Almost monochromatic" means linear sequence c_1...c_n has <= 1 switch.
        
        vector<int> best_p;
        
        // Create a doubled cycle for easy linear slicing
        vector<int> dcycle = cycle;
        dcycle.insert(dcycle.end(), cycle.begin(), cycle.end());

        for (int i = 0; i < n; ++i) {
            // Extract permutation starting at i
            vector<int> p;
            p.reserve(n);
            for(int k=0; k<n; ++k) p.push_back(dcycle[i+k]);

            // Check linear switches
            int linear_switches = 0;
            // Iterate 1 <= k < n. Indices in p are 0-based.
            // c_k corresponds to edge (p[k-1], p[k])? No, problem says:
            // c_i = C_{p_i, p_{i+1}}.
            // So we check diff between c_k and c_{k+1}.
            // range of i for check is 1 to n-1.
            // array indices: c[0] vs c[1], ..., c[n-2] vs c[n-1].
            // c[n-1] is edge (p[n-1], p[0]).
            
            for (int k = 0; k < n - 1; ++k) {
                int u = p[k];
                int v = p[k+1];
                int color_curr = C[u][v];

                int next_u, next_v;
                if (k + 1 < n - 1) {
                    next_u = p[k+1];
                    next_v = p[k+2];
                } else {
                    // Last comparison: c_{n-1} vs c_n
                    next_u = p[n-1];
                    next_v = p[0];
                }
                int color_next = C[next_u][next_v];
                
                if (color_curr != color_next) {
                    linear_switches++;
                }
            }

            if (linear_switches <= 1) {
                if (best_p.empty() || p < best_p) {
                    best_p = p;
                }
            }
        }

        if (best_p.empty()) {
            cout << -1 << "\n";
        } else {
            for (int i = 0; i < n; ++i) {
                cout << best_p[i] << (i == n - 1 ? "" : " ");
            }
            cout << "\n";
        }
    }
    return 0;
}