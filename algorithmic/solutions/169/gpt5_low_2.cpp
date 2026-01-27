#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int N;
    if (!(cin >> N)) return 0;
    vector<string> C(N);
    for (int i = 0; i < N; ++i) cin >> C[i];

    vector<vector<int>> oni(N, vector<int>(N, 0)), fuku(N, vector<int>(N, 0));
    int oniCount = 0;
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            if (C[i][j] == 'x') { oni[i][j] = 1; oniCount++; }
            else if (C[i][j] == 'o') fuku[i][j] = 1;
        }
    }

    // Prefix sums of Fukunokami for quick queries
    vector<vector<int>> rowPref(N, vector<int>(N+1, 0)), colPref(N, vector<int>(N+1, 0));
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j)
            rowPref[i][j+1] = rowPref[i][j] + fuku[i][j];
    }
    for (int j = 0; j < N; ++j) {
        for (int i = 0; i < N; ++i)
            colPref[j][i+1] = colPref[j][i] + fuku[i][j];
    }

    auto clearUp = [&](int i, int j){ return colPref[j][i] - colPref[j][0] == 0; }; // rows [0, i-1]
    auto clearDown = [&](int i, int j){ return colPref[j][N] - colPref[j][i+1] == 0; }; // rows [i+1, N-1]
    auto clearLeft = [&](int i, int j){ return rowPref[i][j] - rowPref[i][0] == 0; }; // cols [0, j-1]
    auto clearRight = [&](int i, int j){ return rowPref[i][N] - rowPref[i][j+1] == 0; }; // cols [j+1, N-1]

    struct Move { char d; int p; };
    vector<Move> ops;
    const int Tlimit = 4 * N * N;

    while (oniCount > 0) {
        int best_i = -1, best_j = -1;
        char best_dir = '?';
        int best_k = INT_MAX;
        int best_remove = -1;

        for (int i = 0; i < N; ++i) {
            for (int j = 0; j < N; ++j) if (oni[i][j]) {
                // consider directions
                struct Cand { char dir; int k; int rem; };
                vector<Cand> cand;
                if (clearUp(i,j)) {
                    int k = i + 1;
                    int rem = 0;
                    for (int r = 0; r <= i; ++r) if (oni[r][j]) rem++;
                    cand.push_back({'U', k, rem});
                }
                if (clearDown(i,j)) {
                    int k = N - i;
                    int rem = 0;
                    for (int r = i; r < N; ++r) if (oni[r][j]) rem++;
                    cand.push_back({'D', k, rem});
                }
                if (clearLeft(i,j)) {
                    int k = j + 1;
                    int rem = 0;
                    for (int c = 0; c <= j; ++c) if (oni[i][c]) rem++;
                    cand.push_back({'L', k, rem});
                }
                if (clearRight(i,j)) {
                    int k = N - j;
                    int rem = 0;
                    for (int c = j; c < N; ++c) if (oni[i][c]) rem++;
                    cand.push_back({'R', k, rem});
                }
                if (cand.empty()) continue; // should not happen due to guarantee

                // choose minimal k, tie by larger rem
                Cand best = cand[0];
                for (auto &x : cand) {
                    if (x.k < best.k || (x.k == best.k && x.rem > best.rem)) best = x;
                }

                if (best.k < best_k || (best.k == best_k && best.rem > best_remove)) {
                    best_k = best.k;
                    best_dir = best.dir;
                    best_i = i;
                    best_j = j;
                    best_remove = best.rem;
                }
            }
        }

        if (best_i == -1) break; // no moves possible (shouldn't happen)

        int i = best_i, j = best_j, k = best_k;
        if ((int)ops.size() + 2*k > Tlimit) break; // safety

        if (best_dir == 'U') {
            for (int t = 0; t < k; ++t) ops.push_back({'U', j});
            for (int t = 0; t < k; ++t) ops.push_back({'D', j});
            for (int r = 0; r <= i; ++r) if (oni[r][j]) { oni[r][j] = 0; oniCount--; }
        } else if (best_dir == 'D') {
            for (int t = 0; t < k; ++t) ops.push_back({'D', j});
            for (int t = 0; t < k; ++t) ops.push_back({'U', j});
            for (int r = i; r < N; ++r) if (oni[r][j]) { oni[r][j] = 0; oniCount--; }
        } else if (best_dir == 'L') {
            for (int t = 0; t < k; ++t) ops.push_back({'L', i});
            for (int t = 0; t < k; ++t) ops.push_back({'R', i});
            for (int c = 0; c <= j; ++c) if (oni[i][c]) { oni[i][c] = 0; oniCount--; }
        } else if (best_dir == 'R') {
            for (int t = 0; t < k; ++t) ops.push_back({'R', i});
            for (int t = 0; t < k; ++t) ops.push_back({'L', i});
            for (int c = j; c < N; ++c) if (oni[i][c]) { oni[i][c] = 0; oniCount--; }
        }
    }

    // Output operations
    for (auto &m : ops) {
        cout << m.d << ' ' << m.p << '\n';
    }
    return 0;
}