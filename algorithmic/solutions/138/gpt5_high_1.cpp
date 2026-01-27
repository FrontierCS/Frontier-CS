#include <bits/stdc++.h>
using namespace std;

static const int MAXNM = 400;

struct Operation {
    int op, x, y;
};

int idxChar(char c) {
    if ('a' <= c && c <= 'z') return c - 'a';
    if ('A' <= c && c <= 'Z') return 26 + (c - 'A');
    if ('0' <= c && c <= '9') return 52 + (c - '0');
    return -1;
}

char idxToChar(int idx) {
    if (0 <= idx && idx < 26) return 'a' + idx;
    if (26 <= idx && idx < 52) return 'A' + (idx - 26);
    if (52 <= idx && idx < 62) return '0' + (idx - 52);
    return '?';
}

vector<int> countVectorGrid(const vector<string>& g) {
    vector<int> cnt(62, 0);
    for (auto &row : g) for (char c : row) cnt[idxChar(c)]++;
    return cnt;
}

bool equalCounts(const vector<int>& a, const vector<int>& b) {
    return a == b;
}

struct Preset {
    int h, w;
    vector<string> mat;
    vector<int> cnt; // 62 counts
};

struct PlacementA {
    int id; // preset index (0-based)
    int x, y; // top-left (0-based)
    bitset<MAXNM> cover;
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n, m, k;
    if (!(cin >> n >> m >> k)) {
        return 0;
    }
    vector<string> init(n), target(n);
    for (int i = 0; i < n; ++i) cin >> init[i];
    for (int i = 0; i < n; ++i) cin >> target[i];

    vector<Preset> presets(k);
    for (int i = 0; i < k; ++i) {
        int h, w;
        cin >> h >> w;
        presets[i].h = h;
        presets[i].w = w;
        presets[i].mat.resize(h);
        for (int r = 0; r < h; ++r) cin >> presets[i].mat[r];
        presets[i].cnt.assign(62, 0);
        for (int r = 0; r < h; ++r)
            for (int c = 0; c < w; ++c)
                presets[i].cnt[idxChar(presets[i].mat[r][c])]++;
    }

    int nm = n * m;

    // Step A: try to cover entire grid with presets that match target blocks exactly
    vector<PlacementA> placementsA;
    placementsA.reserve(10000);
    for (int id = 0; id < k; ++id) {
        int h = presets[id].h, w = presets[id].w;
        for (int x = 0; x + h <= n; ++x) {
            for (int y = 0; y + w <= m; ++y) {
                bool ok = true;
                for (int r = 0; r < h && ok; ++r) {
                    for (int c = 0; c < w; ++c) {
                        if (presets[id].mat[r][c] != target[x + r][y + c]) {
                            ok = false; break;
                        }
                    }
                }
                if (ok) {
                    PlacementA pa;
                    pa.id = id;
                    pa.x = x;
                    pa.y = y;
                    pa.cover.reset();
                    for (int r = 0; r < h; ++r) {
                        for (int c = 0; c < w; ++c) {
                            int idx = (x + r) * m + (y + c);
                            pa.cover.set(idx);
                        }
                    }
                    placementsA.push_back(pa);
                }
            }
        }
    }

    vector<Operation> ops;

    auto attempt_full_cover = [&]() -> bool {
        if (placementsA.empty()) return false;
        bitset<MAXNM> uncovered;
        for (int i = 0; i < nm; ++i) uncovered.set(i);
        vector<PlacementA> chosen;
        for (int step = 0; step < nm; ++step) {
            int bestIdx = -1;
            size_t bestGain = 0;
            for (int i = 0; i < (int)placementsA.size(); ++i) {
                bitset<MAXNM> inter = placementsA[i].cover & uncovered;
                size_t gain = inter.count();
                if (gain > bestGain) {
                    bestGain = gain;
                    bestIdx = i;
                }
            }
            if (bestIdx == -1 || bestGain == 0) break;
            // choose
            chosen.push_back(placementsA[bestIdx]);
            uncovered &= ~(placementsA[bestIdx].cover);
            if (uncovered.none()) break;
        }
        if (uncovered.any()) return false;
        // apply chosen overlays
        for (auto &pa : chosen) {
            ops.push_back({pa.id + 1, pa.x + 1, pa.y + 1});
        }
        // Done: final grid equals target
        cout << ops.size() << "\n";
        for (auto &op : ops) {
            cout << op.op << " " << op.x << " " << op.y << "\n";
        }
        return true;
    };

