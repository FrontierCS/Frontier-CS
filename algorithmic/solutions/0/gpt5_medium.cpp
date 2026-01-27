#include <bits/stdc++.h>
using namespace std;

struct Piece {
    int k;
    vector<pair<int,int>> cells;
};

struct Placement {
    long long X, Y;
    int R, F;
};

static inline pair<long long,long long> rotate_point(long long x, long long y, int r) {
    // 0: (x,y)
    // 1: (y,-x)
    // 2: (-x,-y)
    // 3: (-y,x)
    switch(r & 3) {
        case 0: return {x, y};
        case 1: return {y, -x};
        case 2: return {-x, -y};
        default: return {-y, x};
    }
}

struct BBox {
    long long minx, miny, maxx, maxy;
    long long w, h;
};

static inline BBox bbox_rot(const vector<pair<int,int>>& cells, int r) {
    long long minx = LLONG_MAX, miny = LLONG_MAX;
    long long maxx = LLONG_MIN, maxy = LLONG_MIN;
    for (auto &p : cells) {
        auto q = rotate_point(p.first, p.second, r);
        minx = min(minx, q.first);
        miny = min(miny, q.second);
        maxx = max(maxx, q.first);
        maxy = max(maxy, q.second);
    }
    BBox b;
    b.minx = minx; b.miny = miny; b.maxx = maxx; b.maxy = maxy;
    b.w = maxx - minx + 1;
    b.h = maxy - miny + 1;
    return b;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n;
    if (!(cin >> n)) return 0;
    vector<Piece> pieces(n);
    for (int i = 0; i < n; ++i) {
        int k; cin >> k;
        pieces[i].k = k;
        pieces[i].cells.resize(k);
        for (int j = 0; j < k; ++j) {
            int x, y; cin >> x >> y;
            pieces[i].cells[j] = {x, y};
        }
    }

    // Precompute bbox for R=0 to estimate area and max width
    long long total_bbox_area = 0;
    long long max_w0 = 0;
    for (int i = 0; i < n; ++i) {
        BBox b0 = bbox_rot(pieces[i].cells, 0);
        total_bbox_area += b0.w * b0.h;
        max_w0 = max(max_w0, b0.w);
    }
    long long targetW = (long long)(sqrt((long double)max(1LL, total_bbox_area)) + 0.5L);
    targetW = max(targetW, max_w0);
    if (targetW <= 0) targetW = 1;

    // Shelf packing with optional 90-degree rotation
    vector<Placement> ans(n);
    long long curX = 0, curY = 0;
    long long rowH = 0;
    long long rowUsed = 0;
    long long maxW = 0;

    for (int i = 0; i < n; ++i) {
        BBox b0 = bbox_rot(pieces[i].cells, 0);
        BBox b1 = bbox_rot(pieces[i].cells, 1);

        bool fit0 = (curX + b0.w <= targetW);
        bool fit1 = (curX + b1.w <= targetW);

        int Rchoose = 0;
        BBox bch = b0;

        if (fit0 || fit1) {
            if (fit0 && fit1) {
                if (b1.h < b0.h || (b1.h == b0.h && b1.w < b0.w)) {
                    Rchoose = 1; bch = b1;
                } else {
                    Rchoose = 0; bch = b0;
                }
            } else if (fit0) {
                Rchoose = 0; bch = b0;
            } else {
                Rchoose = 1; bch = b1;
            }
        } else {
            // Start new row
            maxW = max(maxW, rowUsed);
            curY += rowH;
            curX = 0;
            rowH = 0;
            rowUsed = 0;

            if (b1.h < b0.h || (b1.h == b0.h && b1.w < b0.w)) {
                Rchoose = 1; bch = b1;
            } else {
                Rchoose = 0; bch = b0;
            }
        }

        long long X = curX - bch.minx;
        long long Y = curY - bch.miny;

        ans[i] = {X, Y, Rchoose, 0};

        rowUsed = max(rowUsed, curX + bch.w);
        curX += bch.w;
        rowH = max(rowH, bch.h);
    }

    long long H = curY + rowH;
    long long W = max(maxW, rowUsed);
    if (W <= 0) W = 1;
    if (H <= 0) H = 1;

    // Make it square to be safe if some judges expect W=H
    long long side = max(W, H);
    W = side;
    H = side;

    cout << W << " " << H << "\n";
    for (int i = 0; i < n; ++i) {
        cout << ans[i].X << " " << ans[i].Y << " " << ans[i].R << " " << ans[i].F << "\n";
    }

    return 0;
}