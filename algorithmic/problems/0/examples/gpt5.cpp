#include <bits/stdc++.h>
using namespace std;

struct FastScanner {
    static const int BUFSIZE = 1<<20;
    int idx, size;
    char buf[BUFSIZE];
    FastScanner(): idx(0), size(0) {}
    inline char getChar() {
        if (idx >= size) {
            size = (int)fread(buf, 1, BUFSIZE, stdin);
            idx = 0;
            if (size == 0) return 0;
        }
        return buf[idx++];
    }
    template<typename T>
    bool nextInt(T &out) {
        char c; T sign = 1, val = 0;
        c = getChar();
        if (!c) return false;
        while (c!='-' && (c<'0'||c>'9')) {
            c = getChar();
            if (!c) return false;
        }
        if (c=='-') { sign = -1; c = getChar(); }
        for (; c>='0' && c<='9'; c=getChar()) val = val*10 + (c - '0');
        out = val * sign;
        return true;
    }
};

struct VecHash {
    size_t operator()(const vector<int>& v) const noexcept {
        uint64_t h = 1469598103934665603ULL;
        for (int x : v) {
            h ^= (uint64_t)(uint32_t)x + 0x9e3779b97f4a7c15ULL + (h<<6) + (h>>2);
            h *= 1099511628211ULL;
        }
        return (size_t)h;
    }
};

struct Orientation {
    int w, h;
    unsigned char R, F;
};

struct Piece {
    int k;
    vector<pair<int,int>> cells; // original
    vector<Orientation> oris;    // unique orientations
    int minW;
    int hmin;
    int w_at_hmin;
    int areaMin;
};

struct Placement {
    int X, Y;
    unsigned char R, F;
};

struct Result {
    int W, H;
    long long area;
    vector<Placement> P; // size n
};

