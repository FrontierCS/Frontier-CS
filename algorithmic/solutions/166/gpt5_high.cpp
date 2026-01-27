#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N;
    if (!(cin >> N)) return 0;
    vector<vector<long long>> h(N, vector<long long>(N));
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) cin >> h[i][j];
    }

    // Build serpentine path
    vector<pair<int,int>> path;
    path.reserve(N*N);
    for (int i = 0; i < N; ++i) {
        if (i % 2 == 0) {
            for (int j = 0; j < N; ++j) path.emplace_back(i, j);
        } else {
            for (int j = N - 1; j >= 0; --j) path.emplace_back(i, j);
        }
    }

    vector<string> ops;
    long long load = 0;

    auto process_cell = [&](int i, int j) {
        long long c = h[i][j];
        if (c > 0) {
            long long d = c;
            if (d > 0) {
                ops.push_back("+" + to_string(d));
                load += d;
                h[i][j] -= d;
            }
        } else if (c < 0) {
            long long need = -c;
            long long d = min(load, need);
            if (d > 0) {
                ops.push_back("-" + to_string(d));
                load -= d;
                h[i][j] += d;
            }
        }
    };

    auto move_step = [&](int ci, int cj, int ni, int nj) {
        if (ni == ci + 1 && nj == cj) ops.push_back("D");
        else if (ni == ci - 1 && nj == cj) ops.push_back("U");
        else if (nj == cj + 1 && ni == ci) ops.push_back("R");
        else if (nj == cj - 1 && ni == ci) ops.push_back("L");
    };

    // First pass along serpentine path
    for (int k = 0; k < (int)path.size(); ++k) {
        int i = path[k].first, j = path[k].second;
        process_cell(i, j);
        if (k + 1 < (int)path.size()) {
            int ni = path[k+1].first, nj = path[k+1].second;
            move_step(i, j, ni, nj);
        }
    }

    // Second pass in reverse to deliver remaining load to negative cells
    if (load > 0) {
        for (int k = (int)path.size() - 1; k >= 0; --k) {
            int i = path[k].first, j = path[k].second;
            process_cell(i, j);
            if (load == 0) break;
            if (k > 0) {
                int pi = path[k-1].first, pj = path[k-1].second;
                move_step(i, j, pi, pj);
            }
        }
    }

    for (const auto& s : ops) {
        cout << s << '\n';
    }
    return 0;
}