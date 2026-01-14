#include <iostream>
#include <vector>
#include <string>
#include <numeric>
#include <algorithm>
#include <set>

using namespace std;

long long n, m, L, R, sx, sy, lq, s;
vector<long long> q;

vector<long long> Q_seq;
vector<long long> O_seq;

long long cost_seg(long long u, long long v, const vector<long long>& seg) {
    if (seg.empty()) {
        return abs(u - v);
    }
    long long min_r = seg.front();
    long long max_r = seg.back();
    long long path1 = abs(u - min_r) + abs(v - max_r);
    long long path2 = abs(u - max_r) + abs(v - min_r);
    return (max_r - min_r) + min(path1, path2);
}

long long cost_last_seg(long long u, const vector<long long>& seg) {
    if (seg.empty()) {
        return 0;
    }
    long long min_r = seg.front();
    long long max_r = seg.back();
    return (max_r - min_r) + min(abs(u - min_r), abs(u - max_r));
}

void generate_path(const vector<long long>& p) {
    vector<pair<long long, long long>> path;
    path.reserve(n * m + 2 * n);

    path.push_back({sx, sy});

    for (int i = 0; i < p.size(); ++i) {
        long long curr_row = p[i];
        if ((i + 1) % 2 != 0) { // Odd step, L->R
            for (long long col = L + 1; col <= R; ++col) path.push_back({curr_row, col});
            if (i + 1 < p.size()) {
                long long next_row = p[i+1];
                long long conn_col = (R < m) ? R + 1 : m;
                if (R < m) path.push_back({curr_row, conn_col});
                if (curr_row < next_row) {
                    for (long long r = curr_row + 1; r < next_row; ++r) path.push_back({r, conn_col});
                } else {
                    for (long long r = curr_row - 1; r > next_row; --r) path.push_back({r, conn_col});
                }
                path.push_back({next_row, conn_col});
                if (R < m) path.push_back({next_row, R});
            }
        } else { // Even step, R->L
            for (long long col = R - 1; col >= L; --col) path.push_back({curr_row, col});
            if (i + 1 < p.size()) {
                long long next_row = p[i+1];
                long long conn_col = (L > 1) ? L - 1 : 1;
                if (L > 1) path.push_back({curr_row, conn_col});
                if (curr_row < next_row) {
                    for (long long r = curr_row + 1; r < next_row; ++r) path.push_back({r, conn_col});
                } else {
                    for (long long r = curr_row - 1; r > next_row; --r) path.push_back({r, conn_col});
                }
                path.push_back({next_row, conn_col});
                if (L > 1) path.push_back({next_row, L});
            }
        }
    }
    cout << path.size() << "\n";
    for (const auto& point : path) {
        cout << point.first << " " << point.second << "\n";
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    cin >> n >> m >> L >> R >> sx >> sy >> lq >> s;
    q.resize(lq);
    long long sx_pos_in_q = -1;
    for (int i = 0; i < lq; ++i) {
        cin >> q[i];
        if (q[i] == sx) {
            sx_pos_in_q = i;
        }
    }

    if (sx_pos_in_q > 0) {
        cout << "NO" << endl;
        return 0;
    }

    if (sx_pos_in_q == -1) {
        Q_seq.push_back(sx);
    }
    for (long long val : q) {
        Q_seq.push_back(val);
    }

    set<long long> Q_set(Q_seq.begin(), Q_seq.end());
    for (long long i = 1; i <= n; ++i) {
        if (Q_set.find(i) == Q_set.end()) {
            O_seq.push_back(i);
        }
    }
    
    long long L_Q = Q_seq.size();
    long long K = O_seq.size();

    if (L_Q == 0) { // Should only happen if n=0, not possible by constraints
         cout << "NO" << endl;
         return 0;
    }

    if (L_Q == 1) {
        vector<long long> p;
        p.push_back(Q_seq[0]);
        vector<long long> seg = O_seq;
        if (!seg.empty()) {
            long long u = Q_seq[0];
            long long min_r = seg.front();
            long long max_r = seg.back();
            if (abs(u - min_r) <= abs(u - max_r)) {
                for (long long val : seg) p.push_back(val);
            } else {
                for (int i = seg.size() - 1; i >= 0; --i) p.push_back(seg[i]);
            }
        }
        cout << "YES" << endl;
        generate_path(p);
        return 0;
    }

    vector<vector<long long>> dp(L_Q, vector<long long>(K + 1, -1));
    vector<vector<int>> parent(L_Q, vector<int>(K + 1, 0));

    for (int j = 0; j <= K; ++j) {
        vector<long long> seg;
        if (j > 0) seg.assign(O_seq.begin(), O_seq.begin() + j);
        dp[0][j] = cost_seg(Q_seq[0], Q_seq[1], seg);
        parent[0][j] = j;
    }

    for (int i = 1; i < L_Q - 1; ++i) {
        for (int j = 0; j <= K; ++j) {
            for (int k = 0; k <= j; ++k) {
                vector<long long> seg;
                if (k > 0) seg.assign(O_seq.begin() + (j - k), O_seq.begin() + j);
                long long current_cost = dp[i-1][j-k] + cost_seg(Q_seq[i], Q_seq[i+1], seg);
                if (dp[i][j] == -1 || current_cost < dp[i][j]) {
                    dp[i][j] = current_cost;
                    parent[i][j] = k;
                }
            }
        }
    }
    
    long long min_total_cost = -1;
    int best_j = -1;

    for (int j = 0; j <= K; ++j) {
        vector<long long> seg;
        if (K - j > 0) seg.assign(O_seq.begin() + j, O_seq.end());
        long long current_total_cost = dp[L_Q - 2][j] + cost_last_seg(Q_seq[L_Q - 1], seg);
        if (min_total_cost == -1 || current_total_cost < min_total_cost) {
            min_total_cost = current_total_cost;
            best_j = j;
        }
    }
    
    cout << "YES" << endl;

    vector<vector<long long>> partitions(L_Q);
    int current_j = best_j;

    vector<long long> last_seg;
    if (K - current_j > 0) last_seg.assign(O_seq.begin() + current_j, O_seq.end());
    partitions[L_Q - 1] = last_seg;

    for (int i = L_Q - 2; i >= 0; --i) {
        int k = parent[i][current_j];
        vector<long long> seg;
        if (k > 0) seg.assign(O_seq.begin() + (current_j - k), O_seq.begin() + current_j);
        partitions[i] = seg;
        current_j -= k;
    }

    vector<long long> p;
    p.push_back(Q_seq[0]);

    for (int i = 0; i < L_Q; ++i) {
        vector<long long> seg = partitions[i];
        if (!seg.empty()) {
            long long u = p.back();
            long long v = (i + 1 < L_Q) ? Q_seq[i+1] : -1;
            long long min_r = seg.front();
            long long max_r = seg.back();
            
            bool go_up = true;
            if (v != -1) {
                if (abs(u - max_r) + abs(v - min_r) < abs(u - min_r) + abs(v - max_r)) {
                    go_up = false;
                }
            } else {
                if (abs(u - max_r) < abs(u - min_r)) {
                    go_up = false;
                }
            }

            if (go_up) {
                for (long long val : seg) p.push_back(val);
            } else {
                for (int k = seg.size() - 1; k >= 0; --k) p.push_back(seg[k]);
            }
        }
        if (i + 1 < L_Q) {
            p.push_back(Q_seq[i+1]);
        }
    }

    generate_path(p);

    return 0;
}