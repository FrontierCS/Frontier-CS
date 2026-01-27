#include <bits/stdc++.h>
using namespace std;

static const int N = 30;
static const int MAXOPS = 10000;

struct Move {
    int x1, y1, x2, y2;
};

vector<vector<int>> a;
vector<Move> moves;

inline bool doSwap(int x1, int y1, int x2, int y2) {
    if ((int)moves.size() >= MAXOPS) return false;
    moves.push_back({x1, y1, x2, y2});
    int t = a[x1][y1];
    a[x1][y1] = a[x2][y2];
    a[x2][y2] = t;
    return true;
}

inline bool bubbleDownFrom(int x, int y) {
    while (x < N - 1) {
        int cx = x + 1, cy = y;
        int rx = x + 1, ry = y + 1;
        if (a[rx][ry] < a[cx][cy]) { cx = rx; cy = ry; }
        if (a[x][y] <= a[cx][cy]) break;
        if (!doSwap(x, y, cx, cy)) return false;
        x = cx; y = cy;
    }
    return true;
}

inline bool bubbleUpFrom(int x, int y) {
    while (x > 0) {
        int val = a[x][y];
        int bestpx = -1, bestpy = -1, bestVal = -1;
        if (y <= x - 1) {
            int pv = a[x - 1][y];
            if (pv > val && pv > bestVal) { bestVal = pv; bestpx = x - 1; bestpy = y; }
        }
        if (y - 1 >= 0) {
            int pv = a[x - 1][y - 1];
            if (pv > val && pv > bestVal) { bestVal = pv; bestpx = x - 1; bestpy = y - 1; }
        }
        if (bestpx == -1) break;
        if (!doSwap(bestpx, bestpy, x, y)) return false;
        x = bestpx; y = bestpy;
    }
    return true;
}

inline int computeE() {
    int E = 0;
    for (int x = 0; x < N - 1; ++x) {
        for (int y = 0; y <= x; ++y) {
            if (a[x][y] > a[x + 1][y]) ++E;
            if (a[x][y] > a[x + 1][y + 1]) ++E;
        }
    }
    return E;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    a.resize(N);
    for (int x = 0; x < N; ++x) {
        a[x].resize(x + 1);
        for (int y = 0; y <= x; ++y) cin >> a[x][y];
    }

    vector<int> tri(N + 1);
    for (int i = 0; i <= N; ++i) tri[i] = i * (i + 1) / 2;
    vector<int> targetRow(465);
    for (int v = 0; v < 465; ++v) {
        int lo = 0, hi = N - 1, ans = 0;
        while (lo <= hi) {
            int mid = (lo + hi) / 2;
            if (tri[mid] <= v) { ans = mid; lo = mid + 1; }
            else hi = mid - 1;
        }
        targetRow[v] = ans;
    }

    int budget1 = min(MAXOPS, 6500);
    int budget2 = min(MAXOPS, 9500);

    // Stage 1: bottom-up bubble-down passes
    for (int iter = 0; iter < 1000; ++iter) {
        bool changed = false, limitReached = false;
        for (int x = N - 2; x >= 0; --x) {
            for (int y = 0; y <= x; ++y) {
                if (a[x][y] > a[x + 1][y] || a[x][y] > a[x + 1][y + 1]) {
                    if (!bubbleDownFrom(x, y)) { limitReached = true; break; }
                    changed = true;
                }
                if ((int)moves.size() >= budget1) { limitReached = true; break; }
            }
            if (limitReached) break;
        }
        if (!changed || limitReached) break;
        if (computeE() == 0) break;
    }

    if (computeE() > 0 && (int)moves.size() < MAXOPS) {
        // Stage 2: raise small numbers toward target rows
        for (int iter = 0; iter < 1000; ++iter) {
            bool changed = false, limitReached = false;
            for (int x = N - 1; x > 0; --x) {
                for (int y = 0; y <= x; ++y) {
                    int v = a[x][y];
                    int trow = targetRow[v];
                    if (x > trow) {
                        int cx = x, cy = y;
                        while (cx > trow) {
                            int bestpx = -1, bestpy = -1, bestVal = -1;
                            if (cy <= cx - 1) {
                                int pv = a[cx - 1][cy];
                                if (pv > v && pv > bestVal) { bestVal = pv; bestpx = cx - 1; bestpy = cy; }
                            }
                            if (cy - 1 >= 0) {
                                int pv = a[cx - 1][cy - 1];
                                if (pv > v && pv > bestVal) { bestVal = pv; bestpx = cx - 1; bestpy = cy - 1; }
                            }
                            if (bestpx == -1) break;
                            if (!doSwap(bestpx, bestpy, cx, cy)) { limitReached = true; break; }
                            changed = true;
                            cx = bestpx; cy = bestpy;
                            if ((int)moves.size() >= budget2) { limitReached = true; break; }
                        }
                        if (limitReached) break;
                    }
                    if (limitReached) break;
                }
                if (limitReached) break;
            }
            if (!changed || limitReached) break;
            if (computeE() == 0) break;
        }
    }

    if (computeE() > 0 && (int)moves.size() < MAXOPS) {
        // Stage 3: bubble-down again to repair violations
        for (int iter = 0; iter < 1000; ++iter) {
            bool changed = false, limitReached = false;
            for (int x = N - 2; x >= 0; --x) {
                for (int y = 0; y <= x; ++y) {
                    if (a[x][y] > a[x + 1][y] || a[x][y] > a[x + 1][y + 1]) {
                        if (!bubbleDownFrom(x, y)) { limitReached = true; break; }
                        changed = true;
                    }
                    if ((int)moves.size() >= MAXOPS) { limitReached = true; break; }
                }
                if (limitReached) break;
            }
            if (!changed || limitReached) break;
            if (computeE() == 0) break;
        }
    }

    if (computeE() > 0 && (int)moves.size() < MAXOPS) {
        // Stage 4: greedy fix by largest violating edge, with local up/down heap adjustments
        for (int iter = 0; iter < 20 && (int)moves.size() < MAXOPS; ++iter) {
            struct Edge { int x, y, x2, y2, diff; };
            vector<Edge> edges;
            edges.reserve(N * N);
            for (int x = 0; x < N - 1; ++x) {
                for (int y = 0; y <= x; ++y) {
                    if (a[x][y] > a[x + 1][y]) edges.push_back({x, y, x + 1, y, a[x][y] - a[x + 1][y]});
                    if (a[x][y] > a[x + 1][y + 1]) edges.push_back({x, y, x + 1, y + 1, a[x][y] - a[x + 1][y + 1]});
                }
            }
            if (edges.empty()) break;
            sort(edges.begin(), edges.end(), [](const Edge &A, const Edge &B) { return A.diff > B.diff; });
            int preMoves = (int)moves.size();
            for (auto &ed : edges) {
                if ((int)moves.size() >= MAXOPS) break;
                int x = ed.x, y = ed.y, cx = ed.x2, cy = ed.y2;
                if (a[x][y] <= a[cx][cy]) continue;
                if (!doSwap(x, y, cx, cy)) break;
                if (!bubbleUpFrom(x, y)) break;
                if (!bubbleDownFrom(cx, cy)) break;
                if (computeE() == 0) break;
            }
            if ((int)moves.size() == preMoves || computeE() == 0) break;
        }
    }

    cout << moves.size() << '\n';
    for (auto &mv : moves) {
        cout << mv.x1 << ' ' << mv.y1 << ' ' << mv.x2 << ' ' << mv.y2 << '\n';
    }
    return 0;
}