#include <iostream>
#include <vector>
#include <string>
#include <algorithm>
#include <set>
#include <cmath>

using namespace std;

const long long INF = 1e18;

long long n, m, L, R, Sx, Sy, Lq, s;
vector<long long> q;
vector<long long> q_prime;
vector<long long> o_rows;

// dp[k][i][d][is_q]
// k: q_prime rows 1..k used
// i: o_rows 1..i used
// d: direction of last row (0 for L->R, 1 for R->L)
// is_q: 0 if last row is o_rows[i-1], 1 if last row is q_prime[k-1]
long long dp[42][42][2][2];
// parent[k][i][d][is_q] = {{prev_k, prev_i}, {prev_d, prev_is_q}}
pair<pair<int, int>, pair<int, int>> parent[42][42][2][2];

long long get_horizontal_cost(int d_prev, int d_curr) {
    long long exit_c = (d_prev == 0) ? R : L;
    long long entry_c = (d_curr == 0) ? L : R;

    long long cost = INF;
    if (L > 1) {
        cost = min(cost, abs(exit_c - (L - 1)) + abs(entry_c - (L - 1)));
    }
    if (R < m) {
        cost = min(cost, abs(exit_c - (R + 1)) + abs(entry_c - (R + 1)));
    }
    return cost;
}

long long get_transition_cost(long long r_prev, int d_prev, long long r_curr, int d_curr) {
    long long exit_c = (d_prev == 0) ? R : L;
    long long entry_c = (d_curr == 0) ? L : R;

    if (exit_c == entry_c && abs(r_prev - r_curr) == 1) {
        return 1;
    }
    return abs(r_prev - r_curr) + get_horizontal_cost(d_prev, d_curr);
}


