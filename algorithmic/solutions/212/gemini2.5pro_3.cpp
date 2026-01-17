#include <iostream>
#include <vector>
#include <string>
#include <numeric>
#include <algorithm>
#include <cmath>
#include <set>

using namespace std;

long long N, M, L, R, SX, SY, LQ, S;
vector<long long> Q;

vector<long long> q_aug;
vector<long long> free_rows;

long long dp[42][42];
int pred[42][42];

vector<pair<long long, long long>> path;

bool is_subsequence(const vector<long long>& p, const vector<long long>& q_seq) {
    if (q_seq.empty()) return true;
    if (p.empty()) return false;
    int i = 0, j = 0;
    while (i < p.size() && j < q_seq.size()) {
        if (p[i] == q_seq[j]) {
            j++;
        }
        i++;
    }
    return j == q_seq.size();
}

void generate_path_coords(const vector<long long>& p, int case_type) {
    if (p.empty()) return;

    if (case_type == 1) { // Both corridors
        path.push_back({p[0], L});
        for (int i = 0; i < N; ++i) {
            long long row = p[i];
            if ((i + 1) % 2 != 0) { // L->R sweep
                for (long long y = L + 1; y <= R; ++y) path.push_back({row, y});
                if (i < N - 1) {
                    long long next_row = p[i + 1];
                    path.push_back({row, R + 1});
                    if (row < next_row) {
                        for (long long x = row + 1; x <= next_row; ++x) path.push_back({x, R + 1});
                    } else {
                        for (long long x = row - 1; x >= next_row; --x) path.push_back({x, R + 1});
                    }
                    path.push_back({next_row, R});
                }
            } else { // R->L sweep
                for (long long y = R - 1; y >= L; --y) path.push_back({row, y});
                if (i < N - 1) {
                    long long next_row = p[i + 1];
                    path.push_back({row, L - 1});
                    if (row < next_row) {
                        for (long long x = row + 1; x <= next_row; ++x) path.push_back({x, L - 1});
                    } else {
                        for (long long x = row - 1; x >= next_row; --x) path.push_back({x, L - 1});
                    }
                    path.push_back({next_row, L});
                }
            }
        }
    } else if (case_type == 2) { // No corridors
        path.push_back({p[0], L});
        long long cur_y = L;
        for (size_t i = 0; i < p.size(); ++i) {
            long long r = p[i];
            if (i > 0) {
                if (abs(p[i] - p[i - 1]) == 1) {
                    path.push_back({r, cur_y});
                } else { // Turn
                    cur_y = (cur_y == L) ? R : L;
                    path.push_back({p[i - 1], cur_y});
                    path.push_back({r, cur_y});
                }
            }
            if (cur_y == L) {
                for (long long y = L + 1; y <= R; ++y) path.push_back({r, y});
                cur_y = R;
            } else {
                for (long long y = R - 1; y >= L; --y) path.push_back({r, y});
                cur_y = L;
            }
        }
    } else { // One corridor
        bool right_blocked = (R == M);
        long long free_col = right_blocked ? L - 1 : R + 1;

        path.push_back({p[0], right_blocked ? R : L});
        
        for (int i = 0; i < N; ++i) {
            long long row = p[i];
            
            if (i % 2 == 0) { // Unconstrained move -> constrained sweep
                if (!right_blocked) for (long long y = L + 1; y <= R; ++y) path.push_back({row, y});
                else for (long long y = R - 1; y >= L; --y) path.push_back({row, y});
                
                if (i < N - 1) {
                    long long next_row = p[i + 1];
                    path.push_back({row, (right_blocked ? L : R)});
                }
            } else { // Constrained move -> unconstrained sweep
                if (!right_blocked) for (long long y = R - 1; y >= L; --y) path.push_back({row, y});
                else for (long long y = L + 1; y <= R; ++y) path.push_back({row, y});

                if (i < N - 1) {
                    long long next_row = p[i+1];
                    path.push_back({row, free_col});
                    if (row < next_row) {
                        for (long long x = row + 1; x <= next_row; ++x) path.push_back({x, free_col});
                    } else {
                        for (long long x = row - 1; x >= next_row; --x) path.push_back({x, free_col});
                    }
                    path.push_back({next_row, right_blocked ? R : L});
                }
            }
        }
    }
}

