#include <bits/stdc++.h>
using namespace std;

static const int N = 30;
static const int DIRS = 4;
static const int di[4] = {0, -1, 0, 1};
static const int dj[4] = {-1, 0, 1, 0};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    // Read input
    vector<vector<int>> t(N, vector<int>(N));
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            int x;
            if (!(cin >> x)) x = 0;
            t[i][j] = x;
        }
    }

    // to mapping as given in the problem
    int to[8][4] = {
        {1, 0, -1, -1},
        {3, -1, -1, 0},
        {-1, -1, 3, 2},
        {-1, 2, 1, -1},
        {1, 0, 3, 2},
        {3, 2, 1, 0},
        {2, -1, 0, -1},
        {-1, 3, -1, 1},
    };

    // rotation mapping (rotate 90 degrees CCW)
    int rot[8] = {1,2,3,0,5,4,7,6};

    // precompute used mask for each state
    int usedMask[8] = {};
    for (int s = 0; s < 8; ++s) {
        int m = 0;
        for (int d = 0; d < 4; ++d) if (to[s][d] != -1) m |= (1 << d);
        usedMask[s] = m;
    }

    // precompute rotated states for t and r in [0..3]
    int rotState[8][4];
    for (int s = 0; s < 8; ++s) {
        int cur = s;
        for (int r = 0; r < 4; ++r) {
            rotState[s][r] = cur;
            cur = rot[cur];
        }
    }

    // current oriented states
    vector<vector<int>> cur(N, vector<int>(N));
    // initialize cur with input states (no rotation)
    for (int i = 0; i < N; ++i)
        for (int j = 0; j < N; ++j)
            cur[i][j] = t[i][j];

    auto inb = [&](int i, int j) -> bool {
        return (0 <= i && i < N && 0 <= j && j < N);
    };

    // helper lambdas
    auto used = [&](int s, int d) -> bool {
        return (usedMask[s] >> d) & 1;
    };

    // match contributions for tile (i,j) if state s is used
    auto localMatched = [&](int i, int j, int s) -> int {
        int cnt = 0;
        // left neighbor
        int ni = i, nj = j - 1;
        if (inb(ni, nj)) {
            if (used(s, 0) && used(cur[ni][nj], 2)) cnt++;
        }
        // up neighbor
        ni = i - 1; nj = j;
        if (inb(ni, nj)) {
            if (used(s, 1) && used(cur[ni][nj], 3)) cnt++;
        }
        // right neighbor
        ni = i; nj = j + 1;
        if (inb(ni, nj)) {
            if (used(s, 2) && used(cur[ni][nj], 0)) cnt++;
        }
        // down neighbor
        ni = i + 1; nj = j;
        if (inb(ni, nj)) {
            if (used(s, 3) && used(cur[ni][nj], 1)) cnt++;
        }
        return cnt;
    };

    auto boundaryExposure = [&](int i, int j, int s) -> int {
        int expo = 0;
        // left boundary
        if (j == 0 && used(s, 0)) expo++;
        // up boundary
        if (i == 0 && used(s, 1)) expo++;
        // right boundary
        if (j == N - 1 && used(s, 2)) expo++;
        // down boundary
        if (i == N - 1 && used(s, 3)) expo++;
        return expo;
    };

    // "continuation" score: number of entries that will continue to a neighbor that can accept
    auto continueScore = [&](int i, int j, int s) -> int {
        int sc = 0;
        for (int d = 0; d < 4; ++d) {
            int d2 = to[s][d];
            if (d2 == -1) continue;
            int ni = i + di[d2];
            int nj = j + dj[d2];
            if (!inb(ni, nj)) continue;
            int need = (d2 + 2) & 3;
            if (used(cur[ni][nj], need)) sc++;
        }
        return sc;
    };

    // weights
    const int W_EDGE = 1000;
    const int W_CONT = 1;
    const int W_BOUND = 1;

    // Evaluate local score for a state s at (i,j)
    auto localScore = [&](int i, int j, int s) -> int64_t {
        int m = localMatched(i, j, s);
        int b = boundaryExposure(i, j, s);
        int c = continueScore(i, j, s);
        return (int64_t)W_EDGE * m - (int64_t)W_BOUND * b + (int64_t)W_CONT * c;
    };

    // Initial greedy pass: choose best local state per tile (considering current neighbors)
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            int bestS = cur[i][j];
            int64_t bestVal = localScore(i, j, bestS);
            for (int r = 0; r < 4; ++r) {
                int s = rotState[t[i][j]][r];
                int64_t val = localScore(i, j, s);
                if (val > bestVal) {
                    bestVal = val;
                    bestS = s;
                }
            }
            cur[i][j] = bestS;
        }
    }

    // Hill climbing with time limit
    auto start_time = chrono::steady_clock::now();
    const double TIME_LIMIT = 1.85; // seconds
    mt19937 rng((uint64_t)chrono::high_resolution_clock::now().time_since_epoch().count());
    uniform_int_distribution<int> dist_cell(0, N * N - 1);

    while (true) {
        auto now = chrono::steady_clock::now();
        double elapsed = chrono::duration<double>(now - start_time).count();
        if (elapsed > TIME_LIMIT) break;

        // Randomly pick a tile
        int id = dist_cell(rng);
        int i = id / N;
        int j = id % N;

        int curS = cur[i][j];
        int64_t baseVal = localScore(i, j, curS);

        int bestS = curS;
        int64_t bestVal = baseVal;

        // Try all 4 rotations from original tile type
        for (int r = 0; r < 4; ++r) {
            int s = rotState[t[i][j]][r];
            if (s == curS) continue;
            int64_t val = localScore(i, j, s);
            if (val > bestVal) {
                bestVal = val;
                bestS = s;
            }
        }
        if (bestS != curS) {
            cur[i][j] = bestS;
        }
    }

    // Build output string of rotations r in [0..3]
    string ans;
    ans.reserve(N * N);
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            int s0 = t[i][j];
            int s = s0;
            int r = 0;
            for (; r < 4; ++r) {
                if (s == cur[i][j]) break;
                s = rot[s];
            }
            if (r == 4) r = 0; // fallback, shouldn't happen
            ans.push_back(char('0' + r));
        }
    }
    cout << ans << "\n";
    return 0;
}