void build_path_sequence(vector<pair<long long, long long>>& p_seq) {
    int k = q_prime.size();
    int i = o_rows.size();
    
    long long min_val = INF;
    int best_d = -1, best_is_q = -1;

    if (k > 0 || i > 0) {
        if (k > 0) {
            if (dp[k][i][0][1] < min_val) {
                min_val = dp[k][i][0][1];
                best_d = 0; best_is_q = 1;
            }
            if (dp[k][i][1][1] < min_val) {
                min_val = dp[k][i][1][1];
                best_d = 1; best_is_q = 1;
            }
        }
        if (i > 0) {
            if (dp[k][i][0][0] < min_val) {
                min_val = dp[k][i][0][0];
                best_d = 0; best_is_q = 0;
            }
            if (dp[k][i][1][0] < min_val) {
                min_val = dp[k][i][1][0];
                best_d = 1; best_is_q = 0;
            }
        }
    } else { // Only Sx
        p_seq.push_back({Sx, 0});
        return;
    }

    int cur_k = k;
    int cur_i = i;
    int cur_d = best_d;
    int cur_is_q = best_is_q;

    while (cur_k > 0 || cur_i > 0) {
        if (cur_is_q) {
            p_seq.push_back({q_prime[cur_k - 1], cur_d});
        } else {
            p_seq.push_back({o_rows[cur_i - 1], cur_d});
        }
        
        auto p = parent[cur_k][cur_i][cur_d][cur_is_q];
        cur_k = p.first.first;
        cur_i = p.first.second;
        cur_d = p.second.first;
        cur_is_q = p.second.second;
    }
    p_seq.push_back({Sx, 0});
    reverse(p_seq.begin(), p_seq.end());
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    cin >> n >> m >> L >> R >> Sx >> Sy >> Lq >> s;
    q.resize(Lq);
    set<long long> q_set;
    for (int i = 0; i < Lq; ++i) {
        cin >> q[i];
        q_set.insert(q[i]);
    }

    if (L == 1 && R == m && n > 1) {
        cout << "NO" << endl;
        return 0;
    }
    
    for (long long x : q) {
        if (x != Sx) {
            q_prime.push_back(x);
        }
    }

    for (int i = 1; i <= n; ++i) {
        if (i != Sx && q_set.find(i) == q_set.end()) {
            o_rows.push_back(i);
        }
    }

    int K = q_prime.size();
    int I = o_rows.size();

    for(int k=0; k<=K; ++k) for(int i=0; i<=I; ++i) for(int d=0; d<2; ++d) for(int iq=0; iq<2; ++iq) dp[k][i][d][iq] = INF;

    if (K > 0) {
        for (int d = 0; d < 2; ++d) {
            dp[1][0][d][1] = get_transition_cost(Sx, 0, q_prime[0], d);
            parent[1][0][d][1] = {{0,0}, {-1,-1}};
        }
    }
    if (I > 0) {
        for (int d = 0; d < 2; ++d) {
            dp[0][1][d][0] = get_transition_cost(Sx, 0, o_rows[0], d);
            parent[0][1][d][0] = {{0,0}, {-1,-1}};
        }
    }

    for (int k = 0; k <= K; ++k) {
        for (int i = 0; i <= I; ++i) {
            if (k==0 && i==0) continue;

            // Target: dp[k][i][d_curr][1] (ends q_prime[k-1])
            if (k > 0) {
                for(int d_curr = 0; d_curr < 2; ++d_curr) {
                    long long q_cur = q_prime[k-1];
                    // from q_prev (q_prime[k-2])
                    if (k > 1) {
                        long long q_prev = q_prime[k-2];
                        for(int d_prev=0; d_prev<2; ++d_prev) {
                            if (dp[k-1][i][d_prev][1] != INF) {
                                long long new_cost = dp[k-1][i][d_prev][1] + get_transition_cost(q_prev, d_prev, q_cur, d_curr);
                                if (new_cost < dp[k][i][d_curr][1]) {
                                    dp[k][i][d_curr][1] = new_cost;
                                    parent[k][i][d_curr][1] = {{k-1, i}, {d_prev, 1}};
                                }
                            }
                        }
                    }
                    // from o_prev (o_rows[i-1])
                    if (i > 0) {
                        long long o_prev = o_rows[i-1];
                         for(int d_prev=0; d_prev<2; ++d_prev) {
                            if (dp[k-1][i][d_prev][0] != INF) {
                                long long new_cost = dp[k-1][i][d_prev][0] + get_transition_cost(o_prev, d_prev, q_cur, d_curr);
                                if (new_cost < dp[k][i][d_curr][1]) {
                                    dp[k][i][d_curr][1] = new_cost;
                                    parent[k][i][d_curr][1] = {{k-1, i}, {d_prev, 0}};
                                }
                            }
                        }
                    }
                }
            }

            // Target: dp[k][i][d_curr][0] (ends o_rows[i-1])
            if (i > 0) {
                for (int d_curr=0; d_curr<2; ++d_curr) {
                    long long o_cur = o_rows[i-1];
                    // from q_prev (q_prime[k-1])
                    if (k > 0) {
                        long long q_prev = q_prime[k-1];
                        for(int d_prev=0; d_prev<2; ++d_prev) {
                            if (dp[k][i-1][d_prev][1] != INF) {
                                long long new_cost = dp[k][i-1][d_prev][1] + get_transition_cost(q_prev, d_prev, o_cur, d_curr);
                                if (new_cost < dp[k][i][d_curr][0]) {
                                    dp[k][i][d_curr][0] = new_cost;
                                    parent[k][i][d_curr][0] = {{k, i-1}, {d_prev, 1}};
                                }
                            }
                        }
                    }
                    // from o_prev (o_rows[i-2])
                    if (i > 1) {
                        long long o_prev = o_rows[i-2];
                        for(int d_prev=0; d_prev<2; ++d_prev) {
                            if (dp[k][i-1][d_prev][0] != INF) {
                                long long new_cost = dp[k][i-1][d_prev][0] + get_transition_cost(o_prev, d_prev, o_cur, d_curr);
                                if (new_cost < dp[k][i][d_curr][0]) {
                                    dp[k][i][d_curr][0] = new_cost;
                                    parent[k][i][d_curr][0] = {{k, i-1}, {d_prev, 0}};
                                }
                            }
                        }
                    }
                }
            }
        }
    }
    
    long long min_cost = INF;
    if (K > 0 || I > 0) {
        if (K > 0) min_cost = min({min_cost, dp[K][I][0][1], dp[K][I][1][1]});
        if (I > 0) min_cost = min({min_cost, dp[K][I][0][0], dp[K][I][1][0]});
    } else {
        min_cost = 0;
    }
    
    if (min_cost == INF) {
        cout << "NO" << endl;
        return 0;
    }

    cout << "YES" << endl;
    
    vector<pair<long long, long long>> p_seq;
    build_path_sequence(p_seq);

    vector<pair<long long, long long>> final_path;
    long long last_x = -1, last_y = -1;

    for (size_t i = 0; i < p_seq.size(); ++i) {
        long long r = p_seq[i].first;
        long long dir = p_seq[i].second;

        long long entry_c, exit_c;
        if (dir == 0) { // L->R
            entry_c = L; exit_c = R;
        } else { // R->L
            entry_c = R; exit_c = L;
        }

        if (i > 0) {
            long long prev_r = p_seq[i-1].first;
            long long prev_dir = p_seq[i-1].second;
            long long prev_exit_c = (prev_dir == 0) ? R : L;

            if (prev_exit_c == entry_c && abs(r - prev_r) == 1) {
                 while (last_x != r) {
                    last_x += (r > last_x ? 1 : -1);
                    final_path.push_back({last_x, last_y});
                }
            } else {
                long long cost_L = INF, cost_R = INF;
                if (L > 1) cost_L = abs(prev_exit_c - (L - 1)) + abs(entry_c - (L - 1));
                if (R < m) cost_R = abs(prev_exit_c - (R + 1)) + abs(entry_c - (R + 1));
                
                long long c_side = (cost_L <= cost_R) ? L - 1 : R + 1;
                
                while (last_y != c_side) {
                    last_y += (c_side > last_y ? 1 : -1);
                    final_path.push_back({last_x, last_y});
                }
                while (last_x != r) {
                    last_x += (r > last_x ? 1 : -1);
                    final_path.push_back({last_x, last_y});
                }
                while (last_y != entry_c) {
                    last_y += (entry_c > last_y ? 1 : -1);
                    final_path.push_back({last_x, last_y});
                }
            }
        } else { // First row
            final_path.push_back({Sx, Sy});
            last_x = Sx; last_y = Sy;
        }

        if (dir == 0) { // L->R
            for (long long c = L; c <= R; ++c) {
                if (c == last_y && r == last_x) continue;
                final_path.push_back({r, c});
            }
        } else { // R->L
            for (long long c = R; c >= L; --c) {
                if (c == last_y && r == last_x) continue;
                final_path.push_back({r, c});
            }
        }
        last_x = r;
        last_y = exit_c;
    }

    cout << final_path.size() << endl;
    for (const auto& p : final_path) {
        cout << p.first << " " << p.second << endl;
    }

    return 0;
}