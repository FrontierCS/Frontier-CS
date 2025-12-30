#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N;
    cin >> N;
    vector<string> C(N);
    for (int i = 0; i < N; i++) cin >> C[i];

    struct Oni { int i, j; };
    vector<Oni> onis;
    for (int i = 0; i < N; i++) {
        for (int j = 0; j < N; j++) {
            if (C[i][j] == 'x') onis.push_back({i, j});
        }
    }

    vector<pair<char,int>> ops;
    auto add_ops = [&](char d, int p, int times) {
        for (int t = 0; t < times; t++) ops.push_back({d, p});
    };

    auto no_fuku_up = [&](int i, int j) {
        for (int r = 0; r < i; r++) if (C[r][j] == 'o') return false;
        return true;
    };
    auto no_fuku_down = [&](int i, int j) {
        for (int r = i + 1; r < N; r++) if (C[r][j] == 'o') return false;
        return true;
    };
    auto no_fuku_left = [&](int i, int j) {
        for (int c = 0; c < j; c++) if (C[i][c] == 'o') return false;
        return true;
    };
    auto no_fuku_right = [&](int i, int j) {
        for (int c = j + 1; c < N; c++) if (C[i][c] == 'o') return false;
        return true;
    };

    for (auto [i, j] : onis) {
        int bestCost = INT_MAX;
        char bestDir = '?';
        int bestK = -1;
        int bestP = -1;

        if (no_fuku_up(i, j)) {
            int k = i + 1;
            int cost = 2 * k;
            if (cost < bestCost) { bestCost = cost; bestDir = 'U'; bestK = k; bestP = j; }
        }
        if (no_fuku_down(i, j)) {
            int k = N - i;
            int cost = 2 * k;
            if (cost < bestCost) { bestCost = cost; bestDir = 'D'; bestK = k; bestP = j; }
        }
        if (no_fuku_left(i, j)) {
            int k = j + 1;
            int cost = 2 * k;
            if (cost < bestCost) { bestCost = cost; bestDir = 'L'; bestK = k; bestP = i; }
        }
        if (no_fuku_right(i, j)) {
            int k = N - j;
            int cost = 2 * k;
            if (cost < bestCost) { bestCost = cost; bestDir = 'R'; bestK = k; bestP = i; }
        }

        if (bestDir == 'U') {
            add_ops('U', bestP, bestK);
            add_ops('D', bestP, bestK);
        } else if (bestDir == 'D') {
            add_ops('D', bestP, bestK);
            add_ops('U', bestP, bestK);
        } else if (bestDir == 'L') {
            add_ops('L', bestP, bestK);
            add_ops('R', bestP, bestK);
        } else if (bestDir == 'R') {
            add_ops('R', bestP, bestK);
            add_ops('L', bestP, bestK);
        } else {
            // Should not happen due to guarantee; output nothing if it does.
        }
    }

    const int LIMIT = 4 * N * N;
    if ((int)ops.size() > LIMIT) ops.resize(LIMIT);

    for (auto &[d, p] : ops) {
        cout << d << ' ' << p << "\n";
    }
    return 0;
}