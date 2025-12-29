#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int N, M;
    if (!(cin >> N >> M)) return 0;
    vector<pair<int,int>> init(M);
    for (int i = 0; i < M; ++i) cin >> init[i].first >> init[i].second;

    // Grid of existing dots
    vector<vector<char>> has(N, vector<char>(N, 0));
    // Row -> list of x with dot
    vector<vector<int>> rowX(N);
    // Col -> list of y with dot
    vector<vector<int>> colY(N);

    for (auto &p : init) {
        int x = p.first, y = p.second;
        has[x][y] = 1;
        rowX[y].push_back(x);
        colY[x].push_back(y);
    }
    for (int i = 0; i < N; ++i) {
        sort(rowX[i].begin(), rowX[i].end());
        rowX[i].erase(unique(rowX[i].begin(), rowX[i].end()), rowX[i].end());
        sort(colY[i].begin(), colY[i].end());
        colY[i].erase(unique(colY[i].begin(), colY[i].end()), colY[i].end());
    }

    // Used edge segments (axis-aligned)
    // Horizontal edges: usedH[y][x] is segment from (x,y) to (x+1,y)
    // Vertical edges: usedV[x][y] is segment from (x,y) to (x,y+1)
    vector<vector<char>> usedH(N, vector<char>(max(0, N-1), 0));
    vector<vector<char>> usedV(N, vector<char>(max(0, N-1), 0));

    auto countBetween = [](const vector<int>& v, int a, int b) -> int {
        if (a > b) swap(a, b);
        auto it1 = upper_bound(v.begin(), v.end(), a);
        auto it2 = lower_bound(v.begin(), v.end(), b);
        return (int)(it2 - it1);
    };

    int c = (N - 1) / 2;
    auto weight = [&](int x, int y) -> int {
        int dx = x - c, dy = y - c;
        return dx*dx + dy*dy + 1;
    };

    vector<array<int,8>> ops;

    while (true) {
        bool found = false;
        int bx1=0, by1=0, bx2=0, by2=0;
        int bestW = -1;

        // Enumerate all possible axis-aligned rectangles with three existing dots and one missing
        for (int x2 = 0; x2 < N; ++x2) {
            const auto &Y = colY[x2];
            int Ly = (int)Y.size();
            if (Ly < 2) continue;
            for (int i = 0; i < Ly; ++i) {
                for (int j = i+1; j < Ly; ++j) {
                    int y1 = Y[i], y2 = Y[j];
                    // Check vertical edge on x2 has no other dots between y1 and y2
                    if (j - i - 1 > 0) continue; // fast check

                    const auto &rowY2 = rowX[y2];
                    for (int x1 : rowY2) {
                        if (x1 == x2) continue;
                        if (has[x1][y1]) continue; // new dot must be empty

                        int xmin = min(x1, x2), xmax = max(x1, x2);
                        int ymin = y1, ymax = y2;

                        // Vertical edge at x1: no other dots between y1 and y2 (excluding endpoints)
                        if (countBetween(colY[x1], ymin, ymax) > 0) continue;

                        // Horizontal edge at y1: no other dots between x1 and x2 (excluding endpoints)
                        if (countBetween(rowX[y1], xmin, xmax) > 0) continue;

                        // Horizontal edge at y2: no other dots between x1 and x2 (excluding endpoints)
                        if (countBetween(rowX[y2], xmin, xmax) > 0) continue;

                        // Check used segments (no overlap with previous rectangles)
                        bool bad = false;
                        for (int x = xmin; x < xmax; ++x) {
                            if (usedH[y1][x] || usedH[y2][x]) { bad = true; break; }
                        }
                        if (bad) continue;
                        for (int y = ymin; y < ymax; ++y) {
                            if (usedV[x1][y] || usedV[x2][y]) { bad = true; break; }
                        }
                        if (bad) continue;

                        int w = weight(x1, y1);
                        if (w > bestW) {
                            bestW = w;
                            bx1 = x1; by1 = y1; bx2 = x2; by2 = y2;
                            found = true;
                        }
                    }
                }
            }
        }

        if (!found) break;

        int x1 = bx1, y1 = by1, x2 = bx2, y2 = by2;
        int xmin = min(x1, x2), xmax = max(x1, x2);
        int ymin = min(y1, y2), ymax = max(y1, y2);

        // Record operation in clockwise order starting from new dot (x1,y1):
        // (x1,y1) -> (x1,y2) -> (x2,y2) -> (x2,y1)
        ops.push_back({x1, y1, x1, y2, x2, y2, x2, y1});

        // Mark used segments
        for (int x = xmin; x < xmax; ++x) {
            usedH[y1][x] = 1;
            usedH[y2][x] = 1;
        }
        for (int y = ymin; y < ymax; ++y) {
            usedV[x1][y] = 1;
            usedV[x2][y] = 1;
        }

        // Place new dot
        has[x1][y1] = 1;
        // Insert into rowX[y1] and colY[x1] keeping sorted order
        {
            auto &v = rowX[y1];
            auto it = lower_bound(v.begin(), v.end(), x1);
            if (it == v.end() || *it != x1) v.insert(it, x1);
        }
        {
            auto &v = colY[x1];
            auto it = lower_bound(v.begin(), v.end(), y1);
            if (it == v.end() || *it != y1) v.insert(it, y1);
        }
    }

    cout << ops.size() << '\n';
    for (auto &op : ops) {
        for (int i = 0; i < 8; ++i) {
            if (i) cout << ' ';
            cout << op[i];
        }
        cout << '\n';
    }
    return 0;
}