static inline pair<int,int> transform_point(int x, int y, int F, int R) {
    if (F) x = -x;
    int nx=x, ny=y;
    switch (R & 3) {
        case 0: nx = x; ny = y; break;
        case 1: nx = y; ny = -x; break;
        case 2: nx = -x; ny = -y; break;
        case 3: nx = -y; ny = x; break;
    }
    return {nx, ny};
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    FastScanner fs;
    int n;
    if (!fs.nextInt(n)) {
        return 0;
    }
    vector<Piece> pieces(n);
    long long totalCells = 0;
    for (int i = 0; i < n; ++i) {
        int k; fs.nextInt(k);
        pieces[i].k = k;
        pieces[i].cells.resize(k);
        totalCells += k;
        for (int j = 0; j < k; ++j) {
            int x, y; fs.nextInt(x); fs.nextInt(y);
            pieces[i].cells[j] = {x, y};
        }
    }

    // Precompute unique orientations for each piece
    for (int i = 0; i < n; ++i) {
        auto &pc = pieces[i];
        unordered_set<vector<int>, VecHash> seen;
        pc.oris.clear();
        for (int F = 0; F <= 1; ++F) {
            for (int R = 0; R < 4; ++R) {
                int minx = INT_MAX, miny = INT_MAX, maxx = INT_MIN, maxy = INT_MIN;
                vector<pair<int,int>> pts; pts.reserve(pc.k);
                pts.clear();
                for (auto &p : pc.cells) {
                    auto q = transform_point(p.first, p.second, F, R);
                    pts.push_back(q);
                    if (q.first < minx) minx = q.first;
                    if (q.second < miny) miny = q.second;
                    if (q.first > maxx) maxx = q.first;
                    if (q.second > maxy) maxy = q.second;
                }
                // Normalize so minx=0, miny=0
                int shiftx = -minx, shifty = -miny;
                vector<pair<int,int>> norm; norm.reserve(pc.k);
                for (auto &q : pts) norm.push_back({q.first + shiftx, q.second + shifty});
                sort(norm.begin(), norm.end());
                vector<int> key; key.reserve(pc.k * 2);
                for (auto &q : norm) { key.push_back(q.first); key.push_back(q.second); }

                if (seen.insert(key).second) {
                    Orientation o;
                    o.w = maxx - minx + 1;
                    o.h = maxy - miny + 1;
                    o.R = (unsigned char)R;
                    o.F = (unsigned char)F;
                    pc.oris.push_back(o);
                }
            }
        }
        if (pc.oris.empty()) {
            // Should not happen, but ensure at least identity
            Orientation o; o.w = 1; o.h = 1; o.R = 0; o.F = 0;
            pc.oris.push_back(o);
        }
        // Metrics
        pc.minW = INT_MAX;
        pc.hmin = INT_MAX;
        pc.w_at_hmin = INT_MAX;
        pc.areaMin = INT_MAX;
        for (auto &o : pc.oris) {
            pc.minW = min(pc.minW, o.w);
            if (o.h < pc.hmin) {
                pc.hmin = o.h;
                pc.w_at_hmin = o.w;
            } else if (o.h == pc.hmin) {
                pc.w_at_hmin = min(pc.w_at_hmin, o.w);
            }
            pc.areaMin = min(pc.areaMin, o.w * o.h);
        }
    }

    // Orders
    vector<int> idx(n);
    iota(idx.begin(), idx.end(), 0);

    vector<vector<int>> orders;
    {
        auto ord = idx;
        stable_sort(ord.begin(), ord.end(), [&](int a, int b) {
            if (pieces[a].hmin != pieces[b].hmin) return pieces[a].hmin > pieces[b].hmin;
            if (pieces[a].areaMin != pieces[b].areaMin) return pieces[a].areaMin > pieces[b].areaMin;
            if (pieces[a].minW != pieces[b].minW) return pieces[a].minW > pieces[b].minW;
            return a < b;
        });
        orders.push_back(ord);
    }
    {
        auto ord = idx;
        stable_sort(ord.begin(), ord.end(), [&](int a, int b) {
            if (pieces[a].areaMin != pieces[b].areaMin) return pieces[a].areaMin > pieces[b].areaMin;
            if (pieces[a].hmin != pieces[b].hmin) return pieces[a].hmin > pieces[b].hmin;
            if (pieces[a].minW != pieces[b].minW) return pieces[a].minW > pieces[b].minW;
            return a < b;
        });
        orders.push_back(ord);
    }
    {
        auto ord = idx;
        stable_sort(ord.begin(), ord.end(), [&](int a, int b) {
            if (pieces[a].minW != pieces[b].minW) return pieces[a].minW > pieces[b].minW;
            if (pieces[a].hmin != pieces[b].hmin) return pieces[a].hmin > pieces[b].hmin;
            if (pieces[a].areaMin != pieces[b].areaMin) return pieces[a].areaMin > pieces[b].areaMin;
            return a < b;
        });
        orders.push_back(ord);
    }

    int W_minGlobal = 1;
    for (int i = 0; i < n; ++i) W_minGlobal = max(W_minGlobal, pieces[i].minW);
    int baseW = (int)floor(sqrt((double)max(1LL, totalCells)));
    baseW = max(baseW, W_minGlobal);

    // width candidates
    vector<int> widthCands;
    auto addW = [&](int w) {
        if (w < W_minGlobal) w = W_minGlobal;
        if (w <= 0) w = W_minGlobal;
        widthCands.push_back(w);
    };
    addW(baseW);
    addW(W_minGlobal);
    for (int d = -5; d <= 8; ++d) {
        double factor = pow(1.12, d);
        int w = (int)llround(baseW * factor);
        addW(w);
    }
    for (int i = 1; i <= 5; ++i) addW(baseW + i);
    for (int i = 1; i <= 5; ++i) addW(baseW - i);
    addW((int)(baseW * 1.5));
    addW((int)(baseW * 0.85));
    addW((int)(baseW * 1.25));
    addW((int)(baseW * 2.0));

    // Dedup and clamp
    sort(widthCands.begin(), widthCands.end());
    widthCands.erase(unique(widthCands.begin(), widthCands.end()), widthCands.end());

    // Time limit handling
    auto tstart = chrono::high_resolution_clock::now();
    const double TIME_LIMIT = 1.85;

    Result bestRes;
    bestRes.area = (1LL<<62);
    bestRes.W = bestRes.H = 0;
    bestRes.P.resize(n);

    auto packWithWidth = [&](int W, const vector<int>& order, Result &out) {
        int y0 = 0, shelf_h = 0, x = 0;
        vector<Placement> placements(n);
        for (int id : order) {
            const auto &pc = pieces[id];
            while (true) {
                int rem = W - x;
                int bestIdx = -1;
                int bestH = INT_MAX;
                int bestW = -1; // choose larger width on tie to fill space
                int bestArea = INT_MAX;
                for (int oi = 0; oi < (int)pc.oris.size(); ++oi) {
                    const auto &o = pc.oris[oi];
                    if (o.w <= rem) {
                        if (o.h < bestH) {
                            bestH = o.h;
                            bestW = o.w;
                            bestArea = o.w * o.h;
                            bestIdx = oi;
                        } else if (o.h == bestH) {
                            if (o.w > bestW) {
                                bestW = o.w;
                                bestArea = o.w * o.h;
                                bestIdx = oi;
                            } else if (o.w == bestW) {
                                int area = o.w * o.h;
                                if (area < bestArea) {
                                    bestArea = area;
                                    bestIdx = oi;
                                }
                            }
                        }
                    }
                }
                if (bestIdx == -1) {
                    if (x == 0) {
                        // cannot fit even in empty shelf - should not happen if W >= minW
                        // fallback: pick orientation with minimal width and place anyway by increasing W (but we can't). So just choose minimal width and proceed.
                        int mw = INT_MAX, mhi = -1;
                        for (int oi = 0; oi < (int)pc.oris.size(); ++oi) {
                            const auto &o = pc.oris[oi];
                            if (o.w < mw) { mw = o.w; mhi = oi; }
                        }
                        if (mhi == -1) mhi = 0;
                        const auto &o = pc.oris[mhi];
                        placements[id] = {x, y0, o.R, o.F};
                        x += o.w;
                        shelf_h = max(shelf_h, o.h);
                        break;
                    } else {
                        // Close shelf, start new
                        y0 += shelf_h;
                        shelf_h = 0;
                        x = 0;
                        continue;
                    }
                } else {
                    const auto &o = pc.oris[bestIdx];
                    placements[id] = {x, y0, o.R, o.F};
                    x += o.w;
                    if (o.h > shelf_h) shelf_h = o.h;
                    break;
                }
            }
        }
        int H = y0 + shelf_h;
        out.W = W;
        out.H = H;
        out.area = 1LL * W * H;
        out.P.swap(placements);
    };

    // Try packing for each order and width
    for (size_t oi = 0; oi < orders.size(); ++oi) {
        const auto &order = orders[oi];
        for (size_t wi = 0; wi < widthCands.size(); ++wi) {
            auto now = chrono::high_resolution_clock::now();
            double elapsed = chrono::duration<double>(now - tstart).count();
            if (elapsed > TIME_LIMIT) break;

            Result cur;
            cur.P.resize(n);
            int W = widthCands[wi];
            packWithWidth(W, order, cur);
            // choose best
            if (cur.area < bestRes.area
                || (cur.area == bestRes.area && (cur.H < bestRes.H || (cur.H == bestRes.H && cur.W < bestRes.W)))) {
                bestRes = cur;
            }
        }
        auto now = chrono::high_resolution_clock::now();
        double elapsed = chrono::duration<double>(now - tstart).count();
        if (elapsed > TIME_LIMIT) break;
    }

    // Fallback if somehow not set
    if (bestRes.area >= (1LL<<62)) {
        // Simple fallback: single column using minimal width orientation, W = W_minGlobal
        int W = W_minGlobal;
        vector<Placement> placements(n);
        int y = 0;
        for (int i = 0; i < n; ++i) {
            int bestIdx = 0;
            int bestH = INT_MAX, bestW = INT_MAX;
            for (int oi = 0; oi < (int)pieces[i].oris.size(); ++oi) {
                auto &o = pieces[i].oris[oi];
                if (o.w <= W) {
                    if (o.h < bestH || (o.h == bestH && o.w < bestW)) {
                        bestH = o.h; bestW = o.w; bestIdx = oi;
                    }
                }
            }
            auto &o = pieces[i].oris[bestIdx];
            placements[i] = {0, y, o.R, o.F};
            y += o.h;
        }
        bestRes.W = W; bestRes.H = y; bestRes.area = 1LL*W*y; bestRes.P = placements;
    }

    // Output
    cout << bestRes.W << " " << bestRes.H << "\n";
    for (int i = 0; i < n; ++i) {
        auto &pl = bestRes.P[i];
        cout << pl.X << " " << pl.Y << " " << int(pl.R) << " " << int(pl.F) << "\n";
    }
    return 0;
}
