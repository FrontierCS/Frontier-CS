#include <bits/stdc++.h>
using namespace std;

struct Pos {
    int dir, i, j, newCells;
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int N, M;
    if (!(cin >> N >> M)) return 0;
    vector<string> S(M);
    for (int i = 0; i < M; ++i) cin >> S[i];

    vector<vector<char>> grid(N, vector<char>(N, '.'));
    int usedCells = 0;
    int maxK = 0;
    for (auto &s : S) maxK = max(maxK, (int)s.size());

    vector<int> ord(M);
    iota(ord.begin(), ord.end(), 0);
    stable_sort(ord.begin(), ord.end(), [&](int a, int b) {
        if (S[a].size() != S[b].size()) return S[a].size() < S[b].size();
        return a < b;
    });

    vector<bool> done(M, false);

    auto findBestUpTo = [&](const string &s, int cap) -> Pos {
        Pos best = {-1, -1, -1, cap + 1};
        int k = (int)s.size();
        for (int dir = 0; dir < 2; ++dir) {
            for (int i = 0; i < N; ++i) {
                for (int j = 0; j < N; ++j) {
                    int newCells = 0;
                    bool conflict = false;
                    for (int p = 0; p < k; ++p) {
                        int r = (dir == 0) ? i : (i + p) % N;
                        int c = (dir == 0) ? (j + p) % N : j;
                        char cell = grid[r][c];
                        if (cell == '.') {
                            ++newCells;
                            if (newCells > best.newCells || newCells > cap) { conflict = true; break; }
                        } else if (cell != s[p]) {
                            conflict = true;
                            break;
                        }
                    }
                    if (!conflict) {
                        if (newCells < best.newCells) {
                            best = {dir, i, j, newCells};
                            if (best.newCells == 0) return best;
                        }
                    }
                }
            }
        }
        return best;
    };

    for (int T = 0; T <= maxK; ++T) {
        bool progress = true;
        while (progress) {
            progress = false;
            for (int idx : ord) {
                if (done[idx]) continue;
                Pos pos = findBestUpTo(S[idx], T);
                if (pos.newCells <= T) {
                    done[idx] = true;
                    if (pos.newCells > 0) {
                        int k = (int)S[idx].size();
                        for (int p = 0; p < k; ++p) {
                            int r = (pos.dir == 0) ? pos.i : (pos.i + p) % N;
                            int c = (pos.dir == 0) ? (pos.j + p) % N : pos.j;
                            if (grid[r][c] == '.') { grid[r][c] = S[idx][p]; ++usedCells; }
                        }
                    }
                    progress = true;
                    if (usedCells == N * N) break;
                }
            }
            if (usedCells == N * N) break;
        }
        if (usedCells == N * N) break;
    }

    mt19937 rng(1234567);
    for (int i = 0; i < N; ++i)
        for (int j = 0; j < N; ++j)
            if (grid[i][j] == '.')
                grid[i][j] = char('A' + (rng() % 8));

    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) cout << grid[i][j];
        cout << '\n';
    }
    return 0;
}