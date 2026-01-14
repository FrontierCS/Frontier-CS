#include <iostream>
#include <vector>
#include <string>
#include <numeric>
#include <algorithm>
#include <cmath>

using namespace std;

struct Point {
    int x, y;
};

int n, m, L, R, Sx, Sy, Lq, s;
vector<int> q;

bool is_subsequence(const vector<int>& p, const vector<int>& sub) {
    if (sub.empty()) {
        return true;
    }
    int i = 0, j = 0;
    while (i < p.size() && j < sub.size()) {
        if (p[i] == sub[j]) {
            j++;
        }
        i++;
    }
    return j == sub.size();
}

void add_path(vector<Point>& path, int r1, int c1, int r2, int c2, bool use_spare) {
    if (!use_spare) {
        if (r1 < r2) {
            for (int r = r1 + 1; r <= r2; ++r) path.push_back({r, c1});
        } else {
            for (int r = r1 - 1; r >= r2; --r) path.push_back({r, c1});
        }
        if (c1 < c2) {
            for (int c = c1 + 1; c <= c2; ++c) path.push_back({r2, c});
        } else {
            for (int c = c1 - 1; c >= c2; --c) path.push_back({r2, c});
        }
        return;
    }

    int spare_c = -1;
    if (L > 1) spare_c = 1;
    else if (R < m) spare_c = m;

    if (path.back().y < spare_c) {
        for (int c = path.back().y + 1; c <= spare_c; ++c) path.push_back({path.back().x, c});
    } else {
        for (int c = path.back().y - 1; c >= spare_c; --c) path.push_back({path.back().x, c});
    }

    if (path.back().x < r2) {
        for (int r = path.back().x + 1; r <= r2; ++r) path.push_back({r, path.back().y});
    } else {
        for (int r = path.back().x - 1; r >= r2; --r) path.push_back({r, path.back().y});
    }

    if (path.back().y < c2) {
        for (int c = path.back().y + 1; c <= c2; ++c) path.push_back({path.back().x, c});
    } else {
        for (int c = path.back().y - 1; c >= c2; --c) path.push_back({path.back().x, c});
    }
}


