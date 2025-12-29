#include <bits/stdc++.h>
using namespace std;

const int R = 8;
const int C = 14;
const int N = R * C;
const int MAX_N = 400;
const int TRIALS = 150;

vector<int> adj[N];
vector<vector<int>> numDigits;

bool canRead(const array<int, N>& grid, const vector<int>& digits) {
    int L = (int)digits.size();
    int first = digits[0];

    int curList[N];
    int curCount = 0;

    for (int i = 0; i < N; ++i) {
        if (grid[i] == first) {
            curList[curCount++] = i;
        }
    }
    if (curCount == 0) return false;

    bool nxtMask[N];
    int nextList[N];

    for (int pos = 1; pos < L; ++pos) {
        int need = digits[pos];
        memset(nxtMask, 0, sizeof(nxtMask));
        int nextCount = 0;

        for (int idx = 0; idx < curCount; ++idx) {
            int u = curList[idx];
            const vector<int>& nu = adj[u];
            for (int v : nu) {
                if (!nxtMask[v] && grid[v] == need) {
                    nxtMask[v] = true;
                    nextList[nextCount++] = v;
                }
            }
        }

        if (nextCount == 0) return false;

        curCount = nextCount;
        for (int i = 0; i < curCount; ++i) {
            curList[i] = nextList[i];
        }
    }

    return true;
}

int evaluate(const array<int, N>& grid) {
    for (int n = 1; n <= MAX_N; ++n) {
        if (!canRead(grid, numDigits[n])) return n - 1;
    }
    return MAX_N;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    // Precompute adjacency
    for (int r = 0; r < R; ++r) {
        for (int c = 0; c < C; ++c) {
            int id = r * C + c;
            for (int dr = -1; dr <= 1; ++dr) {
                for (int dc = -1; dc <= 1; ++dc) {
                    if (dr == 0 && dc == 0) continue;
                    int nr = r + dr;
                    int nc = c + dc;
                    if (0 <= nr && nr < R && 0 <= nc && nc < C) {
                        adj[id].push_back(nr * C + nc);
                    }
                }
            }
        }
    }

    // Precompute digits for numbers 1..MAX_N
    numDigits.assign(MAX_N + 1, vector<int>());
    for (int n = 1; n <= MAX_N; ++n) {
        int x = n;
        vector<int> ds;
        while (x > 0) {
            ds.push_back(x % 10);
            x /= 10;
        }
        reverse(ds.begin(), ds.end());
        numDigits[n] = ds;
    }

    // RNG
    mt19937 rng((unsigned)chrono::steady_clock::now().time_since_epoch().count());
    uniform_int_distribution<int> distDigit(0, 9);

    array<int, N> bestGrid;
    int bestScore = -1;

    array<int, N> grid;

    for (int t = 0; t < TRIALS; ++t) {
        for (int i = 0; i < N; ++i) {
            grid[i] = distDigit(rng);
        }
        int score = evaluate(grid);
        if (score > bestScore) {
            bestScore = score;
            bestGrid = grid;
        }
    }

    // Output best grid
    for (int r = 0; r < R; ++r) {
        for (int c = 0; c < C; ++c) {
            cout << bestGrid[r * C + c];
        }
        cout << '\n';
    }

    return 0;
}