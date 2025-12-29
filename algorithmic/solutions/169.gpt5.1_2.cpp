#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N;
    if (!(cin >> N)) return 0;
    vector<string> C(N);
    for (int i = 0; i < N; ++i) cin >> C[i];

    vector<vector<bool>> fuku(N, vector<bool>(N, false));
    vector<pair<int,int>> oni;
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            if (C[i][j] == 'o') fuku[i][j] = true;
            else if (C[i][j] == 'x') oni.emplace_back(i, j);
        }
    }

    vector<vector<bool>> cleared(N, vector<bool>(N, false));
    vector<pair<char,int>> moves;

    auto canUp = [&](int i, int j) -> bool {
        for (int r = 0; r < i; ++r) if (fuku[r][j]) return false;
        return true;
    };
    auto canDown = [&](int i, int j) -> bool {
        for (int r = i + 1; r < N; ++r) if (fuku[r][j]) return false;
        return true;
    };
    auto canLeft = [&](int i, int j) -> bool {
        for (int c = 0; c < j; ++c) if (fuku[i][c]) return false;
        return true;
    };
    auto canRight = [&](int i, int j) -> bool {
        for (int c = j + 1; c < N; ++c) if (fuku[i][c]) return false;
        return true;
    };

    for (auto [i, j] : oni) {
        if (cleared[i][j]) continue; // already removed

        int bestK = N + 1;
        char bestDir = '?';

        if (canUp(i, j)) {
            int k = i + 1;
            if (k < bestK) { bestK = k; bestDir = 'U'; }
        }
        if (canDown(i, j)) {
            int k = N - i;
            if (k < bestK) { bestK = k; bestDir = 'D'; }
        }
        if (canLeft(i, j)) {
            int k = j + 1;
            if (k < bestK) { bestK = k; bestDir = 'L'; }
        }
        if (canRight(i, j)) {
            int k = N - j;
            if (k < bestK) { bestK = k; bestDir = 'R'; }
        }

        if (bestDir == '?') {
            // Fallback (should not occur due to problem guarantee)
            bestDir = 'U';
            bestK = i + 1;
        }

        if (bestDir == 'U') {
            for (int t = 0; t < bestK; ++t) moves.emplace_back('U', j);
            for (int t = 0; t < bestK; ++t) moves.emplace_back('D', j);
            for (int r = 0; r < bestK; ++r) cleared[r][j] = true;
        } else if (bestDir == 'D') {
            for (int t = 0; t < bestK; ++t) moves.emplace_back('D', j);
            for (int t = 0; t < bestK; ++t) moves.emplace_back('U', j);
            for (int r = N - bestK; r < N; ++r) cleared[r][j] = true;
        } else if (bestDir == 'L') {
            for (int t = 0; t < bestK; ++t) moves.emplace_back('L', i);
            for (int t = 0; t < bestK; ++t) moves.emplace_back('R', i);
            for (int c = 0; c < bestK; ++c) cleared[i][c] = true;
        } else if (bestDir == 'R') {
            for (int t = 0; t < bestK; ++t) moves.emplace_back('R', i);
            for (int t = 0; t < bestK; ++t) moves.emplace_back('L', i);
            for (int c = N - bestK; c < N; ++c) cleared[i][c] = true;
        }
    }

    // Ensure we do not exceed the allowed number of operations
    if ((int)moves.size() > 4 * N * N) {
        moves.resize(4 * N * N);
    }

    for (auto &mv : moves) {
        cout << mv.first << ' ' << mv.second << '\n';
    }

    return 0;
}