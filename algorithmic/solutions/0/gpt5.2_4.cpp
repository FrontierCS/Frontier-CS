#include <bits/stdc++.h>
using namespace std;

struct Cell {
    long long x, y;
};

struct Piece {
    int k = 0;
    int w = 0, h = 0;
    int r = 0, f = 0;
    long long minx = 0, miny = 0;
    int maxdim = 0;
    long long bboxArea = 0;
};

static long long ceil_sqrt_ll(long long x) {
    if (x <= 0) return 0;
    long long r = (long long)floor(sqrt((long double)x));
    while (r * r < x) ++r;
    while ((r - 1) > 0 && (r - 1) * (r - 1) >= x) --r;
    return r;
}

static inline pair<long long,long long> rot_cw(long long x, long long y, int r) {
    switch (r & 3) {
        case 0: return {x, y};
        case 1: return {y, -x};
        case 2: return {-x, -y};
        default: return {-y, x};
    }
}

static Piece best_orientation(const vector<Cell>& cells) {
    Piece best;
    bool inited = false;

    for (int f = 0; f <= 1; ++f) {
        for (int r = 0; r < 4; ++r) {
            long long minx = LLONG_MAX, miny = LLONG_MAX;
            long long maxx = LLONG_MIN, maxy = LLONG_MIN;
            for (const auto &c : cells) {
                long long x = c.x, y = c.y;
                if (f) x = -x; // reflect across y-axis before rotation
                auto [tx, ty] = rot_cw(x, y, r);
                minx = min(minx, tx);
                miny = min(miny, ty);
                maxx = max(maxx, tx);
                maxy = max(maxy, ty);
            }
            int w = (int)(maxx - minx + 1);
            int h = (int)(maxy - miny + 1);
            int md = max(w, h);
            long long area = 1LL * w * h;

            // Metric: minimize maxdim, then area, then h, then w, then f, then r
            auto better = [&](const Piece& cur) -> bool {
                if (md != cur.maxdim) return md < cur.maxdim;
                if (area != cur.bboxArea) return area < cur.bboxArea;
                if (h != cur.h) return h < cur.h;
                if (w != cur.w) return w < cur.w;
                if (f != cur.f) return f < cur.f;
                return r < cur.r;
            };

            if (!inited) {
                inited = true;
                best.k = (int)cells.size();
                best.w = w; best.h = h;
                best.maxdim = md;
                best.bboxArea = area;
                best.minx = minx; best.miny = miny;
                best.f = f; best.r = r;
            } else if (better(best)) {
                best.k = (int)cells.size();
                best.w = w; best.h = h;
                best.maxdim = md;
                best.bboxArea = area;
                best.minx = minx; best.miny = miny;
                best.f = f; best.r = r;
            }
        }
    }
    return best;
}

static bool pack_shelves(int L, const vector<Piece>& pieces, const vector<int>& ord,
                         vector<int>& outx, vector<int>& outy) {
    int n = (int)pieces.size();
    if ((int)outx.size() != n) outx.assign(n, 0);
    if ((int)outy.size() != n) outy.assign(n, 0);

    int x = 0, y = 0;
    int shelfH = 0;

    for (int idx : ord) {
        int w = pieces[idx].w;
        int h = pieces[idx].h;
        if (w > L || h > L) return false;

        if (x + w > L) {
            y += shelfH;
            x = 0;
            shelfH = 0;
        }
        if (y + h > L) return false;

        outx[idx] = x;
        outy[idx] = y;

        x += w;
        shelfH = max(shelfH, h);
    }
    return true;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    cin >> n;
    vector<Piece> pieces(n);

    long long totalCells = 0;
    for (int i = 0; i < n; ++i) {
        int k;
        cin >> k;
        totalCells += k;
        vector<Cell> cells(k);
        for (int j = 0; j < k; ++j) cin >> cells[j].x >> cells[j].y;
        pieces[i] = best_orientation(cells);
    }

    long long sumBBoxArea = 0;
    int maxDim = 1;
    long long sumW = 0;
    for (int i = 0; i < n; ++i) {
        sumBBoxArea += pieces[i].bboxArea;
        maxDim = max(maxDim, pieces[i].maxdim);
        sumW += pieces[i].w;
    }

    vector<int> ord(n);
    iota(ord.begin(), ord.end(), 0);
    sort(ord.begin(), ord.end(), [&](int a, int b) {
        const auto &A = pieces[a], &B = pieces[b];
        if (A.maxdim != B.maxdim) return A.maxdim > B.maxdim;
        if (A.h != B.h) return A.h > B.h;
        if (A.w != B.w) return A.w > B.w;
        if (A.k != B.k) return A.k > B.k;
        return a < b;
    });

    int lb = (int)max<long long>(maxDim, ceil_sqrt_ll(sumBBoxArea));
    vector<int> bestx, besty, curx, cury;

    int hi = lb;
    while (!pack_shelves(hi, pieces, ord, bestx, besty)) {
        if (hi >= (int)sumW) { // guaranteed success if single row fits
            hi = (int)sumW;
            break;
        }
        hi = min<int>(max(hi + 1, hi * 2), (int)sumW);
    }
    while (!pack_shelves(hi, pieces, ord, bestx, besty)) {
        // safety fallback
        hi = (int)sumW;
        if (!pack_shelves(hi, pieces, ord, bestx, besty)) {
            // extreme fallback: put each in separate column with large side
            hi = (int)(sumW + 10);
            pack_shelves(hi, pieces, ord, bestx, besty);
            break;
        }
    }

    int lo = lb, ans = hi;
    while (lo <= hi) {
        int mid = lo + (hi - lo) / 2;
        if (pack_shelves(mid, pieces, ord, curx, cury)) {
            ans = mid;
            bestx = curx; besty = cury;
            hi = mid - 1;
        } else {
            lo = mid + 1;
        }
    }

    int W = ans, H = ans;
    cout << W << ' ' << H << "\n";
    for (int i = 0; i < n; ++i) {
        long long X = (long long)bestx[i] - pieces[i].minx;
        long long Y = (long long)besty[i] - pieces[i].miny;
        cout << X << ' ' << Y << ' ' << pieces[i].r << ' ' << pieces[i].f << "\n";
    }
    return 0;
}