void solve_general() {
    vector<int> p1, p2;
    p1.push_back(Sx);
    for (int i = Sx + 1; i <= n; ++i) p1.push_back(i);
    for (int i = Sx - 1; i >= 1; --i) p1.push_back(i);

    p2.push_back(Sx);
    for (int i = Sx - 1; i >= 1; --i) p2.push_back(i);
    for (int i = Sx + 1; i <= n; ++i) p2.push_back(i);

    vector<vector<int>> candidates;
    if (is_subsequence(p1, q)) candidates.push_back(p1);
    if (is_subsequence(p2, q)) candidates.push_back(p2);
    
    if (candidates.empty()) {
        cout << "NO" << endl;
        return;
    }

    long long min_cost = -1;
    vector<int> best_p;
    vector<bool> best_dirs;

    for (const auto& p : candidates) {
        vector<long long> cost_L(n + 1, -1), cost_R(n + 1, -1);
        vector<int> parent_L(n + 1, 0), parent_R(n + 1, 0); // 0 for prev L, 1 for prev R

        cost_R[0] = 0; // Start at (Sx,L), sweep L->R, exit at (Sx,R)
        
        for (int i = 1; i < n; ++i) {
            int r1 = p[i-1], r2 = p[i];
            
            long long d_LL, d_LR, d_RL, d_RR;

            if (abs(r1 - r2) == 1) {
                d_LL = abs(r1 - r2) + abs(L - L);
                d_LR = abs(r1 - r2) + abs(L - R);
                d_RL = abs(r1 - r2) + abs(R - L);
                d_RR = abs(r1 - r2) + abs(R - R);
            } else {
                long long spare_L = (L > 1) ? 1 : -1;
                long long spare_R = (R < m) ? m : -1;
                
                auto calc_dist = [&](int c_start, int c_end) {
                    long long dist = -1;
                    if (spare_L != -1) {
                        long long current_dist = (long long)abs(c_start - spare_L) + abs(r1-r2) + abs(spare_L - c_end);
                        if (dist == -1 || current_dist < dist) dist = current_dist;
                    }
                    if (spare_R != -1) {
                        long long current_dist = (long long)abs(c_start - spare_R) + abs(r1-r2) + abs(spare_R - c_end);
                        if (dist == -1 || current_dist < dist) dist = current_dist;
                    }
                    return dist;
                };

                d_LL = calc_dist(L, L);
                d_LR = calc_dist(L, R);
                d_RL = calc_dist(R, L);
                d_RR = calc_dist(R, R);
            }
            
            // Calculate cost to end at R for row p[i] (entry L)
            long long path1_R = (cost_L[i-1] != -1 && d_LL != -1) ? cost_L[i-1] + d_LL : -1;
            long long path2_R = (cost_R[i-1] != -1 && d_RL != -1) ? cost_R[i-1] + d_RL : -1;
            if (path1_R != -1 && (path2_R == -1 || path1_R <= path2_R)) {
                cost_R[i] = path1_R;
                parent_R[i] = 0;
            } else if(path2_R != -1) {
                cost_R[i] = path2_R;
                parent_R[i] = 1;
            }

            // Calculate cost to end at L for row p[i] (entry R)
            long long path1_L = (cost_L[i-1] != -1 && d_LR != -1) ? cost_L[i-1] + d_LR : -1;
            long long path2_L = (cost_R[i-1] != -1 && d_RR != -1) ? cost_R[i-1] + d_RR : -1;
            if (path1_L != -1 && (path2_L == -1 || path1_L <= path2_L)) {
                cost_L[i] = path1_L;
                parent_L[i] = 0;
            } else if (path2_L != -1) {
                cost_L[i] = path2_L;
                parent_L[i] = 1;
            }
        }
        
        long long current_cost;
        bool final_exit_is_L;
        if (cost_L[n-1] != -1 && (cost_R[n-1] == -1 || cost_L[n-1] <= cost_R[n-1])) {
            current_cost = cost_L[n-1];
            final_exit_is_L = true;
        } else if (cost_R[n-1] != -1) {
            current_cost = cost_R[n-1];
            final_exit_is_L = false;
        } else {
            continue;
        }
        
        if (min_cost == -1 || current_cost < min_cost) {
            min_cost = current_cost;
            best_p = p;
            best_dirs.assign(n, false); // false for L->R (exit R), true for R->L (exit L)
            
            bool exit_is_L = final_exit_is_L; // at p[n-1]
            best_dirs[n-1] = exit_is_L;
            
            for (int i = n - 2; i >= 0; --i) {
                 if (exit_is_L) {
                    exit_is_L = (parent_L[i+1] == 0);
                } else {
                    exit_is_L = (parent_R[i+1] == 0);
                }
                best_dirs[i] = exit_is_L;
            }
        }
    }

    if (min_cost == -1) {
        cout << "NO" << endl;
        return;
    }

    cout << "YES" << endl;
    vector<Point> path;
    path.push_back({Sx, Sy});

    for (int i = 0; i < n; ++i) {
        int r = best_p[i];
        bool traverse_R_to_L = best_dirs[i];
        
        if (i == 0) { // First row
             if (Sy == L) traverse_R_to_L = false;
             else traverse_R_to_L = true;
        } else {
            int r_prev = best_p[i-1];
            bool prev_exited_L = best_dirs[i-1];
            Point prev_exit = {r_prev, prev_exited_L ? L : R};
            
            bool use_spare = abs(r - r_prev) > 1;
            
            // Re-determine entry side for current row based on minimum path
            Point entry_L = {r, L};
            Point entry_R = {r, R};

            long long cost_to_L, cost_to_R;
            if(use_spare) {
                long long spare_L = (L > 1) ? 1 : -1;
                long long spare_R = (R < m) ? m : -1;
                auto calc_dist = [&](int c_start, int c_end) {
                    long long dist = -1;
                    if(spare_L != -1) {
                        long long d = (long long)abs(c_start-spare_L) + abs(r-r_prev) + abs(spare_L-c_end);
                        if(dist==-1 || d<dist) dist=d;
                    }
                    if(spare_R != -1) {
                        long long d = (long long)abs(c_start-spare_R) + abs(r-r_prev) + abs(spare_R-c_end);
                        if(dist==-1 || d<dist) dist=d;
                    }
                    return dist;
                };
                cost_to_L = calc_dist(prev_exit.y, entry_L.y);
                cost_to_R = calc_dist(prev_exit.y, entry_R.y);
            } else {
                cost_to_L = abs(r-r_prev) + abs(prev_exit.y - entry_L.y);
                cost_to_R = abs(r-r_prev) + abs(prev_exit.y - entry_R.y);
            }
            if (cost_to_L <= cost_to_R) traverse_R_to_L = false; // Enter L
            else traverse_R_to_L = true; // Enter R
        }

        Point entry_pt = {r, traverse_R_to_L ? R : L};
        add_path(path, path.back().x, path.back().y, entry_pt.x, entry_pt.y, abs(path.back().x - entry_pt.x) > 1);
        
        if (!traverse_R_to_L) { // L to R
            for (int c = L + 1; c <= R; ++c) path.push_back({r, c});
        } else { // R to L
            for (int c = R - 1; c >= L; --c) path.push_back({r, c});
        }
    }

    cout << path.size() << endl;
    for (const auto& pt : path) {
        cout << pt.x << " " << pt.y << endl;
    }
}

void solve_full_grid() {
    vector<int> p;
    bool possible = true;
    if (Sx > 1 && Sx < n) {
        possible = false;
    } else if (Sx == 1) {
        for (int i = 1; i <= n; ++i) p.push_back(i);
    } else { // Sx == n
        for (int i = n; i >= 1; --i) p.push_back(i);
    }
    
    if (!possible || !is_subsequence(p, q)) {
        cout << "NO" << endl;
        return;
    }

    cout << "YES" << endl;
    vector<Point> path;
    path.push_back({Sx, Sy});

    bool l_to_r = (Sy == 1);
    
    for (int i = 0; i < n; ++i) {
        int r = p[i];
        if (l_to_r) {
            for (int c = L + 1; c <= R; ++c) path.push_back({r, c});
        } else {
            for (int c = R - 1; c >= L; --c) path.push_back({r, c});
        }
        if (i < n - 1) {
            path.push_back({p[i+1], path.back().y});
        }
        l_to_r = !l_to_r;
    }

    cout << path.size() << endl;
    for (const auto& pt : path) {
        cout << pt.x << " " << pt.y << endl;
    }
}


int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    cin >> n >> m >> L >> R >> Sx >> Sy >> Lq >> s;
    q.resize(Lq);
    for (int i = 0; i < Lq; ++i) {
        cin >> q[i];
    }

    if (L == 1 && R == m) {
        solve_full_grid();
    } else {
        solve_general();
    }

    return 0;
}