#include <bits/stdc++.h>
using namespace std;

using pii = pair<int,int>;

vector<pii> gen_row_snake(int N) {
    vector<pii> path;
    path.reserve(N*N);
    for (int i = 0; i < N; i++) {
        if (i % 2 == 0) {
            for (int j = 0; j < N; j++) path.emplace_back(i, j);
        } else {
            for (int j = N-1; j >= 0; j--) path.emplace_back(i, j);
        }
    }
    return path;
}

vector<pii> gen_col_snake(int N) {
    vector<pii> path;
    path.reserve(N*N);
    for (int j = 0; j < N; j++) {
        if (j % 2 == 0) {
            for (int i = 0; i < N; i++) path.emplace_back(i, j);
        } else {
            for (int i = N-1; i >= 0; i--) path.emplace_back(i, j);
        }
    }
    return path;
}

long long evaluate_path(const vector<vector<int>>& H, const vector<pii>& path) {
    int N = H.size();
    int M = N * N;
    vector<int> arr(M);
    for (int idx = 0; idx < M; idx++) {
        arr[idx] = H[path[idx].first][path[idx].second];
    }
    long long cargo = 0;
    long long csum = 0;
    for (int i = 0; i < M; i++) {
        if (arr[i] > 0) {
            cargo += arr[i];
            arr[i] = 0;
        } else if (arr[i] < 0) {
            long long d = min(cargo, (long long)(-arr[i]));
            cargo -= d;
            arr[i] += (int)d;
        }
        if (i < M - 1) csum += cargo;
    }
    for (int i = M - 1; i >= 0; i--) {
        if (arr[i] < 0) {
            long long d = -arr[i];
            cargo -= d;
            arr[i] = 0;
        }
        if (i > 0) csum += cargo;
    }
    return csum;
}

void move_step(vector<string>& ops, int &ci, int &cj, int ni, int nj) {
    if (ni == ci + 1 && nj == cj) { ops.emplace_back("D"); ci++; return; }
    if (ni == ci - 1 && nj == cj) { ops.emplace_back("U"); ci--; return; }
    if (nj == cj + 1 && ni == ci) { ops.emplace_back("R"); cj++; return; }
    if (nj == cj - 1 && ni == ci) { ops.emplace_back("L"); cj--; return; }
    // For repositioning, may be multiple steps; handle Manhattan path
    while (ci < ni) { ops.emplace_back("D"); ci++; }
    while (ci > ni) { ops.emplace_back("U"); ci--; }
    while (cj < nj) { ops.emplace_back("R"); cj++; }
    while (cj > nj) { ops.emplace_back("L"); cj--; }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int N;
    if (!(cin >> N)) return 0;
    vector<vector<int>> H(N, vector<int>(N));
    for (int i = 0; i < N; i++) for (int j = 0; j < N; j++) cin >> H[i][j];

    vector<vector<pii>> candidates;
    auto prow = gen_row_snake(N);
    auto prow_rev = prow; reverse(prow_rev.begin(), prow_rev.end());
    auto pcol = gen_col_snake(N);
    auto pcol_rev = pcol; reverse(pcol_rev.begin(), pcol_rev.end());
    candidates.push_back(prow);
    candidates.push_back(prow_rev);
    candidates.push_back(pcol);
    candidates.push_back(pcol_rev);

    long long best_metric = LLONG_MAX;
    int best_idx = 0;
    for (int k = 0; k < (int)candidates.size(); k++) {
        const auto& p = candidates[k];
        long long csum = evaluate_path(H, p);
        long long R = abs(p[0].first - 0) + abs(p[0].second - 0);
        long long metric = csum + 100LL * R;
        if (metric < best_metric) {
            best_metric = metric;
            best_idx = k;
        }
    }

    const auto& P = candidates[best_idx];
    int M = N * N;

    vector<string> ops;
    ops.reserve(5000);

    // Reposition from (0,0) to P[0] with empty cargo
    int ci = 0, cj = 0;
    move_step(ops, ci, cj, P[0].first, P[0].second);

    vector<vector<int>> A = H;
    long long cargo = 0;

    // Forward pass
    for (int t = 0; t < M; t++) {
        int r = P[t].first, c = P[t].second;
        int val = A[r][c];
        if (val > 0) {
            cargo += val;
            ops.emplace_back("+" + to_string(val));
            A[r][c] = 0;
        } else if (val < 0) {
            long long d = min(cargo, (long long)(-val));
            if (d > 0) {
                cargo -= d;
                ops.emplace_back("-" + to_string(d));
                A[r][c] += (int)d;
            }
        }
        if (t < M - 1) {
            move_step(ops, ci, cj, P[t+1].first, P[t+1].second);
        }
    }

    // Backward pass
    for (int t = M - 1; t >= 0; t--) {
        int r = P[t].first, c = P[t].second;
        int val = A[r][c];
        if (val < 0) {
            long long d = -val;
            cargo -= d;
            ops.emplace_back("-" + to_string(d));
            A[r][c] = 0;
        }
        if (t > 0) {
            move_step(ops, ci, cj, P[t-1].first, P[t-1].second);
        }
    }

    // Output operations
    for (auto &s : ops) cout << s << '\n';
    return 0;
}