#include <bits/stdc++.h>
using namespace std;

struct Ori {
    int w, h;
    int minx, miny;
    int R, F;
};

struct Item {
    int idx;
    int w, h;
};

struct Row {
    int y;
    int height;
    int usedx;
};

struct PackResult {
    bool ok = false;
    int needed = 0;      // if !ok: suggested next side lower bound (> current side)
    int usedHeight = 0;  // if ok: total used height
};

static inline long long isqrt_ceil(long long x) {
    long long r = (long long)floor(sqrt((long double)x));
    while (r * r < x) ++r;
    while ((r - 1) * (r - 1) >= x) --r;
    return r;
}

static inline void transformCell(int x, int y, int R, int F, int &ox, int &oy) {
    if (F) x = -x;
    switch (R & 3) {
        case 0: ox = x;  oy = y;  break;
        case 1: ox = y;  oy = -x; break; // 90 deg clockwise
        case 2: ox = -x; oy = -y; break;
        case 3: ox = -y; oy = x;  break;
    }
}

class Solver {
public:
    int n;
    vector<array<Ori, 8>> allOri;
    vector<int> minSide;
    long long totalCells = 0;

    Solver(int n_) : n(n_), allOri(n_), minSide(n_, 1) {}

    PackResult packOne(int S, const vector<int> &chosen, const vector<Item> &sortedItems,
                       vector<int> *outX, vector<int> *outY, vector<int> *outR, vector<int> *outF) {
        vector<Row> rows;
        rows.reserve(1024);
        int totalH = 0;

        for (const auto &it : sortedItems) {
            int idx = it.idx;
            int w = it.w;
            int h = it.h;

            bool placed = false;
            for (auto &row : rows) {
                if (row.usedx + w <= S) {
                    int x = row.usedx;
                    int y = row.y;
                    row.usedx += w;

                    if (outX) {
                        const Ori &o = allOri[idx][chosen[idx]];
                        (*outX)[idx] = x - o.minx;
                        (*outY)[idx] = y - o.miny;
                        (*outR)[idx] = o.R;
                        (*outF)[idx] = o.F;
                    }
                    placed = true;
                    break;
                }
            }
            if (!placed) {
                if (totalH + h > S) {
                    PackResult res;
                    res.ok = false;
                    res.needed = totalH + h;
                    return res;
                }
                Row nr{totalH, h, w};
                rows.push_back(nr);

                if (outX) {
                    const Ori &o = allOri[idx][chosen[idx]];
                    (*outX)[idx] = 0 - o.minx;
                    (*outY)[idx] = totalH - o.miny;
                    (*outR)[idx] = o.R;
                    (*outF)[idx] = o.F;
                }

                totalH += h;
            }
        }

        PackResult res;
        res.ok = true;
        res.usedHeight = totalH;
        return res;
    }

