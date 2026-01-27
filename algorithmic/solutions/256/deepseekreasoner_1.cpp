#include <iostream>
#include <vector>
#include <string>
#include <cmath>
#include <algorithm>

using namespace std;

int N;
int val[55][55];
vector<pair<int, int>> clusters[105]; 

// Memoization for check_conn
bool memo_conn[55][55][55][55];
bool visited_conn[55][55][55][55];

int query(int r1, int c1, int r2, int c2) {
    cout << "? " << r1 << " " << c1 << " " << r2 << " " << c2 << endl;
    int res;
    cin >> res;
    if (res == -1) exit(0);
    return res;
}

// Checks if there exists a palindromic path between (r1, c1) and (r2, c2)
// using the PREVIOUSLY determined inner layers.
// Since we process inside-out, the inner diagonal values are fixed relative to their component.
bool check_conn(int r1, int c1, int r2, int c2) {
    // Base case: distance 2.
    // For t=1 (in main loop), we invoke this on neighbors (dist 2).
    if (r1 + c1 + 2 == r2 + c2) return true;
    
    if (visited_conn[r1][c1][r2][c2]) return memo_conn[r1][c1][r2][c2];
    
    bool res = false;
    int r1_next[2] = {r1 + 1, r1};
    int c1_next[2] = {c1, c1 + 1};
    int r2_prev[2] = {r2 - 1, r2};
    int c2_prev[2] = {c2, c2 - 1};
    
    for (int k1 = 0; k1 < 2; ++k1) {
        for (int k2 = 0; k2 < 2; ++k2) {
            int nr1 = r1_next[k1];
            int nc1 = c1_next[k1];
            int nr2 = r2_prev[k2];
            int nc2 = c2_prev[k2];
            if (nr1 > nr2 || nc1 > nc2) continue;
            
            // Should always be valid within grid given loop constraints
            
            if (val[nr1][nc1] == val[nr2][nc2]) {
                if (check_conn(nr1, nc1, nr2, nc2)) {
                    res = true;
                    goto done;
                }
            }
        }
    }
    
    done:
    visited_conn[r1][c1][r2][c2] = true;
    memo_conn[r1][c1][r2][c2] = res;
    return res;
}

