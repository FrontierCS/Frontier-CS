#include <bits/stdc++.h>
using namespace std;

static inline uint64_t splitmix64(uint64_t &x) {
    uint64_t z = (x += 0x9e3779b97f4a7c15ULL);
    z = (z ^ (z >> 30)) * 0xbf58476d1ce4e5b9ULL;
    z = (z ^ (z >> 27)) * 0x94d049bb133111ebULL;
    return z ^ (z >> 31);
}

struct RNG {
    uint64_t x;
    RNG() {
        uint64_t seed = chrono::high_resolution_clock::now().time_since_epoch().count();
        x = seed;
    }
    uint64_t operator()() { return splitmix64(x); }
    int nextInt(int l, int r) { // inclusive
        return (int)(operator()() % (uint64_t)(r - l + 1)) + l;
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N, M;
    if (!(cin >> N >> M)) {
        return 0;
    }
    vector<string> S(M);
    for (int i = 0; i < M; i++) cin >> S[i];

    RNG rng;

    auto countMatches = [&](const vector<string>& grid) -> int {
        vector<string> rows2(N), cols2(N);
        for (int i = 0; i < N; i++) {
            rows2[i] = grid[i] + grid[i];
        }
        for (int j = 0; j < N; j++) {
            string col(N, '.');
            for (int i = 0; i < N; i++) col[i] = grid[i][j];
            cols2[j] = col + col;
        }
        int c = 0;
        for (int idx = 0; idx < M; idx++) {
            const string &s = S[idx];
            bool found = false;
            for (int i = 0; i < N && !found; i++) {
                if (rows2[i].find(s) != string::npos) {
                    found = true;
                    break;
                }
            }
            for (int j = 0; j < N && !found; j++) {
                if (cols2[j].find(s) != string::npos) {
                    found = true;
                    break;
                }
            }
            if (found) c++;
        }
        return c;
    };

    auto buildWithOrder = [&](const vector<int>& order) -> vector<string> {
        vector<string> grid(N, string(N, '.'));
        array<int, 64> dummy{}; (void)dummy;
        vector<int> rowUsed(N, 0), colUsed(N, 0);

        for (int id : order) {
            const string &s = S[id];
            int k = (int)s.size();
            int bestScore = -1;
            int bestUsedLine = -1;
            int bestOri = -1, bestI = -1, bestJ = -1;

            // orientation 0: horizontal, 1: vertical
            for (int ori = 0; ori < 2; ori++) {
                if (ori == 0) {
                    for (int i = 0; i < N; i++) {
                        for (int j = 0; j < N; j++) {
                            int matched = 0;
                            bool conflict = false;
                            int c = j;
                            for (int p = 0; p < k; p++) {
                                char cell = grid[i][c];
                                char ch = s[p];
                                if (cell != '.' && cell != ch) {
                                    conflict = true;
                                    break;
                                }
                                if (cell == ch) matched++;
                                c++;
                                if (c == N) c = 0;
                            }
                            if (!conflict) {
                                int usedLine = rowUsed[i];
                                if (matched > bestScore ||
                                   (matched == bestScore && usedLine > bestUsedLine) ||
                                   (matched == bestScore && usedLine == bestUsedLine && (rng() & 1))) {
                                    bestScore = matched;
                                    bestUsedLine = usedLine;
                                    bestOri = 0; bestI = i; bestJ = j;
                                }
                            }
                        }
                    }
                } else {
                    for (int j = 0; j < N; j++) {
                        for (int i = 0; i < N; i++) {
                            int matched = 0;
                            bool conflict = false;
                            int r = i;
                            for (int p = 0; p < k; p++) {
                                char cell = grid[r][j];
                                char ch = s[p];
                                if (cell != '.' && cell != ch) {
                                    conflict = true;
                                    break;
                                }
                                if (cell == ch) matched++;
                                r++;
                                if (r == N) r = 0;
                            }
                            if (!conflict) {
                                int usedLine = colUsed[j];
                                if (matched > bestScore ||
                                   (matched == bestScore && usedLine > bestUsedLine) ||
                                   (matched == bestScore && usedLine == bestUsedLine && (rng() & 1))) {
                                    bestScore = matched;
                                    bestUsedLine = usedLine;
                                    bestOri = 1; bestI = i; bestJ = j;
                                }
                            }
                        }
                    }
                }
            }

            if (bestScore >= 0) {
                if (bestOri == 0) {
                    int c = bestJ;
                    for (int p = 0; p < k; p++) {
                        if (grid[bestI][c] == '.') {
                            grid[bestI][c] = S[id][p];
                            rowUsed[bestI]++;
                            colUsed[c]++;
                        }
                        c++;
                        if (c == N) c = 0;
                    }
                } else {
                    int r0 = bestI;
                    for (int p = 0; p < k; p++) {
                        if (grid[r0][bestJ] == '.') {
                            grid[r0][bestJ] = S[id][p];
                            rowUsed[r0]++;
                            colUsed[bestJ]++;
                        }
                        r0++;
                        if (r0 == N) r0 = 0;
                    }
                }
            }
        }
        return grid;
    };

    auto start = chrono::steady_clock::now();
    const int TIME_LIMIT_MS = 1800;

    vector<string> bestGrid(N, string(N, '.'));
    int bestC = 0;

    vector<int> order(M);
    iota(order.begin(), order.end(), 0);

    // Precompute string lengths to sort quickly
    vector<int> slen(M);
    for (int i = 0; i < M; i++) slen[i] = (int)S[i].size();

    int attempts = 0;
    while (true) {
        auto now = chrono::steady_clock::now();
        if ((int)chrono::duration_cast<chrono::milliseconds>(now - start).count() > TIME_LIMIT_MS) break;

        // Generate an order: shuffle then stable sort by length descending
        shuffle(order.begin(), order.end(), std::mt19937((unsigned)rng()));
        stable_sort(order.begin(), order.end(), [&](int a, int b){
            if (slen[a] != slen[b]) return slen[a] > slen[b];
            return a < b;
        });

        vector<string> grid = buildWithOrder(order);
        int c = countMatches(grid);
        if (c > bestC) {
            bestC = c;
            bestGrid = grid;
        }
        attempts++;
    }

    for (int i = 0; i < N; i++) {
        cout << bestGrid[i] << '\n';
    }

    return 0;
}