#include <iostream>
#include <vector>
#include <string>
#include <numeric>
#include <algorithm>

using namespace std;

int adj[101][101];
const int N = 100;

int query(int a, int b, int c) {
    cout << "? " << a << " " << b << " " << c << endl;
    int response;
    cin >> response;
    return response;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int p1 = -1, p2 = -1;

    // First, check for a complete graph, a very special case.
    // Query a few random-ish triples. If all are 3, it's likely a complete graph.
    bool maybe_complete = true;
    int first_q = query(1, 2, 3);
    if (first_q != 3) {
        maybe_complete = false;
    } else {
        if (query(1, 2, 4) != 3 || query(1, 3, 5) != 3 || query(2, 4, 6) != 3) {
            maybe_complete = false;
        }
    }
    
    if (maybe_complete) {
        bool is_definitely_complete = true;
        for (int i = 3; i <= N; ++i) {
            if (query(1, 2, i) != 3) {
                is_definitely_complete = false;
                break;
            }
        }
        if (is_definitely_complete) {
            // It seems 1 and 2 are connected and are connected to all other vertices.
            // Let's assume vertex 1 is connected to all others.
            for (int i = 1; i <= N; ++i) {
                for (int j = 1; j <= N; ++j) {
                    if (i == j) adj[i][j] = 0;
                    else adj[i][j] = 1;
                }
            }
            // Verify remaining edges
            for (int i = 2; i <= N; ++i) {
                for (int j = i + 1; j <= N; ++j) {
                    int res = query(1, i, j);
                    if (res != 3) {
                        adj[i][j] = adj[j][i] = 0;
                    }
                }
            }
            cout << "!" << endl;
            for (int i = 1; i <= N; ++i) {
                string row = "";
                for (int j = 1; j <= N; ++j) {
                    row += to_string(adj[i][j]);
                }
                cout << row << endl;
            }
            return 0;
        }
    }

    // Find a pair of non-adjacent vertices (p1, p2)
    // This is guaranteed unless the graph is complete.
    for (int i = 1; i <= N && p1 == -1; ++i) {
        for (int j = i + 1; j <= N && p1 == -1; ++j) {
            for (int k = j + 1; k <= N && p1 == -1; ++k) {
                if (query(i, j, k) == 0) {
                    p1 = i;
                    p2 = j;
                    adj[i][k] = adj[k][i] = 0;
                    adj[j][k] = adj[k][j] = 0;
                    break;
                }
            }
        }
    }
    
    // Fallback if the above simple search fails
    if (p1 == -1) {
        for (int i = 1; i <= N; ++i) {
            for (int j = i + 1; j <= N; ++j) {
                bool found_non_adj = false;
                for (int k = 1; k <= N; ++k) {
                    if (k == i || k == j) continue;
                    if (query(i, j, k) < 3) {
                        // Found a non-edge among {i, j, k}
                        int other = 1;
                        while(other == i || other == j || other == k) other++;
                        int q_ijo = query(i, j, other);
                        int q_iko = query(i, k, other);
                        int q_jko = query(j, k, other);

                        if (query(i, j, k) + q_ijo - q_iko - q_jko != 0) { // check E(i,k)-E(j,k)
                            // i,j are not symmetric wrt k,other
                        }
                        // This logic is complex, simple BFS-like search for non-adj is better
                        // But since a non-edge exists, let's find it.
                        int q_ijk_p_ijo = query(i,j,k) + q_ijo;
                        if(q_ijk_p_ijo == q_iko + q_jko) { // E(i,j) = E(k,other)
                            // Can't determine from this
                        }
                    }
                }
            }
        }
        p1=1; p2=2; // As a last resort, assume this.
    }

    adj[p1][p2] = adj[p2][p1] = 0;

    vector<int> S0, S1, S2;
    vector<int> others;
    for (int i = 1; i <= N; ++i) {
        if (i != p1 && i != p2) others.push_back(i);
    }

    for (int v : others) {
        if (adj[p1][v] != -1) continue; // Already determined from a query(p1,p2,v)==0
        int sum_p1v_p2v = query(p1, p2, v);
        if (sum_p1v_p2v == 0) S0.push_back(v);
        else if (sum_p1v_p2v == 1) S1.push_back(v);
        else S2.push_back(v);
    }
    
    for (int v : S0) {
        adj[p1][v] = adj[v][p1] = 0;
        adj[p2][v] = adj[v][p2] = 0;
    }
    for (int v : S2) {
        adj[p1][v] = adj[v][p1] = 1;
        adj[p2][v] = adj[v][p2] = 1;
    }

    if (!S1.empty()) {
        int anchor = S1[0];
        int resolver = -1;
        if (!S0.empty()) resolver = S0[0];
        else if (!S2.empty()) resolver = S2[0];
        else { // All others are in S1
            if (others.size() > 1) resolver = others[1];
        }

        int E_p1_anchor, E_p2_anchor;
        if (!S0.empty() || !S2.empty()) {
            int q_p1_ar = query(p1, anchor, resolver);
            int q_p2_ar = query(p2, anchor, resolver);
            int E_p1_r = adj[p1][resolver];
            int E_p2_r = adj[p2][resolver];
            int diff = q_p1_ar - q_p2_ar - (E_p1_r - E_p2_r);
            E_p1_anchor = (diff + 1) / 2;
        } else { // All vertices are in S1
            int v2 = S1[1];
            int q_p1_av2 = query(p1, anchor, v2);
            int q_p2_av2 = query(p2, anchor, v2);
            int sum_p1_av2 = (q_p1_av2 - q_p2_av2 + 2) / 2;
            
            // Assume E(p1, anchor)=0 to start
            E_p1_anchor = 0;
            int E_p1_v2 = sum_p1_av2 - E_p1_anchor;
            
            // Verify with a third vertex from S1
            if (S1.size() > 2) {
                int v3 = S1[2];
                int E_a_v2 = q_p1_av2 - E_p1_anchor - E_p1_v2;
                int q_p1_av3 = query(p1, anchor, v3);
                int q_p1_v2v3 = query(p1, v2, v3);
                int E_p1_v3 = ( (q_p1_av2 - q_p2_av2 + 2)/2 + (query(p1, anchor, v3) - query(p2, anchor, v3) + 2)/2 - ( (query(p1, v2, v3) - query(p2, v2, v3) + 2)/2) ) / 2 - E_p1_anchor;

                int E_a_v3 = q_p1_av3 - E_p1_anchor - E_p1_v3;
                int E_v2_v3 = q_p1_v2v3 - E_p1_v2 - E_p1_v3;

                if (query(anchor, v2, v3) != E_a_v2 + E_a_v3 + E_v2_v3) {
                    E_p1_anchor = 1; // Flip assumption
                }
            } else { // Only two vertices in S1, no way to distinguish
                E_p1_anchor = 0; // Arbitrary choice
            }
        }
        
        adj[p1][anchor] = adj[anchor][p1] = E_p1_anchor;
        adj[p2][anchor] = adj[anchor][p2] = 1 - E_p1_anchor;

        for (size_t i = 1; i < S1.size(); ++i) {
            int v = S1[i];
            int q_p1_av = query(p1, anchor, v);
            int q_p2_av = query(p2, anchor, v);
            int sum_p1_av = (q_p1_av - q_p2_av + 2) / 2;
            adj[p1][v] = adj[v][p1] = sum_p1_av - adj[p1][anchor];
            adj[p2][v] = adj[v][p2] = 1 - adj[p1][v];
        }
    }
    
    for (size_t i = 0; i < others.size(); ++i) {
        for (size_t j = i + 1; j < others.size(); ++j) {
            int u = others[i], v = others[j];
            int res = query(p1, u, v);
            adj[u][v] = adj[v][u] = res - adj[p1][u] - adj[p1][v];
        }
    }
    
    for (int i = 1; i <= N; ++i) adj[i][i] = 0;

    cout << "!" << endl;
    for (int i = 1; i <= N; ++i) {
        string row = "";
        for (int j = 1; j <= N; ++j) {
            row += to_string(adj[i][j]);
        }
        cout << row << endl;
    }

    return 0;
}