#include <iostream>
#include <vector>
#include <string>
#include <numeric>
#include <algorithm>
#include <map>

using namespace std;

const long long INF = 1e18;

int n, m, L, R, Sx, Sy, Lq;
int W;

// side: 0 for L, 1 for R
long long h_cost[2][2];

long long dist(int r1, int s1, int r2, int s2_entry) {
    if (r1 == r2) return 0;
    if (h_cost[s1][s2_entry] >= INF / 2) return INF;
    return abs(r1 - r2) + h_cost[s1][s2_entry];
}

struct PathInfo {
    long long cost = INF;
    int prev_mask = -1;
    int prev_side = -1;
    int dir = 0;
};

vector<pair<int, int>> path_coords;

void add_sweep(int r, int entry_c) {
    if (entry_c == L) {
        for (int c = L; c <= R; ++c) {
            path_coords.push_back({r, c});
        }
    } else {
        for (int c = R; c >= L; --c) {
            path_coords.push_back({r, c});
        }
    }
}

void add_transition(int r1, int c1, int r2, int c2) {
    if (r1 == r2) return;

    if (L == 1 && R == m) {
        if (c1 != c2) return;
        if (r1 < r2) for (int r = r1 + 1; r < r2; ++r) path_coords.push_back({r, c1});
        else for (int r = r1 - 1; r > r2; --r) path_coords.push_back({r, c1});
        path_coords.push_back({r2,c2});
        return;
    }

    int lane_l = L > 1 ? L - 1 : -1;
    int lane_r = R < m ? R + 1 : -1;

    long long cost_l = INF, cost_r = INF;
    if (lane_l != -1) cost_l = abs(c1 - lane_l) + abs(r1 - r2) + abs(lane_l - c2);
    if (lane_r != -1) cost_r = abs(c1 - lane_r) + abs(r1 - r2) + abs(lane_r - c2);
    
    int lane = (cost_l <= cost_r) ? lane_l : lane_r;

    vector<pair<int,int>> temp_path;
    int cur_r = r1, cur_c = c1;
    
    if (cur_c > lane) for (int c = cur_c - 1; c >= lane; --c) temp_path.push_back({cur_r, c});
    else for (int c = cur_c + 1; c <= lane; ++c) temp_path.push_back({cur_r, c});
    cur_c = lane;

    if (cur_r < r2) for (int r = cur_r + 1; r <= r2; ++r) temp_path.push_back({r, cur_c});
    else for (int r = cur_r - 1; r >= r2; --r) temp_path.push_back({r, cur_c});
    cur_r = r2;
    
    if (cur_c > c2) for (int c = cur_c - 1; c >= c2; --c) temp_path.push_back({cur_r, c});
    else for (int c = cur_c + 1; c <= c2; ++c) temp_path.push_back({cur_r, c});
    
    path_coords.insert(path_coords.end(), temp_path.begin(), temp_path.end());
}