    if (attempt_full_cover()) {
        return 0;
    }

    // Step B: try to adjust counts using greedy overlays (L1 improvement), then reorder by swaps

    // Prepare for step B
    vector<string> g = init; // current grid for step B
    vector<int> C = countVectorGrid(g);
    vector<int> Tcnt = countVectorGrid(target);

    // Precompute 1x1 formulas by char (optional use in fallback if needed)
    // Not used directly now but kept for potential future enhancements.

    // Helper: recompute prefix sums for current grid g
    // ps[id][i][j] for id in 0..61, i in 0..n, j in 0..m
    auto compute_prefix = [&](vector<vector<vector<int>>> &ps) {
        ps.assign(62, vector<vector<int>>(n + 1, vector<int>(m + 1, 0)));
        for (int id = 0; id < 62; ++id) {
            for (int i = 1; i <= n; ++i) {
                int rowAccum = 0;
                for (int j = 1; j <= m; ++j) {
                    rowAccum += (idxChar(g[i - 1][j - 1]) == id) ? 1 : 0;
                    ps[id][i][j] = ps[id][i - 1][j] + rowAccum;
                }
            }
        }
    };

    auto rect_counts = [&](const vector<vector<vector<int>>> &ps, int x, int y, int h, int w, vector<int> &out) {
        out.assign(62, 0);
        int x2 = x + h, y2 = y + w;
        for (int id = 0; id < 62; ++id) {
            int v = ps[id][x2][y2] - ps[id][x][y2] - ps[id][x2][y] + ps[id][x][y];
            out[id] = v;
        }
    };

    auto L1 = [&](const vector<int>& R) -> long long {
        long long s = 0;
        for (int id = 0; id < 62; ++id) s += llabs((long long)R[id]);
        return s;
    };

    vector<Operation> opsB; // tentative overlay ops for step B

    // Greedy loop
    int overlayLimit = 400;
    bool adjusted = false;
    {
        int used = 0;
        vector<vector<vector<int>>> ps;
        while (!equalCounts(C, Tcnt) && used < overlayLimit) {
            vector<int> R(62, 0);
            for (int id = 0; id < 62; ++id) R[id] = Tcnt[id] - C[id];
            compute_prefix(ps);
            long long bestImprove = 0;
            int bestId = -1, bestX = -1, bestY = -1;
            vector<int> rectCnt(62);
            for (int id = 0; id < k; ++id) {
                int h = presets[id].h, w = presets[id].w;
                const vector<int>& Fcnt = presets[id].cnt;
                for (int x = 0; x + h <= n; ++x) {
                    for (int y = 0; y + w <= m; ++y) {
                        rect_counts(ps, x, y, h, w, rectCnt);
                        long long improve = 0;
                        for (int t = 0; t < 62; ++t) {
                            int d = Fcnt[t] - rectCnt[t];
                            long long before = llabs((long long)R[t]);
                            long long after = llabs((long long)R[t] - d);
                            improve += (before - after);
                        }
                        if (improve > bestImprove) {
                            bestImprove = improve;
                            bestId = id; bestX = x; bestY = y;
                        }
                    }
                }
            }
            if (bestImprove <= 0) break; // cannot improve further
            // apply best overlay
            // recompute rectCnt and delta
            rect_counts(ps, bestX, bestY, presets[bestId].h, presets[bestId].w, rectCnt);
            for (int t = 0; t < 62; ++t) {
                int d = presets[bestId].cnt[t] - rectCnt[t];
                C[t] += d;
            }
            // update grid g area
            for (int r = 0; r < presets[bestId].h; ++r) {
                for (int c = 0; c < presets[bestId].w; ++c) {
                    g[bestX + r][bestY + c] = presets[bestId].mat[r][c];
                }
            }
            opsB.push_back({bestId + 1, bestX + 1, bestY + 1});
            used++;
        }
        adjusted = equalCounts(C, Tcnt);
    }

