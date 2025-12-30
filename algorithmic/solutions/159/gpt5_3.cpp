#include <bits/stdc++.h>
using namespace std;

struct Op {
    int x1,y1,x2,y2,x3,y3,x4,y4;
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int N, M;
    if (!(cin >> N >> M)) return 0;
    vector<vector<char>> grid(N, vector<char>(N, 0));
    for (int i = 0; i < M; ++i) {
        int x, y;
        cin >> x >> y;
        grid[x][y] = 1;
    }

    // Used edges: horizontal and vertical unit edges
    vector<vector<char>> usedH(N, vector<char>(N-1, 0)); // usedH[y][x] for edge (x,y)-(x+1,y)
    vector<vector<char>> usedV(N, vector<char>(N-1, 0)); // usedV[x][y] for edge (x,y)-(x,y+1)

    int c = (N - 1) / 2;
    auto weight = [&](int x, int y) -> long long {
        long long dx = x - c;
        long long dy = y - c;
        return dx * dx + dy * dy + 1;
    };

    vector<Op> ops;

    // Helper to mark edges used
    auto edges_free = [&](int xL, int xR, int yB, int yT) -> bool {
        for (int x = xL; x < xR; ++x) {
            if (usedH[yB][x]) return false;
            if (usedH[yT][x]) return false;
        }
        for (int y = yB; y < yT; ++y) {
            if (usedV[xL][y]) return false;
            if (usedV[xR][y]) return false;
        }
        return true;
    };

    auto mark_edges = [&](int xL, int xR, int yB, int yT) {
        for (int x = xL; x < xR; ++x) {
            usedH[yB][x] = 1;
            usedH[yT][x] = 1;
        }
        for (int y = yB; y < yT; ++y) {
            usedV[xL][y] = 1;
            usedV[xR][y] = 1;
        }
    };

    auto row_segment_clear = [&](const vector<int>& xs, int a, int b) -> bool {
        if (a > b) swap(a, b);
        auto it = upper_bound(xs.begin(), xs.end(), a);
        if (it != xs.end() && *it < b) return false;
        return true;
    };

    auto col_segment_clear = [&](const vector<int>& ys, int a, int b) -> bool {
        if (a > b) swap(a, b);
        auto it = upper_bound(ys.begin(), ys.end(), a);
        if (it != ys.end() && *it < b) return false;
        return true;
    };