    PackResult packAny(int S, bool store,
                       vector<int> *outX, vector<int> *outY, vector<int> *outR, vector<int> *outF) {
        PackResult failRes;
        failRes.ok = false;
        failRes.needed = 0;

        vector<int> chosen(n, -1);
        vector<Item> items;
        items.reserve(n);

        int neededByPiece = 0;

        for (int i = 0; i < n; i++) {
            long long bestCost = (1LL << 62);
            int best = -1;
            for (int id = 0; id < 8; id++) {
                const Ori &o = allOri[i][id];
                if (o.w <= S && o.h <= S) {
                    // prioritize smaller width strongly, then height, then area
                    long long cost = 1LL * o.w * 1000000LL + 1LL * o.h * 1000LL + 1LL * o.w * o.h;
                    if (cost < bestCost) {
                        bestCost = cost;
                        best = id;
                    }
                }
            }
            if (best < 0) {
                neededByPiece = max(neededByPiece, minSide[i]);
            } else {
                chosen[i] = best;
                const Ori &o = allOri[i][best];
                items.push_back({i, o.w, o.h});
            }
        }

        if (neededByPiece > S) {
            failRes.needed = neededByPiece;
            return failRes;
        }

        // Try a few stable strategies (all sort by height decreasing, varying tiebreak).
        auto makeSorted = [&](int strat) {
            vector<Item> v = items;
            if (strat == 0) {
                sort(v.begin(), v.end(), [](const Item &a, const Item &b) {
                    if (a.h != b.h) return a.h > b.h;
                    if (a.w != b.w) return a.w > b.w;
                    return a.idx < b.idx;
                });
            } else if (strat == 1) {
                sort(v.begin(), v.end(), [](const Item &a, const Item &b) {
                    if (a.h != b.h) return a.h > b.h;
                    if (a.w != b.w) return a.w < b.w;
                    return a.idx < b.idx;
                });
            } else {
                sort(v.begin(), v.end(), [](const Item &a, const Item &b) {
                    if (a.h != b.h) return a.h > b.h;
                    int aa = a.w * a.h, bb = b.w * b.h;
                    if (aa != bb) return aa > bb;
                    if (a.w != b.w) return a.w > b.w;
                    return a.idx < b.idx;
                });
            }
            return v;
        };

        int bestUsedH = INT_MAX;
        int bestStrat = -1;
        int minNeeded = INT_MAX;

        vector<int> tmpX, tmpY, tmpR, tmpF;
        if (store) {
            tmpX.assign(n, 0);
            tmpY.assign(n, 0);
            tmpR.assign(n, 0);
            tmpF.assign(n, 0);
            outX->assign(n, 0);
            outY->assign(n, 0);
            outR->assign(n, 0);
            outF->assign(n, 0);
        }

        for (int strat = 0; strat < 3; strat++) {
            auto sortedItems = makeSorted(strat);
            PackResult res;
            if (store) {
                res = packOne(S, chosen, sortedItems, &tmpX, &tmpY, &tmpR, &tmpF);
                if (res.ok && res.usedHeight < bestUsedH) {
                    bestUsedH = res.usedHeight;
                    bestStrat = strat;
                    *outX = tmpX; *outY = tmpY; *outR = tmpR; *outF = tmpF;
                }
            } else {
                res = packOne(S, chosen, sortedItems, nullptr, nullptr, nullptr, nullptr);
            }

            if (res.ok) {
                // feasibility is enough; keep searching for bestUsedH only in store mode
                if (!store) return res;
            } else {
                minNeeded = min(minNeeded, res.needed);
            }
        }

        if (store && bestStrat >= 0) {
            PackResult okRes;
            okRes.ok = true;
            okRes.usedHeight = bestUsedH;
            return okRes;
        }

        failRes.needed = (minNeeded == INT_MAX ? S + 1 : minNeeded);
        return failRes;
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    cin >> n;
    Solver solver(n);

    for (int i = 0; i < n; i++) {
        int k;
        cin >> k;
        solver.totalCells += k;

        vector<pair<int,int>> cells(k);
        for (int j = 0; j < k; j++) {
            int x, y;
            cin >> x >> y;
            cells[j] = {x, y};
        }

        int ms = INT_MAX;
        for (int F = 0; F <= 1; F++) {
            for (int R = 0; R < 4; R++) {
                int id = F * 4 + R;
                int minx = INT_MAX, miny = INT_MAX, maxx = INT_MIN, maxy = INT_MIN;
                for (auto [x, y] : cells) {
                    int tx, ty;
                    transformCell(x, y, R, F, tx, ty);
                    minx = min(minx, tx);
                    miny = min(miny, ty);
                    maxx = max(maxx, tx);
                    maxy = max(maxy, ty);
                }
                Ori o;
                o.minx = minx;
                o.miny = miny;
                o.w = maxx - minx + 1;
                o.h = maxy - miny + 1;
                o.R = R;
                o.F = F;
                solver.allOri[i][id] = o;
                ms = min(ms, max(o.w, o.h));
            }
        }
        solver.minSide[i] = ms;
    }

    int lb = (int)isqrt_ceil(solver.totalCells);
    int maxMinSide = 1;
    for (int i = 0; i < n; i++) maxMinSide = max(maxMinSide, solver.minSide[i]);
    lb = max(lb, maxMinSide);

    int S = lb;
    for (int iter = 0; iter < 80; iter++) {
        PackResult res = solver.packAny(S, false, nullptr, nullptr, nullptr, nullptr);
        if (res.ok) break;
        int nxt = max(S + 1, res.needed);
        if (nxt <= S) nxt = S + 1;
        S = nxt;
        if (S > 300000) break;
    }

    vector<int> X, Y, R, F;
    while (true) {
        PackResult res = solver.packAny(S, true, &X, &Y, &R, &F);
        if (res.ok) break;
        S = max(S + 1, res.needed);
        if (S > 300000) {
            // Fallback: extremely large, but should never happen
            S = 300000;
            solver.packAny(S, true, &X, &Y, &R, &F);
            break;
        }
    }

    cout << S << " " << S << "\n";
    for (int i = 0; i < n; i++) {
        cout << X[i] << " " << Y[i] << " " << R[i] << " " << F[i] << "\n";
    }
    return 0;
}