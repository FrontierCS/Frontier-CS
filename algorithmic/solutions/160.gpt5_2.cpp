#include <bits/stdc++.h>
using namespace std;

struct Board {
    array<array<int, 10>, 10> g{};
};

static const int N = 10;

pair<int,int> findPthEmpty(const Board& b, int p) {
    int cnt = 0;
    for (int r = 0; r < N; ++r) {
        for (int c = 0; c < N; ++c) {
            if (b.g[r][c] == 0) {
                ++cnt;
                if (cnt == p) return {r, c};
            }
        }
    }
    return {-1, -1}; // should not happen
}

void tilt(Board& b, char dir) {
    if (dir == 'L') {
        for (int r = 0; r < N; ++r) {
            int idx = 0;
            array<int, 10> tmp{};
            for (int c = 0; c < N; ++c) {
                if (b.g[r][c] != 0) {
                    tmp[idx++] = b.g[r][c];
                }
            }
            for (int c = 0; c < N; ++c) b.g[r][c] = (c < idx ? tmp[c] : 0);
        }
    } else if (dir == 'R') {
        for (int r = 0; r < N; ++r) {
            int idx = 0;
            array<int, 10> tmp{};
            for (int c = 0; c < N; ++c) {
                if (b.g[r][c] != 0) {
                    tmp[idx++] = b.g[r][c];
                }
            }
            int start = N - idx;
            for (int c = 0; c < start; ++c) b.g[r][c] = 0;
            for (int k = 0; k < idx; ++k) b.g[r][start + k] = tmp[k];
        }
    } else if (dir == 'F') {
        for (int c = 0; c < N; ++c) {
            int idx = 0;
            array<int, 10> tmp{};
            for (int r = 0; r < N; ++r) {
                if (b.g[r][c] != 0) {
                    tmp[idx++] = b.g[r][c];
                }
            }
            for (int r = 0; r < N; ++r) b.g[r][c] = (r < idx ? tmp[r] : 0);
        }
    } else if (dir == 'B') {
        for (int c = 0; c < N; ++c) {
            int idx = 0;
            array<int, 10> tmp{};
            for (int r = 0; r < N; ++r) {
                if (b.g[r][c] != 0) {
                    tmp[idx++] = b.g[r][c];
                }
            }
            int start = N - idx;
            for (int r = 0; r < start; ++r) b.g[r][c] = 0;
            for (int k = 0; k < idx; ++k) b.g[start + k][c] = tmp[k];
        }
    }
}

long long componentScore(const Board& b) {
    static const int dr[4] = {1, -1, 0, 0};
    static const int dc[4] = {0, 0, 1, -1};
    bool vis[N][N] = {};
    long long score = 0;
    for (int r = 0; r < N; ++r) {
        for (int c = 0; c < N; ++c) {
            int col = b.g[r][c];
            if (col == 0 || vis[r][c]) continue;
            int sz = 0;
            queue<pair<int,int>> q;
            q.push({r,c});
            vis[r][c] = true;
            while (!q.empty()) {
                auto [rr, cc] = q.front(); q.pop();
                ++sz;
                for (int k = 0; k < 4; ++k) {
                    int nr = rr + dr[k], nc = cc + dc[k];
                    if (nr < 0 || nr >= N || nc < 0 || nc >= N) continue;
                    if (!vis[nr][nc] && b.g[nr][nc] == col) {
                        vis[nr][nc] = true;
                        q.push({nr, nc});
                    }
                }
            }
            score += 1LL * sz * sz;
        }
    }
    return score;
}

int adjacencyScore(const Board& b) {
    int adj = 0;
    for (int r = 0; r < N; ++r) {
        for (int c = 0; c < N; ++c) {
            if (b.g[r][c] == 0) continue;
            if (c + 1 < N && b.g[r][c] == b.g[r][c+1]) ++adj;
            if (r + 1 < N && b.g[r][c] == b.g[r+1][c]) ++adj;
        }
    }
    return adj;
}

long long potentialToCorners(const Board& b, const array<pair<int,int>, 4>& target) {
    long long pot = 0;
    for (int r = 0; r < N; ++r) {
        for (int c = 0; c < N; ++c) {
            int t = b.g[r][c];
            if (t == 0) continue;
            auto [tr, tc] = target[t];
            pot += llabs(r - tr) + llabs(c - tc);
        }
    }
    return pot;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    vector<int> f(100);
    for (int i = 0; i < 100; ++i) {
        if (!(cin >> f[i])) return 0;
    }

    Board cur;
    // Assign target corners for tie-break potential:
    // Type 1 -> bottom-left (9,0)
    // Type 2 -> top-right (0,9)
    // Type 3 -> top-left (0,0)
    array<pair<int,int>, 4> target;
    target[1] = {9, 0};
    target[2] = {0, 9};
    target[3] = {0, 0};

    const array<char,4> dirs = {'L','R','F','B'};

    for (int t = 0; t < 100; ++t) {
        int p;
        if (!(cin >> p)) return 0;

        Board base = cur;
        auto [r, c] = findPthEmpty(base, p);
        if (r >= 0) base.g[r][c] = f[t];

        long long bestScore = LLONG_MIN;
        int bestAdj = INT_MIN;
        long long bestPot = LLONG_MAX;
        char bestDir = 'L';
        Board bestBoard;

        for (char d : dirs) {
            Board cand = base;
            tilt(cand, d);
            long long s = componentScore(cand);
            int adj = adjacencyScore(cand);
            long long pot = potentialToCorners(cand, target);

            if (s > bestScore ||
                (s == bestScore && adj > bestAdj) ||
                (s == bestScore && adj == bestAdj && pot < bestPot)) {
                bestScore = s;
                bestAdj = adj;
                bestPot = pot;
                bestDir = d;
                bestBoard = cand;
            }
        }

        cout << bestDir << '\n' << flush;
        cur = bestBoard;
    }

    return 0;
}