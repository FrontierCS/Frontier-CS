#include <bits/stdc++.h>
using namespace std;

struct Cell {
    int i, j, val;
};

int manhattan(int i1, int j1, int i2, int j2) {
    return abs(i1 - i2) + abs(j1 - j2);
}

void generate_moves(int ci, int cj, int ti, int tj, vector<string>& ops) {
    while (ci < ti) { ops.push_back("D"); ci++; }
    while (ci > ti) { ops.push_back("U"); ci--; }
    while (cj < tj) { ops.push_back("R"); cj++; }
    while (cj > tj) { ops.push_back("L"); cj--; }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int N;
    cin >> N;
    vector<vector<int>> h(N, vector<int>(N));
    vector<Cell> pos, neg;
    int total_excess = 0;
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            cin >> h[i][j];
            if (h[i][j] > 0) {
                pos.push_back({i, j, h[i][j]});
                total_excess += h[i][j];
            } else if (h[i][j] < 0) {
                neg.push_back({i, j, -h[i][j]});
            }
        }
    }

    if (pos.empty() && neg.empty()) {
        return 0;
    }

    // Order positives: minimize d * (100 + current_load) * val
    vector<Cell> order_pos;
    int ci = 0, cj = 0;
    int load = 0;
    vector<bool> used_pos(pos.size(), false);
    int remaining = pos.size();
    while (remaining > 0) {
        long long best_score = 1e18;
        int best_idx = -1;
        for (size_t k = 0; k < pos.size(); ++k) {
            if (used_pos[k]) continue;
            int d = manhattan(ci, cj, pos[k].i, pos[k].j);
            long long score = 1LL * d * (100 + load) * pos[k].val;
            if (score < best_score) {
                best_score = score;
                best_idx = k;
            }
        }
        order_pos.push_back(pos[best_idx]);
        used_pos[best_idx] = true;
        ci = pos[best_idx].i;
        cj = pos[best_idx].j;
        load += pos[best_idx].val;
        remaining--;
    }

    // Order negatives: minimize d * (100 + current_load) / val
    vector<Cell> order_neg;
    vector<bool> used_neg(neg.size(), false);
    remaining = neg.size();
    while (remaining > 0) {
        double best_score = 1e18;
        int best_idx = -1;
        for (size_t k = 0; k < neg.size(); ++k) {
            if (used_neg[k]) continue;
            int d = manhattan(ci, cj, neg[k].i, neg[k].j);
            double score = (double)d * (100 + load) / neg[k].val;
            if (score < best_score) {
                best_score = score;
                best_idx = k;
            }
        }
        order_neg.push_back(neg[best_idx]);
        used_neg[best_idx] = true;
        ci = neg[best_idx].i;
        cj = neg[best_idx].j;
        load -= neg[best_idx].val;
        remaining--;
    }

    // Generate operations
    vector<string> ops;
    load = 0;
    ci = 0; cj = 0;

    for (auto& cell : order_pos) {
        if (ci != cell.i || cj != cell.j) {
            generate_moves(ci, cj, cell.i, cell.j, ops);
        }
        ops.push_back("+" + to_string(cell.val));
        load += cell.val;
        ci = cell.i; cj = cell.j;
    }

    for (auto& cell : order_neg) {
        if (ci != cell.i || cj != cell.j) {
            generate_moves(ci, cj, cell.i, cell.j, ops);
        }
        ops.push_back("-" + to_string(cell.val));
        load -= cell.val;
        ci = cell.i; cj = cell.j;
    }

    for (const string& op : ops) {
        cout << op << '\n';
    }

    return 0;
}