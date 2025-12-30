#include <bits/stdc++.h>
using namespace std;

const int R = 8, C = 14, N = R * C;
const int MAX_N = 20000;

uint64_t adjLo[N], adjHi[N];
vector<string> numStr;

bool canReadNumber(int x, const uint64_t digitLo[10], const uint64_t digitHi[10]) {
    const string &s = numStr[x];
    int L = (int)s.size();
    if (L == 0) return false;

    int d0 = s[0] - '0';
    uint64_t currLo = digitLo[d0];
    uint64_t currHi = digitHi[d0];
    if ((currLo | currHi) == 0) return false;

    for (int pos = 1; pos < L; ++pos) {
        int d = s[pos] - '0';
        uint64_t nextLo = 0, nextHi = 0;

        uint64_t tmpLo = currLo;
        while (tmpLo) {
            int bit = __builtin_ctzll(tmpLo);
            tmpLo &= tmpLo - 1;
            nextLo |= adjLo[bit] & digitLo[d];
            nextHi |= adjHi[bit] & digitHi[d];
        }

        uint64_t tmpHi = currHi;
        while (tmpHi) {
            int bit = __builtin_ctzll(tmpHi);
            tmpHi &= tmpHi - 1;
            int idx = bit + 64;
            nextLo |= adjLo[idx] & digitLo[d];
            nextHi |= adjHi[idx] & digitHi[d];
        }

        currLo = nextLo;
        currHi = nextHi;
        if ((currLo | currHi) == 0) return false;
    }

    return true;
}

int getScore(const array<int, N> &g) {
    uint64_t digitLo[10] = {0}, digitHi[10] = {0};
    for (int idx = 0; idx < N; ++idx) {
        int d = g[idx];
        if (idx < 64) digitLo[d] |= 1ULL << idx;
        else digitHi[d] |= 1ULL << (idx - 64);
    }

    for (int n = 1; n <= MAX_N; ++n) {
        if (!canReadNumber(n, digitLo, digitHi)) return n - 1;
    }
    return MAX_N;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    // Build adjacency
    for (int r = 0; r < R; ++r) {
        for (int c = 0; c < C; ++c) {
            int idx = r * C + c;
            uint64_t lo = 0, hi = 0;
            for (int dr = -1; dr <= 1; ++dr) {
                for (int dc = -1; dc <= 1; ++dc) {
                    if (dr == 0 && dc == 0) continue;
                    int nr = r + dr, nc = c + dc;
                    if (0 <= nr && nr < R && 0 <= nc && nc < C) {
                        int j = nr * C + nc;
                        if (j < 64) lo |= 1ULL << j;
                        else hi |= 1ULL << (j - 64);
                    }
                }
            }
            adjLo[idx] = lo;
            adjHi[idx] = hi;
        }
    }

    // Precompute string representations of numbers
    numStr.resize(MAX_N + 1);
    for (int i = 1; i <= MAX_N; ++i) numStr[i] = to_string(i);

    mt19937_64 rng((uint64_t)chrono::high_resolution_clock::now().time_since_epoch().count());

    const double timeLimit = 1.8;
    auto start = chrono::steady_clock::now();

    array<int, N> bestGrid{};
    for (int i = 0; i < N; ++i) bestGrid[i] = rng() % 10;
    int bestScore = getScore(bestGrid);

    while (true) {
        auto now = chrono::steady_clock::now();
        double elapsed = chrono::duration<double>(now - start).count();
        if (elapsed > timeLimit) break;

        array<int, N> grid;
        for (int i = 0; i < N; ++i) grid[i] = rng() % 10;

        int sc = getScore(grid);
        if (sc > bestScore) {
            bestScore = sc;
            bestGrid = grid;
        }
    }

    for (int r = 0; r < R; ++r) {
        for (int c = 0; c < C; ++c) {
            cout << bestGrid[r * C + c];
        }
        cout << '\n';
    }

    return 0;
}