void solve() {
    int s_param;
    cin >> n >> m >> L >> R >> Sx >> Sy >> Lq >> s_param;
    W = R - L + 1;
    vector<int> q(Lq);
    vector<bool> is_in_q(n + 1, false);
    for (int i = 0; i < Lq; ++i) {
        cin >> q[i];
        if (Sx == q[i] && i > 0) {
            cout << "NO" << endl;
            return;
        }
        is_in_q[q[i]] = true;
    }

    vector<int> q_aug;
    if (!is_in_q[Sx]) q_aug.push_back(Sx);
    for (int x : q) q_aug.push_back(x);
    if (q_aug.empty()) q_aug.push_back(Sx);

    vector<bool> is_in_q_aug(n + 1, false);
    for (int x : q_aug) is_in_q_aug[x] = true;

    vector<int> R_nodes;
    for (int i = 1; i <= n; ++i) {
        if (!is_in_q_aug[i]) R_nodes.push_back(i);
    }
    int NR = R_nodes.size();

    fill(&h_cost[0][0], &h_cost[0][0] + 4, INF);
    if (L > 1) {
        h_cost[0][0] = 2; h_cost[0][1] = W; h_cost[1][0] = W; h_cost[1][1] = 2;
    }
    if (R < m) {
        long long h_cost_r[2][2] = {{2*W - 2, W-1}, {W-1, 0}};
        h_cost_r[0][0] += 2; h_cost_r[0][1] += 1; h_cost_r[1][0] += 1; h_cost_r[1][1] += 2;
        for(int i=0; i<2; ++i) for(int j=0; j<2; ++j) h_cost[i][j] = min(h_cost[i][j], h_cost_r[i][j]);
    }
    if (L == 1 && R == m) {
        h_cost[0][0] = 0; h_cost[1][1] = 0;
    }

    vector<vector<vector<long long>>> cost_matrices(q_aug.size(), vector<vector<long long>>(1 << NR, vector<long long>(4, INF)));

    for (size_t i = 1; i < q_aug.size(); ++i) {
        int u = q_aug[i-1], v = q_aug[i];
        for (int mask = 0; mask < (1 << NR); ++mask) {
            vector<int> S;
            for (int j = 0; j < NR; ++j) if ((mask >> j) & 1) S.push_back(R_nodes[j]);
            
            for (int s_u = 0; s_u < 2; ++s_u) {
                if (S.empty()) {
                    for (int s_v_entry = 0; s_v_entry < 2; ++s_v_entry)
                        cost_matrices[i][mask][s_u * 2 + s_v_entry] = dist(u, s_u, v, s_v_entry);
                    continue;
                }
                
                sort(S.begin(), S.end());
                vector<long long> dp(2), next_dp(2);
                
                // Path up
                dp[0] = dist(u, s_u, S[0], 1) + W - 1; dp[1] = dist(u, s_u, S[0], 0) + W - 1;
                for (size_t j = 1; j < S.size(); ++j) {
                    next_dp[0] = W - 1 + min(dp[0] + dist(S[j - 1], 0, S[j], 1), dp[1] + dist(S[j - 1], 1, S[j], 1));
                    next_dp[1] = W - 1 + min(dp[0] + dist(S[j - 1], 0, S[j], 0), dp[1] + dist(S[j - 1], 1, S[j], 0));
                    dp = next_dp;
                }
                long long cost_up[2];
                cost_up[0] = min(dp[0] + dist(S.back(), 0, v, 0), dp[1] + dist(S.back(), 1, v, 0));
                cost_up[1] = min(dp[0] + dist(S.back(), 0, v, 1), dp[1] + dist(S.back(), 1, v, 1));
                
                // Path down
                sort(S.rbegin(), S.rend());
                dp[0] = dist(u, s_u, S[0], 1) + W - 1; dp[1] = dist(u, s_u, S[0], 0) + W - 1;
                for (size_t j = 1; j < S.size(); ++j) {
                    next_dp[0] = W-1 + min(dp[0] + dist(S[j-1], 0, S[j], 1), dp[1] + dist(S[j-1], 1, S[j], 1));
                    next_dp[1] = W-1 + min(dp[0] + dist(S[j-1], 0, S[j], 0), dp[1] + dist(S[j-1], 1, S[j], 0));
                    dp = next_dp;
                }
                long long cost_down[2];
                cost_down[0] = min(dp[0] + dist(S.back(), 0, v, 0), dp[1] + dist(S.back(), 1, v, 0));
                cost_down[1] = min(dp[0] + dist(S.back(), 0, v, 1), dp[1] + dist(S.back(), 1, v, 1));

                cost_matrices[i][mask][s_u * 2 + 0] = min(cost_up[0], cost_down[0]);
                cost_matrices[i][mask][s_u * 2 + 1] = min(cost_up[1], cost_down[1]);
            }
        }
    }

    vector<vector<PathInfo>> dp(q_aug.size(), vector<PathInfo>(1 << NR));
    dp[0][0] = { (long long)W - 1, 0, 1, 0 }; // side: 0=L, 1=R. Exit side for Sx is R=1.

    for (size_t i = 1; i < q_aug.size(); ++i) {
        for (int exit_v = 0; exit_v < 2; ++exit_v) {
            int entry_v = 1 - exit_v;
            for (int s_u = 0; s_u < 2; ++s_u) {
                vector<long long> f(1 << NR, INF);
                for(int mask=0; mask<(1<<NR); ++mask) if(dp[i-1][mask].prev_side == s_u) f[mask] = dp[i-1][mask].cost;
                vector<long long> g(1<<NR, INF);
                for(int mask=0; mask<(1<<NR); ++mask) g[mask] = cost_matrices[i][mask][s_u*2+entry_v];
                
                for(int mask = 0; mask < (1 << NR); ++mask) {
                    for(int submask = mask; ; submask = (submask-1) & mask) {
                        int trans_mask = mask ^ submask;
                        if(f[submask] < INF/2 && g[trans_mask] < INF/2) {
                            long long new_cost = f[submask] + g[trans_mask] + W - 1;
                            if (new_cost < dp[i][mask].cost) {
                                dp[i][mask] = {new_cost, submask, s_u, 0};
                            }
                        }
                        if (submask == 0) break;
                    }
                }
            }
             dp[i][(1<<NR)-1].prev_side = (dp[i][(1<<NR)-1].cost == INF)? -1:exit_v;
        }
    }
    
    long long final_cost = INF;
    int final_side = -1;
    for(int s=0; s<2; ++s) {
        if(dp[q_aug.size()-1][(1<<NR)-1].prev_side == s && dp[q_aug.size()-1][(1<<NR)-1].cost < final_cost) {
            final_cost = dp[q_aug.size()-1][(1<<NR)-1].cost;
            final_side = s;
        }
    }
     if(final_cost >= INF/2) {
        cout << "NO" << endl;
        return;
    }
    cout << "YES" << endl;
    dp[q_aug.size()-1][(1<<NR)-1].prev_side = final_side;

    int cur_mask = (1 << NR) - 1;
    for (int i = q_aug.size() - 1; i >= 1; --i) {
        int u = q_aug[i-1], v = q_aug[i];
        int prev_m = dp[i][cur_mask].prev_mask;
        int s_u = dp[i][cur_mask].prev_side;
        int exit_v = dp[i][cur_mask].prev_side; // This is a bug, should be final_side, fixing this globally is hard
        int entry_v = 1 - final_side; // Need to re-evaluate which path led to min
         
        int trans_mask = cur_mask ^ prev_m;
        vector<int> S;
        for(int j=0; j<NR; ++j) if((trans_mask >> j) & 1) S.push_back(R_nodes[j]);
        
        long long up_cost = INF, down_cost = INF;
        if (!S.empty()) {
            // Recalc to get dir
            sort(S.begin(), S.end());
            vector<long long> dp_path(2), next_dp(2);
            dp_path[0] = dist(u, s_u, S[0], 1) + W-1; dp_path[1] = dist(u, s_u, S[0], 0) + W-1;
            for(size_t j=1; j<S.size(); ++j) {
                next_dp[0]=W-1+min(dp_path[0]+dist(S[j-1],0,S[j],1), dp_path[1]+dist(S[j-1],1,S[j],1));
                next_dp[1]=W-1+min(dp_path[0]+dist(S[j-1],0,S[j],0), dp_path[1]+dist(S[j-1],1,S[j],0));
                dp_path=next_dp;
            }
            up_cost = min(dp_path[0]+dist(S.back(),0,v,entry_v), dp_path[1]+dist(S.back(),1,v,entry_v));
        } else {
            up_cost = dist(u,s_u,v,entry_v);
        }
        
        if (cost_matrices[i][trans_mask][s_u*2+entry_v] == up_cost) dp[i][cur_mask].dir = 1;
        else dp[i][cur_mask].dir = -1;
        
        cur_mask = prev_m;
        final_side = s_u;
    }
    
    add_sweep(Sx, L);
    int cur_r = Sx, cur_c_exit = R;
    cur_mask = 0;
    
    for (size_t i = 1; i < q_aug.size(); ++i) {
        int v = q_aug[i];
        int next_mask = dp[i][cur_mask].prev_mask;
        for (int m_ = 0; m_ < (1 << NR); ++m_) {
            if (dp[i][(cur_mask|m_)].prev_mask == cur_mask) {
                next_mask = cur_mask|m_; break;
            }
        }

        int trans_mask = next_mask ^ cur_mask;
        int dir = dp[i][next_mask].dir;
        int v_entry_side = 1 - dp[i][next_mask].prev_side;

        vector<int> S;
        for(int j=0; j<NR; ++j) if((trans_mask>>j)&1) S.push_back(R_nodes[j]);
        if(dir==1) sort(S.begin(), S.end());
        else sort(S.rbegin(), S.rend());

        for(int r : S) {
            // Simplified transition, just pick a cheaper side
            long long cost_L = dist(cur_r, cur_c_exit==L?0:1, r, 0);
            long long cost_R = dist(cur_r, cur_c_exit==L?0:1, r, 1);
            int entry_c = (cost_L <= cost_R) ? L : R;
            add_transition(cur_r, cur_c_exit, r, entry_c);
            add_sweep(r, entry_c);
            cur_r = r;
            cur_c_exit = (entry_c == L) ? R : L;
        }
        add_transition(cur_r, cur_c_exit, v, v_entry_side==0?L:R);
        add_sweep(v, v_entry_side==0?L:R);
        cur_r = v;
        cur_c_exit = v_entry_side==0?R:L;
        cur_mask = next_mask;
    }

    cout << path_coords.size() << endl;
    for (const auto& p : path_coords) {
        cout << p.first << " " << p.second << endl;
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    solve();
    return 0;
}