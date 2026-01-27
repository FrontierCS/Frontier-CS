#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int N;
    if (!(cin >> N)) return 0;
    vector<string> C(N);
    for (int i = 0; i < N; i++) cin >> C[i];

    vector<vector<bool>> hasF(N, vector<bool>(N, false));
    vector<vector<bool>> remX(N, vector<bool>(N, false));
    vector<pair<int,int>> onis;
    for (int i = 0; i < N; i++) {
        for (int j = 0; j < N; j++) {
            if (C[i][j] == 'o') hasF[i][j] = true;
            if (C[i][j] == 'x') {
                remX[i][j] = true;
                onis.emplace_back(i, j);
            }
        }
    }

    auto allowedUp = [&](int i, int j) {
        for (int r = 0; r < i; r++) if (hasF[r][j]) return false;
        return true;
    };
    auto allowedDown = [&](int i, int j) {
        for (int r = i + 1; r < N; r++) if (hasF[r][j]) return false;
        return true;
    };
    auto allowedLeft = [&](int i, int j) {
        for (int c = 0; c < j; c++) if (hasF[i][c]) return false;
        return true;
    };
    auto allowedRight = [&](int i, int j) {
        for (int c = j + 1; c < N; c++) if (hasF[i][c]) return false;
        return true;
    };

    vector<pair<char,int>> ops;
    int remaining = 0;
    for (auto &p : onis) if (remX[p.first][p.second]) remaining++;

    while (remaining > 0) {
        // best candidate: maximize benefit/distance ratio, tie-break by smaller distance, then arbitrary
        bool found = false;
        int bi = -1, bj = -1, bdir = -1; // dir: 0=U,1=D,2=L,3=R
        int b_dist = 1, b_benefit = 0;

        for (auto &p : onis) {
            int i = p.first, j = p.second;
            if (!remX[i][j]) continue;

            // Up
            if (allowedUp(i, j)) {
                int d = i + 1;
                int b = 0;
                for (int r = 0; r <= i; r++) if (remX[r][j]) b++;
                if (!found || (long long)b * b_dist > (long long)b_benefit * d || ((long long)b * b_dist == (long long)b_benefit * d && d < b_dist)) {
                    found = true; bi = i; bj = j; bdir = 0; b_dist = d; b_benefit = b;
                }
            }
            // Down
            if (allowedDown(i, j)) {
                int d = N - i;
                int b = 0;
                for (int r = i; r < N; r++) if (remX[r][j]) b++;
                if (!found || (long long)b * b_dist > (long long)b_benefit * d || ((long long)b * b_dist == (long long)b_benefit * d && d < b_dist)) {
                    found = true; bi = i; bj = j; bdir = 1; b_dist = d; b_benefit = b;
                }
            }
            // Left
            if (allowedLeft(i, j)) {
                int d = j + 1;
                int b = 0;
                for (int c = 0; c <= j; c++) if (remX[i][c]) b++;
                if (!found || (long long)b * b_dist > (long long)b_benefit * d || ((long long)b * b_dist == (long long)b_benefit * d && d < b_dist)) {
                    found = true; bi = i; bj = j; bdir = 2; b_dist = d; b_benefit = b;
                }
            }
            // Right
            if (allowedRight(i, j)) {
                int d = N - j;
                int b = 0;
                for (int c = j; c < N; c++) if (remX[i][c]) b++;
                if (!found || (long long)b * b_dist > (long long)b_benefit * d || ((long long)b * b_dist == (long long)b_benefit * d && d < b_dist)) {
                    found = true; bi = i; bj = j; bdir = 3; b_dist = d; b_benefit = b;
                }
            }
        }

        if (!found) break; // should not happen due to problem guarantee

        // Apply operation: push moves and update remaining onis
        if (bdir == 0) { // Up on column bj, d = bi+1
            for (int k = 0; k < b_dist; k++) ops.push_back({'U', bj});
            for (int k = 0; k < b_dist; k++) ops.push_back({'D', bj});
            for (int r = 0; r <= bi; r++) {
                if (remX[r][bj]) { remX[r][bj] = false; remaining--; }
            }
        } else if (bdir == 1) { // Down on column bj, d = N-bi
            for (int k = 0; k < b_dist; k++) ops.push_back({'D', bj});
            for (int k = 0; k < b_dist; k++) ops.push_back({'U', bj});
            for (int r = bi; r < N; r++) {
                if (remX[r][bj]) { remX[r][bj] = false; remaining--; }
            }
        } else if (bdir == 2) { // Left on row bi, d = bj+1
            for (int k = 0; k < b_dist; k++) ops.push_back({'L', bi});
            for (int k = 0; k < b_dist; k++) ops.push_back({'R', bi});
            for (int c = 0; c <= bj; c++) {
                if (remX[bi][c]) { remX[bi][c] = false; remaining--; }
            }
        } else { // Right on row bi, d = N-bj
            for (int k = 0; k < b_dist; k++) ops.push_back({'R', bi});
            for (int k = 0; k < b_dist; k++) ops.push_back({'L', bi});
            for (int c = bj; c < N; c++) {
                if (remX[bi][c]) { remX[bi][c] = false; remaining--; }
            }
        }

        if ((int)ops.size() > 4 * N * N) break; // safety
    }

    // Output operations
    for (auto &op : ops) {
        cout << op.first << ' ' << op.second << '\n';
    }
    return 0;
}