long long cost_func(long long u, long long v, const vector<long long>& S) {
    if (S.empty()) return abs(u - v);
    long long min_S = S.front();
    long long max_S = S.back();
    long long cost1 = abs(u - min_S) + (max_S - min_S) + abs(max_S - v);
    long long cost2 = abs(u - max_S) + (max_S - min_S) + abs(min_S - v);
    return min(cost1, cost2);
}

long long cost_after(long long u, const vector<long long>& S) {
    if (S.empty()) return 0;
    long long min_S = S.front();
    long long max_S = S.back();
    return min(abs(u - min_S), abs(u - max_S)) + (max_S - min_S);
}

void solve_both_corridors() {
    for (int i = 0; i <= q_aug.size(); ++i) {
        for (int j = 0; j <= free_rows.size(); ++j) {
            dp[i][j] = -1;
        }
    }
    dp[1][0] = 0;

    for (size_t i = 2; i <= q_aug.size(); ++i) {
        for (size_t j = 0; j <= free_rows.size(); ++j) {
            for (size_t p = 0; p <= j; ++p) {
                if (dp[i - 1][p] == -1) continue;
                vector<long long> current_free;
                if (p < j) {
                    current_free.assign(free_rows.begin() + p, free_rows.begin() + j);
                }
                long long current_cost = dp[i - 1][p] + cost_func(q_aug[i - 2], q_aug[i - 1], current_free);
                if (dp[i][j] == -1 || current_cost < dp[i][j]) {
                    dp[i][j] = current_cost;
                    pred[i][j] = p;
                }
            }
        }
    }

    long long min_total_cost = -1;
    int best_j = -1;
    for (size_t j = 0; j <= free_rows.size(); ++j) {
        if (dp[q_aug.size()][j] == -1) continue;
        vector<long long> remaining_free;
        if (j < free_rows.size()) {
            remaining_free.assign(free_rows.begin() + j, free_rows.end());
        }
        long long total_cost = dp[q_aug.size()][j] + cost_after(q_aug.back(), remaining_free);
        if (min_total_cost == -1 || total_cost < min_total_cost) {
            min_total_cost = total_cost;
            best_j = j;
        }
    }

    if (best_j == -1) {
        cout << "NO" << endl;
        return;
    }
    
    vector<long long> p_recon;
    p_recon.push_back(SX);
    
    vector<vector<long long>> partitions(q_aug.size() + 1);
    int current_j = best_j;
    for (int i = q_aug.size(); i >= 2; --i) {
        int p_idx = pred[i][current_j];
        if (p_idx < current_j) {
            partitions[i-1].assign(free_rows.begin() + p_idx, free_rows.begin() + current_j);
        }
        current_j = p_idx;
    }
    if (best_j < free_rows.size()) {
        partitions[q_aug.size()].assign(free_rows.begin() + best_j, free_rows.end());
    }

    long long last_row = SX;
    for (size_t i = 1; i < q_aug.size(); ++i) {
        vector<long long> current_segment = partitions[i];
        long long next_anchor = q_aug[i];
        if (!current_segment.empty()) {
            long long min_s = current_segment.front();
            long long max_s = current_segment.back();
            long long c1 = abs(last_row - min_s) + abs(max_s - min_s) + abs(max_s - next_anchor);
            long long c2 = abs(last_row - max_s) + abs(max_s - min_s) + abs(min_s - next_anchor);
            if (c1 > c2) reverse(current_segment.begin(), current_segment.end());
            for (auto r : current_segment) p_recon.push_back(r);
        }
        p_recon.push_back(next_anchor);
        last_row = next_anchor;
    }

    vector<long long> last_segment = partitions[q_aug.size()];
    if (!last_segment.empty()) {
        long long min_s = last_segment.front();
        long long max_s = last_segment.back();
        if (abs(last_row - min_s) > abs(last_row - max_s)) reverse(last_segment.begin(), last_segment.end());
        for (auto r : last_segment) p_recon.push_back(r);
    }
    
    cout << "YES" << endl;
    generate_path_coords(p_recon, 1);
    cout << path.size() << endl;
    for (const auto& cell : path) {
        cout << cell.first << " " << cell.second << endl;
    }
}

