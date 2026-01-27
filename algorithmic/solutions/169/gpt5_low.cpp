#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int N;
    if(!(cin >> N)) return 0;
    vector<string> C(N);
    for (int i = 0; i < N; ++i) cin >> C[i];

    struct Move { char d; int p; };
    vector<Move> ops;

    auto clear_up = [&](int i, int j)->bool{
        for (int r = 0; r < i; ++r) if (C[r][j] == 'o') return false;
        return true;
    };
    auto clear_down = [&](int i, int j)->bool{
        for (int r = i + 1; r < N; ++r) if (C[r][j] == 'o') return false;
        return true;
    };
    auto clear_left = [&](int i, int j)->bool{
        for (int c = 0; c < j; ++c) if (C[i][c] == 'o') return false;
        return true;
    };
    auto clear_right = [&](int i, int j)->bool{
        for (int c = j + 1; c < N; ++c) if (C[i][c] == 'o') return false;
        return true;
    };

    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            if (C[i][j] != 'x') continue;
            // Choose direction with minimal shifts among clear ones
            int bestCost = INT_MAX;
            char dir = 0;
            int count = 0, idx = 0;
            // Up
            if (clear_up(i, j)) {
                int k = i + 1;
                if (k < bestCost) { bestCost = k; dir = 'U'; count = k; idx = j; }
            }
            // Down
            if (clear_down(i, j)) {
                int k = N - i;
                if (k < bestCost) { bestCost = k; dir = 'D'; count = k; idx = j; }
            }
            // Left
            if (clear_left(i, j)) {
                int k = j + 1;
                if (k < bestCost) { bestCost = k; dir = 'L'; count = k; idx = i; }
            }
            // Right
            if (clear_right(i, j)) {
                int k = N - j;
                if (k < bestCost) { bestCost = k; dir = 'R'; count = k; idx = i; }
            }
            // Fallback (should not happen due to guarantees), but to be safe, pick some direction
            if (dir == 0) {
                // Prefer Up then Left then Down then Right
                if (clear_up(i,j)) { dir = 'U'; count = i+1; idx = j; }
                else if (clear_left(i,j)) { dir = 'L'; count = j+1; idx = i; }
                else if (clear_down(i,j)) { dir = 'D'; count = N - i; idx = j; }
                else { dir = 'R'; count = N - j; idx = i; }
            }
            // Apply sequence: dir count times, then opposite dir count times
            for (int t = 0; t < count; ++t) ops.push_back({dir, idx});
            char odir;
            if (dir == 'U') odir = 'D';
            else if (dir == 'D') odir = 'U';
            else if (dir == 'L') odir = 'R';
            else odir = 'L';
            for (int t = 0; t < count; ++t) ops.push_back({odir, idx});
        }
    }

    // Output
    // Truncate if somehow exceeded limit (defensive; should not exceed 4*N*N)
    int Tlim = 4 * N * N;
    if ((int)ops.size() > Tlim) ops.resize(Tlim);
    for (auto &m : ops) {
        cout << m.d << ' ' << m.p << '\n';
    }
    return 0;
}