int main() {
    ios_base::sync_with_stdio(false);
    
    cin >> N;
    
    for (int i = 1; i <= N; ++i) {
        for (int j = 1; j <= N; ++j) {
            val[i][j] = -1;
            clusters[i + j].push_back({i, j});
        }
    }

    // Fixed values
    val[1][1] = 1;
    val[N][N] = 0;

    // Process layers inside-out
    // t=0: Diagonals N and N+2
    // t goes up to N-2 (Diagonals 2 and 2N)
    for (int t = 0; t <= N - 2; ++t) {
        int L = N - t;
        int R = N + 2 + t;
        
        vector<pair<int, int>>& qL = clusters[L];
        vector<pair<int, int>>& qR = clusters[R];
        
        int szL = qL.size();
        int szR = qR.size();
        
        // Adjacency matrix for bipartite graph
        vector<vector<bool>> adj(szL, vector<bool>(szR, false));
        
        for (int i = 0; i < szL; ++i) {
            for (int j = 0; j < szR; ++j) {
                int r1 = qL[i].first;
                int c1 = qL[i].second;
                int r2 = qR[j].first;
                int c2 = qR[j].second;
                
                if (r1 > r2 || c1 > c2) continue;

                if (t == 0) {
                    adj[i][j] = true;
                } else {
                    bool ok = false;
                    int r1_next[2] = {r1 + 1, r1};
                    int c1_next[2] = {c1, c1 + 1};
                    int r2_prev[2] = {r2 - 1, r2};
                    int c2_prev[2] = {c2, c2 - 1};
                    
                    for (int k1 = 0; k1 < 2; ++k1) {
                        for (int k2 = 0; k2 < 2; ++k2) {
                            int nr1 = r1_next[k1];
                            int nc1 = c1_next[k1];
                            int nr2 = r2_prev[k2];
                            int nc2 = c2_prev[k2];
                            
                            if (nr1 > nr2 || nc1 > nc2) continue;
                            
                            if (val[nr1][nc1] != -1 && val[nr2][nc2] != -1 && val[nr1][nc1] == val[nr2][nc2]) {
                                if (check_conn(nr1, nc1, nr2, nc2)) {
                                    ok = true;
                                    break;
                                }
                            }
                        }
                        if (ok) break;
                    }
                    if (ok) adj[i][j] = true;
                }
            }
        }
        
        vector<int> L_nodes(szL, 0); 
        vector<int> R_nodes(szR, 0); 
        vector<pair<int, int>> q; 

        // Add already known nodes to queue
        for (int i=0; i<szL; ++i) {
            if (val[qL[i].first][qL[i].second] != -1) {
                q.push_back({0, i});
                L_nodes[i] = 1;
            }
        }
        for (int j=0; j<szR; ++j) {
            if (val[qR[j].first][qR[j].second] != -1) {
                q.push_back({1, j});
                R_nodes[j] = 1;
            }
        }
        
        // Seed if empty
        if (q.empty()) {
             val[qL[0].first][qL[0].second] = 0;
             L_nodes[0] = 1;
             q.push_back({0, 0});
        }
        
        int head = 0;
        while(true) {
            while(head < q.size()) {
                pair<int, int> curr = q[head++];
                int is_R = curr.first;
                int idx = curr.second;
                int my_val = (is_R ? val[qR[idx].first][qR[idx].second] : val[qL[idx].first][qL[idx].second]);
                
                if (!is_R) { // From L
                    for (int j=0; j<szR; ++j) {
                        if (adj[idx][j] && !R_nodes[j]) {
                            int res = query(qL[idx].first, qL[idx].second, qR[j].first, qR[j].second);
                            int other_val = (res == 1 ? my_val : 1 - my_val);
                            val[qR[j].first][qR[j].second] = other_val;
                            R_nodes[j] = 1;
                            q.push_back({1, j});
                        }
                    }
                } else { // From R
                    for (int i=0; i<szL; ++i) {
                        if (adj[i][idx] && !L_nodes[i]) {
                            int res = query(qL[i].first, qL[i].second, qR[idx].first, qR[idx].second);
                            int other_val = (res == 1 ? my_val : 1 - my_val);
                            val[qL[i].first][qL[i].second] = other_val;
                            L_nodes[i] = 1;
                            q.push_back({0, i});
                        }
                    }
                }
            }
            
            // Check for disconnected parts in this layer
            bool found = false;
            for (int i=0; i<szL; ++i) if (!L_nodes[i]) {
                val[qL[i].first][qL[i].second] = 0; 
                L_nodes[i] = 1;
                q.push_back({0, i});
                found = true;
                break; 
            }
            if (found) continue;

            for (int j=0; j<szR; ++j) if (!R_nodes[j]) {
                val[qR[j].first][qR[j].second] = 0; 
                R_nodes[j] = 1;
                q.push_back({1, j});
                found = true;
                break;
            }
            if (found) continue;

            break;
        }
    }
    
    // Solve S_{N+1}
    int mid = N + 1;
    for (auto p : clusters[mid]) {
        for (auto u : clusters[N - 1]) {
            if (u.first <= p.first && u.second <= p.second) {
               int res = query(u.first, u.second, p.first, p.second);
               val[p.first][p.second] = (res == 1 ? val[u.first][u.second] : 1 - val[u.first][u.second]);
               break;
            }
        }
    }
    
    // Resolve Odd Sum Flip
    int flip = -1;
    vector<pair<int, int>>& qU = clusters[N - 1]; // Known
    vector<pair<int, int>>& qV = clusters[N + 2]; // Needs check
    
    for (auto u : qU) {
        if (flip != -1) break;
        for (auto v : qV) {
            if (flip != -1) break;
            if (u.first > v.first || u.second > v.second) continue;
            
            bool can_inner_0 = false;
            bool can_inner_1 = false;
            
            int da_r[] = {1, 0}; int da_c[] = {0, 1};
            
            for (int k1=0; k1<2; ++k1) {
                int ra = u.first + da_r[k1];
                int ca = u.second + da_c[k1];
                if (ra > N || ca > N) continue; 
                
                int db_r[] = {-1, 0}; int db_c[] = {0, -1};
                for (int k2=0; k2<2; ++k2) {
                    int rb = v.first + db_r[k2];
                    int cb = v.second + db_c[k2];
                    if (rb < 1 || cb < 1) continue; 
                    
                    if (rb >= ra && cb >= ca && (rb+cb == ra+ca+1)) {
                         if (val[ra][ca] == val[rb][cb]) can_inner_0 = true;
                         if (val[ra][ca] != val[rb][cb]) can_inner_1 = true;
                    }
                }
            }
            
            bool expect0 = can_inner_0 && (val[u.first][u.second] == val[v.first][v.second]);
            bool expect1 = can_inner_1 && (val[u.first][u.second] != val[v.first][v.second]);
            
            if (expect0 != expect1) {
                int res = query(u.first, u.second, v.first, v.second);
                if ((res == 1) == expect0) flip = 0; else flip = 1;
            }
        }
    }
    
    if (flip == -1) flip = 0; // Should not happen if distinguishing pair exists
    
    // Apply flip
    for (int k = 3; k <= 2 * N; k += 2) {
        for (auto p : clusters[k]) {
            val[p.first][p.second] ^= flip;
        }
    }
    
    cout << "!" << endl;
    for (int i=1; i<=N; ++i) {
        for (int j=1; j<=N; ++j) {
            cout << val[i][j];
        }
        cout << endl;
    }
    
    return 0;
}