    auto solve_with_swaps = [&](const vector<string>& startGrid, vector<Operation>& outOps) -> bool {
        vector<string> cur = startGrid;
        auto applySwapRight = [&](int r, int c) {
            // swap (r,c) with (r,c+1)
            outOps.push_back({-1, r + 1, c + 1});
            swap(cur[r][c], cur[r][c + 1]);
        };
        auto applySwapDown = [&](int r, int c) {
            // swap (r,c) with (r+1,c)
            outOps.push_back({-4, r + 1, c + 1});
            swap(cur[r][c], cur[r + 1][c]);
        };
        for (int rp = 0; rp < n; ++rp) {
            for (int cp = 0; cp < m; ++cp) {
                if (rp == n - 1 && cp == m - 1) break; // last cell automatically correct
                char need = target[rp][cp];
                // find need in allowed region
                int fr = -1, fc = -1;
                for (int r = rp; r < n && fr == -1; ++r) {
                    int cstart = (r == rp ? cp : 0);
                    for (int c = cstart; c < m; ++c) {
                        if (cur[r][c] == need) { fr = r; fc = c; break; }
                    }
                }
                if (fr == -1) {
                    return false; // should not happen if counts match
                }
                int r = fr, c = fc;
                if (r == rp) {
                    while (c > cp) {
                        applySwapRight(r, c - 1);
                        c--;
                    }
                } else {
                    // ensure c >= cp
                    while (c < cp) {
                        applySwapRight(r, c);
                        c++;
                    }
                    while (r > rp) {
                        applySwapDown(r - 1, c);
                        r--;
                    }
                    while (c > cp) {
                        applySwapRight(r, c - 1);
                        c--;
                    }
                }
            }
        }
        // final cell automatically matches by counts
        return true;
    };

    if (adjusted) {
        vector<Operation> swapOps;
        bool ok = solve_with_swaps(g, swapOps);
        if (!ok) {
            // Fallback: if somehow failed, try from init if counts equal
            if (equalCounts(countVectorGrid(init), Tcnt)) {
                swapOps.clear();
                bool ok2 = solve_with_swaps(init, swapOps);
                if (!ok2) {
                    cout << -1 << "\n";
                    return 0;
                } else {
                    cout << (opsB.size() + swapOps.size()) << "\n";
                    for (auto &op : opsB) cout << op.op << " " << op.x << " " << op.y << "\n";
                    for (auto &op : swapOps) cout << op.op << " " << op.x << " " << op.y << "\n";
                    return 0;
                }
            } else {
                cout << -1 << "\n";
                return 0;
            }
        } else {
            cout << (opsB.size() + swapOps.size()) << "\n";
            for (auto &op : opsB) cout << op.op << " " << op.x << " " << op.y << "\n";
            for (auto &op : swapOps) cout << op.op << " " << op.x << " " << op.y << "\n";
            return 0;
        }
    } else {
        // Step B failed; try pure swaps if counts equal initially
        if (equalCounts(countVectorGrid(init), Tcnt)) {
            vector<Operation> swapOps;
            bool ok = solve_with_swaps(init, swapOps);
            if (!ok) { cout << -1 << "\n"; return 0; }
            cout << swapOps.size() << "\n";
            for (auto &op : swapOps) cout << op.op << " " << op.x << " " << op.y << "\n";
            return 0;
        } else {
            cout << -1 << "\n";
            return 0;
        }
    }
}