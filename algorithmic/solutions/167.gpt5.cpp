#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N;
    if (!(cin >> N)) return 0;
    vector<pair<int,int>> m(N), s(N);
    for (int i = 0; i < N; ++i) cin >> m[i].first >> m[i].second;
    for (int i = 0; i < N; ++i) cin >> s[i].first >> s[i].second;

    const int G = 200;
    const int STEP = 500; // 200 * 500 = 100000
    vector<vector<int>> grid(G, vector<int>(G, 0));
    auto idx = [&](int x) { return min(G - 1, x / STEP); };

    for (int i = 0; i < N; ++i) {
        int xi = idx(m[i].first);
        int yi = idx(m[i].second);
        grid[yi][xi] += 1;
    }
    for (int i = 0; i < N; ++i) {
        int xi = idx(s[i].first);
        int yi = idx(s[i].second);
        grid[yi][xi] -= 1;
    }

    long long bestSum = LLONG_MIN;
    int bestT = 0, bestB = 0, bestL = 0, bestR = 0;

    vector<long long> col(G);
    for (int top = 0; top < G; ++top) {
        fill(col.begin(), col.end(), 0);
        for (int bottom = top; bottom < G; ++bottom) {
            for (int x = 0; x < G; ++x) col[x] += grid[bottom][x];

            long long curr = col[0];
            int currL = 0;
            long long localBest = col[0];
            int localL = 0, localR = 0;

            for (int x = 1; x < G; ++x) {
                if (curr + col[x] < col[x]) {
                    curr = col[x];
                    currL = x;
                } else {
                    curr += col[x];
                }
                if (curr > localBest) {
                    localBest = curr;
                    localL = currL;
                    localR = x;
                }
            }

            if (localBest > bestSum) {
                bestSum = localBest;
                bestT = top; bestB = bottom; bestL = localL; bestR = localR;
            }
        }
    }

    auto compute_diff = [&](int x0, int y0, int x1, int y1) {
        long long val = 0;
        for (int i = 0; i < N; ++i) {
            int x = m[i].first, y = m[i].second;
            if (x0 <= x && x <= x1 && y0 <= y && y <= y1) ++val;
        }
        for (int i = 0; i < N; ++i) {
            int x = s[i].first, y = s[i].second;
            if (x0 <= x && x <= x1 && y0 <= y && y <= y1) --val;
        }
        return val;
    };

    int x0 = bestL * STEP;
    int y0 = bestT * STEP;
    int x1 = min(100000, (bestR + 1) * STEP);
    int y1 = min(100000, (bestB + 1) * STEP);

    long long actual = compute_diff(x0, y0, x1, y1);

    if (actual <= 0) {
        // Fallback: full rectangle
        cout << 4 << "\n";
        cout << 0 << " " << 0 << "\n";
        cout << 0 << " " << 100000 << "\n";
        cout << 100000 << " " << 100000 << "\n";
        cout << 100000 << " " << 0 << "\n";
    } else {
        // Output the found rectangle
        cout << 4 << "\n";
        cout << x0 << " " << y0 << "\n";
        cout << x0 << " " << y1 << "\n";
        cout << x1 << " " << y1 << "\n";
        cout << x1 << " " << y0 << "\n";
    }
    return 0;
}