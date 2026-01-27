#include <bits/stdc++.h>
using namespace std;

struct Solution {
    int r, c;
    vector<string> grid;
    long long cost;
};

long long computeCost(const vector<string>& g, int x, int y) {
    long long black = 0, white = 0;
    for (const auto& row : g) {
        for (char ch : row) {
            if (ch == '@') black++;
            else white++;
        }
    }
    return black * x + white * y;
}

int capBothRows(int W) { // capacity of L islands per segment using top and bottom rows
    if (W < 3) return 0;
    int n = W - 2;
    return (n % 2 == 0) ? n : (n + 1);
}

int capOneRow(int W) { // capacity per segment using bottom row only
    if (W < 3) return 0;
    return (W - 1) / 2; // ceil((W-2)/2)
}

Solution buildScenarioMinS(int s, int l, char SChar, char LChar, int x, int y) {
    // Scenario 1: S has smaller number of components (s), L has l components.
    // Build s segments of S separated by (s - 1) columns of L.
    // Add (l - (s - 1)) L islands in top/bottom rows inside segments.
    int add = l - (s - 1);
    int W = 2;
    while (s * capBothRows(W) < add) ++W;

    int c = s * W + (s - 1);
    int r = 3;
    vector<string> g(r, string(c, SChar));

    // Place separators (L columns)
    for (int i = 0; i < s - 1; ++i) {
        int sepCol = i * (W + 1) + W;
        for (int rr = 0; rr < r; ++rr) g[rr][sepCol] = LChar;
    }

    // Place L islands
    int remaining = add;
    for (int i = 0; i < s && remaining > 0; ++i) {
        int start = i * (W + 1);
        for (int rr : {0, 2}) {
            for (int cc = start + 1; cc <= start + W - 2 && remaining > 0; cc += 2) {
                g[rr][cc] = LChar;
                --remaining;
            }
            if (remaining == 0) break;
        }
    }

    Solution sol;
    sol.r = r; sol.c = c; sol.grid = move(g);
    sol.cost = computeCost(sol.grid, x, y);
    return sol;
}

Solution buildScenarioMaxS(int S, int m, char SChar, char LChar, int x, int y) {
    // Scenario 2: S has larger number of components (S), L has m components.
    // Initially separators give (S - 1) L components.
    // If m < (S - 1), connect some separators via top-row walkway across interior segments.
    // If m > (S - 1), add islands in bottom row inside segments.
    int merges = max(0, (S - 1) - m);
    int add = max(0, m - (S - 1));

    int W = 2;
    while (S * capOneRow(W) < add) ++W;

    int c = S * W + (S - 1);
    int r = 3;
    vector<string> g(r, string(c, SChar));

    // Place separators (L columns)
    for (int i = 0; i < S - 1; ++i) {
        int sepCol = i * (W + 1) + W;
        for (int rr = 0; rr < r; ++rr) g[rr][sepCol] = LChar;
    }

    // Connect separators via top-row walkway for required merges across interior segments
    for (int i = 1; i <= merges; ++i) { // interior segments are 1..S-2
        int start = i * (W + 1);
        for (int cc = start; cc < start + W; ++cc) g[0][cc] = LChar;
    }

    // Add L islands in bottom row if needed
    int remaining = add;
    for (int i = 0; i < S && remaining > 0; ++i) {
        int start = i * (W + 1);
        for (int cc = start + 1; cc <= start + W - 2 && remaining > 0; cc += 2) {
            g[2][cc] = LChar;
            --remaining;
        }
    }

    Solution sol;
    sol.r = r; sol.c = c; sol.grid = move(g);
    sol.cost = computeCost(sol.grid, x, y);
    return sol;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int b, w, x, y;
    if (!(cin >> b >> w >> x >> y)) return 0;

    Solution best;
    bool has = false;

    // Scenario 1: S is the color with min components
    {
        int s = min(b, w), l = max(b, w);
        char SChar = (b <= w ? '@' : '.');
        char LChar = (b <= w ? '.' : '@');
        Solution sol = buildScenarioMinS(s, l, SChar, LChar, x, y);
        if (!has || sol.cost < best.cost) { best = move(sol); has = true; }
    }

    // Scenario 2: S is the color with max components
    {
        int S = max(b, w), m = min(b, w);
        char SChar = (b >= w ? '@' : '.');
        char LChar = (b >= w ? '.' : '@');
        Solution sol = buildScenarioMaxS(S, m, SChar, LChar, x, y);
        if (!has || sol.cost < best.cost) { best = move(sol); has = true; }
    }

    cout << best.r << " " << best.c << "\n";
    for (auto& row : best.grid) cout << row << "\n";
    return 0;
}