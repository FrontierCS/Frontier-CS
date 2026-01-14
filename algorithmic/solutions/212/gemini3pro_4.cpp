#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <cmath>

using namespace std;

struct Point {
    int x, y;
};

int N, M, L, R, Sx, Sy, Lq, S;
vector<int> Q;

// Global grid to mark used cells for validation
bool used[45][45];

long long solve_cost(const vector<int>& P, vector<Point>& path_out, bool generate_path) {
    // Reset grid
    for(int i=0; i<=N+1; ++i)
        for(int j=0; j<=M+1; ++j) used[i][j] = false;

    path_out.clear();
    long long cost = 0;
    
    // Initial row traversal
    // We are at (Sx, L). We must traverse to R.
    for(int c=L; c<=R; ++c) used[Sx][c] = true;
    
    if(generate_path) {
        for(int c=L; c<=R; ++c) path_out.push_back({Sx, c});
    }
    cost += (R - L); 
    
    // After traversing Sx (L->R), we are at R.
    int side_col = R; 
    
    for (size_t k = 1; k < P.size(); ++k) {
        int u = P[k-1];
        int v = P[k];
        
        int next_side_col = side_col;
        int target_end_col = (side_col == L) ? R : L;
        
        if (abs(u - v) == 1) {
            cost += 1;
            if(generate_path) {
                path_out.push_back({v, side_col});
            }
        } else {
            // Need strip.
            int dc = (side_col == R) ? 1 : -1;
            int best_off = -1;
            for(int off=1; off<=M; ++off) {
                int col = side_col + dc * off;
                if (col < 1 || col > M) break;
                
                bool ok = true;
                int r_start = min(u, v);
                int r_end = max(u, v);
                for(int r = r_start; r <= r_end; ++r) {
                    if (used[r][col]) { ok = false; break; }
                }
                for(int c_check = side_col + dc; c_check != col + dc; c_check += dc) {
                    if (used[u][c_check]) { ok = false; break; }
                }
                for(int c_check = col; c_check != side_col; c_check -= dc) {
                    if (used[v][c_check]) { ok = false; break; }
                }
                
                if (ok) {
                    best_off = off;
                    break;
                }
            }
            
            if (best_off == -1) return -1; // Impossible
            
            int col = side_col + dc * best_off;
            cost += abs(u - v) + 2 * best_off;
            
            int r_start = min(u, v);
            int r_end = max(u, v);
            for(int r = r_start; r <= r_end; ++r) used[r][col] = true;
            for(int c_step = 1; c_step < best_off; ++c_step) {
                used[u][side_col + dc*c_step] = true;
                used[v][side_col + dc*c_step] = true;
            }
            
            if (generate_path) {
                for(int c = side_col + dc; c != col + dc; c += dc) path_out.push_back({u, c});
                int dr = (u < v) ? 1 : -1;
                for(int r = u + dr; r != v + dr; r += dr) path_out.push_back({r, col});
                for(int c = col - dc; c != side_col - dc; c -= dc) path_out.push_back({v, c});
            }
        }
        
        int step = (side_col < target_end_col) ? 1 : -1;
        for(int c = side_col; c != target_end_col + step; c += step) {
            used[v][c] = true;
            if(generate_path) {
                if (c != side_col) path_out.push_back({v, c});
            }
        }
        cost += abs(R - L);
        side_col = target_end_col;
    }
    
    return cost;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    
    if (!(cin >> N >> M >> L >> R >> Sx >> Sy >> Lq >> S)) return 0;
    
    Q.resize(Lq);
    for(int i=0; i<Lq; ++i) cin >> Q[i];
    
    vector<int> C;
    if (Q.empty() || Q[0] != Sx) C.push_back(Sx);
    for(int x : Q) {
        if (C.back() != x) C.push_back(x);
    }
    
    vector<int> P_base;
    vector<bool> visited(N+1, false);
    
    P_base.push_back(C[0]);
    visited[C[0]] = true;
    
    for(size_t i=0; i<C.size()-1; ++i) {
        int u = C[i];
        int v = C[i+1];
        int dir = (u < v) ? 1 : -1;
        for(int k = u + dir; k != v + dir; k += dir) {
            if (!visited[k]) {
                P_base.push_back(k);
                visited[k] = true;
            }
        }
        if (!visited[v]) {
            P_base.push_back(v);
            visited[v] = true;
        }
    }
    
    int m = N+1, M_val = 0;
    for(int x : P_base) {
        if(x < m) m = x;
        if(x > M_val) M_val = x;
    }
    
    vector<int> tailL, tailH;
    for(int k=1; k<m; ++k) tailL.push_back(k);
    for(int k=M_val+1; k<=N; ++k) tailH.push_back(k);
    
    auto insert_vec = [&](vector<int>& dest, int pos, const vector<int>& src) {
        dest.insert(dest.begin() + pos, src.begin(), src.end());
    };
    
    vector<vector<int>> candidates;
    
    if (m != M_val) {
        for(int optL=0; optL<2; ++optL) {
            for(int optH=0; optH<2; ++optH) {
                vector<int> cand = P_base;
                int idx_m = -1, idx_M = -1;
                for(int i=0; i<(int)cand.size(); ++i) {
                    if(cand[i] == m) idx_m = i;
                    if(cand[i] == M_val) idx_M = i;
                }
                
                vector<int> H = tailH;
                if (!H.empty()) {
                    if (optH == 0) { 
                        sort(H.rbegin(), H.rend());
                        if (idx_M > 0) insert_vec(cand, idx_M, H);
                        else goto next_cand; 
                    } else { 
                        sort(H.begin(), H.end());
                        insert_vec(cand, idx_M + 1, H);
                    }
                }
                
                for(int i=0; i<(int)cand.size(); ++i) if(cand[i] == m) idx_m = i;
                
                vector<int> L_vec = tailL;
                if (!L_vec.empty()) {
                    if (optL == 0) { 
                        sort(L_vec.begin(), L_vec.end());
                        if (idx_m > 0) insert_vec(cand, idx_m, L_vec);
                        else goto next_cand;
                    } else { 
                        sort(L_vec.rbegin(), L_vec.rend());
                        insert_vec(cand, idx_m + 1, L_vec);
                    }
                }
                candidates.push_back(cand);
                next_cand:;
            }
        }
    } else { 
        vector<int> L_desc = tailL; sort(L_desc.rbegin(), L_desc.rend());
        vector<int> H_asc = tailH; sort(H_asc.begin(), H_asc.end());
        vector<int> L_asc = tailL; sort(L_asc.begin(), L_asc.end());
        vector<int> H_desc = tailH; sort(H_desc.rbegin(), H_desc.rend());

        if (true) {
            vector<int> cand = P_base;
            cand.insert(cand.end(), L_desc.begin(), L_desc.end());
            cand.insert(cand.end(), H_asc.begin(), H_asc.end());
            candidates.push_back(cand);
        }
        
        if (true) {
            vector<int> cand = P_base;
            cand.insert(cand.end(), H_asc.begin(), H_asc.end());
            cand.insert(cand.end(), L_desc.begin(), L_desc.end());
            candidates.push_back(cand);
        }
    }
    
    long long min_cost = -1;
    vector<Point> best_path;
    
    for(const auto& cand : candidates) {
        vector<Point> path;
        long long c = solve_cost(cand, path, false);
        if (c != -1) {
            if (min_cost == -1 || c < min_cost) {
                min_cost = c;
                best_path.clear();
                solve_cost(cand, best_path, true);
            }
        }
    }
    
    if (min_cost != -1) {
        cout << "YES" << endl;
        cout << best_path.size() << endl;
        for(const auto& p : best_path) {
            cout << p.x << " " << p.y << "\n";
        }
    } else {
        cout << "NO" << endl;
    }
    
    return 0;
}