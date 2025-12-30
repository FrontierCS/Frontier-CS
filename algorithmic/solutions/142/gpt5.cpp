#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n, m;
    if (!(cin >> n >> m)) return 0;
    int T = n + 1;
    vector<vector<int>> a(T + 1);
    for (int i = 1; i <= n; ++i) {
        a[i].resize(m);
        for (int j = 0; j < m; ++j) cin >> a[i][j];
    }
    a[T] = {}; // empty pole
    vector<vector<int>> cnt(T + 1, vector<int>(n + 1, 0));
    for (int t = 1; t <= T; ++t) {
        for (int x : a[t]) cnt[t][x]++;
    }

    auto topColor = [&](int t)->int {
        if (a[t].empty()) return 0;
        return a[t].back();
    };
    auto sz = [&](int t)->int {
        return (int)a[t].size();
    };
    vector<pair<int,int>> ops;
    ops.reserve(2000000);

    auto move_ball = [&](int x, int y) {
        // assume valid
        int b = a[x].back(); a[x].pop_back();
        a[y].push_back(b);
        cnt[x][b]--; cnt[y][b]++;
        ops.emplace_back(x, y);
    };

    vector<int> colorTotal(n+1, 0);
    for (int c = 1; c <= n; ++c) colorTotal[c] = m;

    vector<int> finishedColor(n+1, 0); // tube -> color finished
    vector<int> home(n+1, 0); // color -> tube
    vector<char> isFinishedTube(T+1, 0);
    vector<char> isProcessedColor(n+1, 0);

    auto chooseDest = [&](int ballColor, int H, int src)->int {
        int bestSame = -1;
        int bestAny = -1;
        int bestAnySize = INT_MAX;
        for (int t = 1; t <= T; ++t) {
            if (t == H || t == src) continue;
            if (isFinishedTube[t]) continue;
            if (sz(t) >= m) continue;
            if (!a[t].empty() && a[t].back() == ballColor) {
                return t; // prioritize same color top
            }
        }
        for (int t = 1; t <= T; ++t) {
            if (t == H || t == src) continue;
            if (isFinishedTube[t]) continue;
            if (sz(t) >= m) continue;
            if (sz(t) < bestAnySize) {
                bestAnySize = sz(t);
                bestAny = t;
            }
        }
        return bestAny; // could be -1 in theory, but should not happen due to reasoning
    };

    auto distToTopmost = [&](int t, int c)->int {
        if (cnt[t][c] == 0) return INT_MAX/4;
        int s = sz(t);
        for (int i = s - 1; i >= 0; --i) {
            if (a[t][i] == c) return s - 1 - i;
        }
        return INT_MAX/4;
    };

    int processed = 0;
    while (processed < n) {
        // pick H: a non-finished tube whose top color c will be processed now
        int H = -1, c = -1, bestCount = -1;
        for (int t = 1; t <= T; ++t) {
            if (isFinishedTube[t]) continue;
            if (sz(t) == 0) continue;
            int tc = topColor(t);
            if (isProcessedColor[tc]) continue;
            int cntHere = cnt[t][tc];
            if (cntHere > bestCount) {
                bestCount = cntHere;
                H = t; c = tc;
            }
        }
        if (H == -1) {
            // Fallback: pick any unprocessed color's best tube
            for (int color = 1; color <= n && H==-1; ++color) if (!isProcessedColor[color]) {
                int bestT = -1, bestCnt = -1;
                for (int t = 1; t <= T; ++t) if (!isFinishedTube[t] && cnt[t][color] > bestCnt) {
                    bestCnt = cnt[t][color];
                    bestT = t;
                }
                if (bestT != -1 && bestCnt > 0) {
                    H = bestT; c = color;
                }
            }
            if (H == -1) break; // should not happen
        }

        home[c] = H;

        // Step1: make top(H) == c by moving non-c from H until c appears or H empty
        while (sz(H) > 0 && topColor(H) != c) {
            int d = topColor(H);
            int dest = chooseDest(d, H, H);
            if (dest == -1) {
                // Shouldn't happen; try to find any available
                for (int t = 1; t <= T && dest==-1; ++t) {
                    if (t==H || isFinishedTube[t]) continue;
                    if (sz(t) < m) dest = t;
                }
                if (dest == -1) break; // no move possible
            }
            move_ball(H, dest);
        }

        // Step2: gather all c into H
        while (cnt[H][c] < m) {
            // If already all c elsewhere count 0, break
            int remaining = 0;
            for (int t = 1; t <= T; ++t) if (t != H && !isFinishedTube[t]) remaining += cnt[t][c];
            if (remaining == 0) break;

            // find a tube with top c
            int srcTop = -1;
            for (int t = 1; t <= T; ++t) {
                if (t == H || isFinishedTube[t]) continue;
                if (sz(t) > 0 && topColor(t) == c) { srcTop = t; break; }
            }
            if (srcTop != -1) {
                // ensure we don't place non-c onto H; top(H) should be c or empty
                if (sz(H) == 0 || topColor(H) == c) {
                    move_ball(srcTop, H);
                    continue;
                } else {
                    // make top(H) c
                    while (sz(H) > 0 && topColor(H) != c) {
                        int d = topColor(H);
                        int dest = chooseDest(d, H, H);
                        if (dest == -1) {
                            // emergency: find any
                            for (int t = 1; t <= T && dest==-1; ++t) {
                                if (t==H || isFinishedTube[t]) continue;
                                if (sz(t) < m) dest = t;
                            }
                            if (dest == -1) break;
                        }
                        move_ball(H, dest);
                    }
                    if (sz(H) == 0 || topColor(H) == c) {
                        move_ball(srcTop, H);
                        continue;
                    }
                }
            }
            // no tube with top c; pick one with minimal distance to bring c to top
            int bestTube = -1, bestDist = INT_MAX;
            for (int t = 1; t <= T; ++t) {
                if (t == H || isFinishedTube[t]) continue;
                if (cnt[t][c] == 0) continue;
                int d = distToTopmost(t, c);
                if (d < bestDist) {
                    bestDist = d;
                    bestTube = t;
                }
            }
            if (bestTube == -1) break; // nothing to do

            // move top balls away until c appears
            while (sz(bestTube) > 0 && topColor(bestTube) != c) {
                int d = topColor(bestTube);
                int dest = chooseDest(d, H, bestTube);
                if (dest == -1) {
                    // Try to create space by moving a c from some tube to H
                    int aux = -1;
                    for (int t = 1; t <= T; ++t) {
                        if (t == H || isFinishedTube[t]) continue;
                        if (sz(t) > 0 && topColor(t) == c) { aux = t; break; }
                    }
                    if (aux != -1 && (sz(H) == 0 || topColor(H) == c)) {
                        move_ball(aux, H);
                        // now aux has space
                        dest = aux;
                    } else {
                        // find any free spot (should exist)
                        for (int t = 1; t <= T && dest==-1; ++t) {
                            if (t == H || isFinishedTube[t] || t == bestTube) continue;
                            if (sz(t) < m) dest = t;
                        }
                        if (dest == -1) break; // hopeless
                    }
                }
                move_ball(bestTube, dest);
            }
            if (sz(H) == 0 || topColor(H) == c) {
                if (sz(bestTube) > 0 && topColor(bestTube) == c) move_ball(bestTube, H);
                else {
                    // cannot proceed; break to avoid infinite loop
                    break;
                }
            } else {
                // make H top c
                while (sz(H) > 0 && topColor(H) != c) {
                    int d = topColor(H);
                    int dest = chooseDest(d, H, H);
                    if (dest == -1) {
                        for (int t = 1; t <= T && dest==-1; ++t) {
                            if (t==H || isFinishedTube[t]) continue;
                            if (sz(t) < m) dest = t;
                        }
                        if (dest == -1) break;
                    }
                    move_ball(H, dest);
                }
                if (sz(bestTube) > 0 && topColor(bestTube) == c) move_ball(bestTube, H);
            }
        }

        // Mark H finished for color c
        isFinishedTube[H] = 1;
        isProcessedColor[c] = 1;
        finishedColor[H] = c;
        processed++;
    }

    // Output
    cout << ops.size() << "\n";
    for (auto &p : ops) cout << p.first << " " << p.second << "\n";
    return 0;
}