    while (true) {
        // Build row and column lists
        vector<vector<int>> rowXs(N), colYs(N);
        for (int y = 0; y < N; ++y) {
            rowXs[y].reserve(N);
            for (int x = 0; x < N; ++x) if (grid[x][y]) rowXs[y].push_back(x);
        }
        for (int x = 0; x < N; ++x) {
            colYs[x].reserve(N);
            for (int y = 0; y < N; ++y) if (grid[x][y]) colYs[x].push_back(y);
        }

        struct Cand {
            int xL, xR, yB, yT;
            int dx, dy; // new dot
            long long w;
        };
        Cand best;
        best.w = -1;

        // Enumerate vertical adjacent pairs
        for (int x = 0; x < N; ++x) {
            auto &ys = colYs[x];
            if ((int)ys.size() < 2) continue;
            for (int i = 0; i + 1 < (int)ys.size(); ++i) {
                int y1 = ys[i];
                int y2 = ys[i+1];
                // Find neighbors on row y1 around x
                auto &rx1 = rowXs[y1];
                int idx1 = lower_bound(rx1.begin(), rx1.end(), x) - rx1.begin();
                // Safety: should exist
                if (idx1 < 0 || idx1 >= (int)rx1.size() || rx1[idx1] != x) continue;

                // Option 1: use neighbor on row y1 (bottom)
                // Left neighbor
                if (idx1 - 1 >= 0) {
                    int x2 = rx1[idx1 - 1]; // left of x
                    int xL = x2, xR = x;
                    int yB = y1, yT = y2;
                    int dx = x2, dy = y2; // new dot D
                    if (!grid[dx][dy]) {
                        // Check right vertical side x2 column clear between y1..y2
                        if (col_segment_clear(colYs[x2], y1, y2)) {
                            // Check top horizontal side at y2 between x2..x
                            if (row_segment_clear(rowXs[y2], x2, x)) {
                                // Check edges not used
                                if (edges_free(xL, xR, yB, yT)) {
                                    long long wD = weight(dx, dy);
                                    if (wD > best.w) {
                                        best = {xL, xR, yB, yT, dx, dy, wD};
                                    }
                                }
                            }
                        }
                    }
                }
                // Right neighbor
                if (idx1 + 1 < (int)rx1.size()) {
                    int x2 = rx1[idx1 + 1]; // right of x
                    int xL = x, xR = x2;
                    int yB = y1, yT = y2;
                    int dx = x2, dy = y2; // new dot D
                    if (!grid[dx][dy]) {
                        if (col_segment_clear(colYs[x2], y1, y2)) {
                            if (row_segment_clear(rowXs[y2], x, x2)) {
                                if (edges_free(xL, xR, yB, yT)) {
                                    long long wD = weight(dx, dy);
                                    if (wD > best.w) {
                                        best = {xL, xR, yB, yT, dx, dy, wD};
                                    }
                                }
                            }
                        }
                    }
                }

                // Option 2: use neighbor on row y2 (top)
                auto &rx2 = rowXs[y2];
                int idx2 = lower_bound(rx2.begin(), rx2.end(), x) - rx2.begin();
                if (idx2 >= 0 && idx2 < (int)rx2.size() && rx2[idx2] == x) {
                    // Left neighbor on top
                    if (idx2 - 1 >= 0) {
                        int x2 = rx2[idx2 - 1];
                        int xL = min(x2, x);
                        int xR = max(x2, x);
                        int yB = y1, yT = y2;
                        int dx = x2, dy = y1; // new dot D at bottom with x2
                        if (!grid[dx][dy]) {
                            if (col_segment_clear(colYs[x2], y1, y2)) {
                                if (row_segment_clear(rowXs[y1], x2, x)) {
                                    if (edges_free(xL, xR, yB, yT)) {
                                        long long wD = weight(dx, dy);
                                        if (wD > best.w) {
                                            best = {xL, xR, yB, yT, dx, dy, wD};
                                        }
                                    }
                                }
                            }
                        }
                    }
                    // Right neighbor on top
                    if (idx2 + 1 < (int)rx2.size()) {
                        int x2 = rx2[idx2 + 1];
                        int xL = min(x, x2);
                        int xR = max(x, x2);
                        int yB = y1, yT = y2;
                        int dx = x2, dy = y1; // new dot D at bottom with x2
                        if (!grid[dx][dy]) {
                            if (col_segment_clear(colYs[x2], y1, y2)) {
                                if (row_segment_clear(rowXs[y1], x, x2)) {
                                    if (edges_free(xL, xR, yB, yT)) {
                                        long long wD = weight(dx, dy);
                                        if (wD > best.w) {
                                            best = {xL, xR, yB, yT, dx, dy, wD};
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }

        if (best.w < 0) break; // no more moves

        // Apply best candidate
        int xL = best.xL, xR = best.xR, yB = best.yB, yT = best.yT;
        int dx = best.dx, dy = best.dy;

        // Mark edges used
        mark_edges(xL, xR, yB, yT);

        // Place new dot
        grid[dx][dy] = 1;

        // Prepare output order: start from D = (dx,dy), then follow rectangle
        Op op;
        op.x1 = dx; op.y1 = dy;
        if (dx == xL && dy == yB) { // bottom-left
            op.x2 = xR; op.y2 = yB;
            op.x3 = xR; op.y3 = yT;
            op.x4 = xL; op.y4 = yT;
        } else if (dx == xR && dy == yB) { // bottom-right
            op.x2 = xR; op.y2 = yT;
            op.x3 = xL; op.y3 = yT;
            op.x4 = xL; op.y4 = yB;
        } else if (dx == xL && dy == yT) { // top-left
            op.x2 = xL; op.y2 = yB;
            op.x3 = xR; op.y3 = yB;
            op.x4 = xR; op.y4 = yT;
        } else { // top-right (dx == xR && dy == yT)
            op.x2 = xL; op.y2 = yT;
            op.x3 = xL; op.y3 = yB;
            op.x4 = xR; op.y4 = yB;
        }
        ops.push_back(op);
    }

    cout << ops.size() << '\n';
    for (auto &op : ops) {
        cout << op.x1 << ' ' << op.y1 << ' ' << op.x2 << ' ' << op.y2 << ' '
             << op.x3 << ' ' << op.y3 << ' ' << op.x4 << ' ' << op.y4 << '\n';
    }
    return 0;
}