void solve_no_corridors() {
    vector<long long> p1, p2;
    for (long long i = SX; i <= N; ++i) p1.push_back(i);
    for (long long i = N - 1; i >= 1; --i) {
        bool in_p1 = false;
        for(long long val : p1) if(val == i) in_p1=true;
        if(!in_p1) p1.push_back(i);
    }
    
    for (long long i = SX; i >= 1; --i) p2.push_back(i);
    for (long long i = 2; i <= N; ++i) {
        bool in_p2 = false;
        for(long long val : p2) if(val == i) in_p2=true;
        if(!in_p2) p2.push_back(i);
    }
    
    if (!is_subsequence(p1, Q) && !is_subsequence(p2, Q)) {
        cout << "NO" << endl;
    } else {
        cout << "YES" << endl;
        vector<long long> p_final = is_subsequence(p1, Q) ? p1 : p2;
        generate_path_coords(p_final, 2);
        cout << path.size() << endl;
        for (const auto& cell : path) {
            cout << cell.first << " " << cell.second << endl;
        }
    }
}

void solve_one_corridor() {
    bool right_blocked = (R == M);
    long long sx_orig = SX;
    vector<long long> q_orig = Q;

    if (right_blocked) {
        SX = N - SX + 1;
        for (auto& val : Q) val = N - val + 1;
    }

    if (N > 1 && N % 2 == 0) {
        cout << "NO" << endl; return;
    }
    if (SX > 1 && SX < N && SX % 2 == 0) {
        cout << "NO" << endl; return;
    }

    vector<long long> p;
    p.push_back(SX);
    vector<bool> visited(N + 1, false);
    visited[SX] = true;
    
    long long curr = SX;
    while(p.size() < N){
        bool found = false;
        for(long long next : {curr - 1, curr + 1}){
            if(next >= 1 && next <= N && !visited[next]){
                p.push_back(next);
                visited[next] = true;
                found = true;
                break;
            }
        }
        if(!found){
            long long best_next = -1, min_dist = N+1;
            for(long long i=1; i<=N; ++i){
                if(!visited[i] && (i % 2 != (curr % 2)) ){
                   if(abs(i-curr) < min_dist){
                       min_dist = abs(i-curr);
                       best_next = i;
                   }
                }
            }
            if(best_next == -1) {
              for(long long i=1; i<=N; ++i) if(!visited[i]) best_next = i;
            }

            p.push_back(best_next);
            visited[best_next] = true;
            curr = best_next;
        } else {
           curr = p.back();
        }
    }

    if (!is_subsequence(p, Q)) {
       cout << "NO" << endl; return;
    }
    
    if (right_blocked) {
        for (auto& val : p) val = N - val + 1;
    }

    cout << "YES" << endl;
    generate_path_coords(p, 3);
    cout << path.size() << endl;
    for (const auto& cell : path) {
        cout << cell.first << " " << cell.second << endl;
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    cin >> N >> M >> L >> R >> SX >> SY >> LQ >> S;
    Q.resize(LQ);
    set<long long> q_set;
    for (int i = 0; i < LQ; ++i) {
        cin >> Q[i];
        q_set.insert(Q[i]);
    }

    if (q_set.count(SX) && (LQ > 0 && Q[0] != SX)) {
        cout << "NO" << endl;
        return 0;
    }

    if (q_set.count(SX)) {
        q_aug = Q;
    } else {
        q_aug.push_back(SX);
        for (long long val : Q) q_aug.push_back(val);
    }
    
    set<long long> q_aug_set(q_aug.begin(), q_aug.end());
    for (long long i = 1; i <= N; ++i) {
        if (!q_aug_set.count(i)) {
            free_rows.push_back(i);
        }
    }

    if (L > 1 && R < M) {
        solve_both_corridors();
    } else if (L == 1 && R == M) {
        solve_no_corridors();
    } else {
        solve_one_corridor();
    }

    return 0;
}