#include <bits/stdc++.h>
using namespace std;

struct Point { int x, y; };
struct Orient {
    int w, h;
    int minx, miny;
    int R, F;
};
struct Piece {
    vector<Point> cells;
    array<Orient, 8> orients;
    int minHeight = INT_MAX;
    int minWidth = INT_MAX;
    long long minArea = LLONG_MAX;
    int minAreaW = 0, minAreaH = 0;
};

static inline void compute_orientations(Piece &p) {
    int idx = 0;
    for (int F = 0; F <= 1; ++F) {
        for (int R = 0; R < 4; ++R) {
            int minx = INT_MAX, miny = INT_MAX, maxx = INT_MIN, maxy = INT_MIN;
            for (auto &pt : p.cells) {
                int x = pt.x;
                int y = pt.y;
                if (F) x = -x; // reflect across y-axis
                int rx, ry;
                switch (R) {
                    case 0: rx = x;  ry = y;  break;
                    case 1: rx = y;  ry = -x; break; // 90 cw
                    case 2: rx = -x; ry = -y; break; // 180
                    case 3: rx = -y; ry = x;  break; // 270 cw
                    default: rx = x; ry = y; break;
                }
                minx = min(minx, rx);
                maxx = max(maxx, rx);
                miny = min(miny, ry);
                maxy = max(maxy, ry);
            }
            Orient o;
            o.minx = minx;
            o.miny = miny;
            o.w = maxx - minx + 1;
            o.h = maxy - miny + 1;
            o.R = R;
            o.F = F;
            p.orients[idx++] = o;

            p.minHeight = min(p.minHeight, o.h);
            p.minWidth = min(p.minWidth, o.w);
            long long area = 1LL * o.w * o.h;
            if (area < p.minArea) {
                p.minArea = area;
                p.minAreaW = o.w;
                p.minAreaH = o.h;
            }
        }
    }
}

static inline int getBestFitByHeight(const Piece &p, int limitW) {
    int best = -1;
    int bestH = INT_MAX, bestW = INT_MAX;
    for (int i = 0; i < 8; ++i) {
        const auto &o = p.orients[i];
        if (o.w <= limitW) {
            if (o.h < bestH || (o.h == bestH && o.w < bestW)) {
                best = i; bestH = o.h; bestW = o.w;
            }
        }
    }
    return best;
}
static inline int getMinWidthOrient(const Piece &p) {
    int best = 0, bestW = INT_MAX, bestH = INT_MAX;
    for (int i = 0; i < 8; ++i) {
        const auto &o = p.orients[i];
        if (o.w < bestW || (o.w == bestW && o.h < bestH)) {
            best = i; bestW = o.w; bestH = o.h;
        }
    }
    return best;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n;
    if (!(cin >> n)) return 0;
    vector<Piece> pieces(n);
    long long sumCells = 0;
    for (int i = 0; i < n; ++i) {
        int k; cin >> k;
        pieces[i].cells.resize(k);
        for (int j = 0; j < k; ++j) {
            cin >> pieces[i].cells[j].x >> pieces[i].cells[j].y;
        }
        sumCells += k;
    }
    for (int i = 0; i < n; ++i) compute_orientations(pieces[i]);
    
    // Estimate target width using sum of minimal bounding-box areas (per piece)
    long long sumMinBBArea = 0;
    for (int i = 0; i < n; ++i) sumMinBBArea += pieces[i].minArea;
    long long Wtarget_ll = (long long)ceil(sqrt((long double)max(1LL, sumMinBBArea)));
    int Wtarget = (int)max(1LL, Wtarget_ll);
    
    // Order pieces: decreasing by minimal possible height, then by minimal width (both across orientations)
    vector<int> order(n);
    iota(order.begin(), order.end(), 0);
    stable_sort(order.begin(), order.end(), [&](int a, int b){
        if (pieces[a].minHeight != pieces[b].minHeight) return pieces[a].minHeight > pieces[b].minHeight;
        if (pieces[a].minWidth != pieces[b].minWidth) return pieces[a].minWidth > pieces[b].minWidth;
        return a < b;
    });
    
    struct Place { long long X=0, Y=0; int R=0, F=0; };
    vector<Place> ans(n);
    
    long long curX = 0;
    long long curY = 0;
    int rowH = 0;
    long long Wactual = 0;
    
    auto start_new_row = [&](){
        if (curX > 0) {
            curY += rowH;
            curX = 0;
            rowH = 0;
        }
    };
    
    for (int idx : order) {
        Piece &p = pieces[idx];
        int limit = max(0LL, (long long)Wtarget - curX);
        int oriIdx = -1;
        if (limit > 0) {
            oriIdx = getBestFitByHeight(p, limit);
        } else {
            // No space left; start new row first
            start_new_row();
            limit = Wtarget;
            oriIdx = getBestFitByHeight(p, limit);
        }
        if (oriIdx == -1) {
            // No orientation fits within target width at row start; choose minimal width orientation
            if (curX > 0) start_new_row();
            oriIdx = getMinWidthOrient(p);
        }
        const Orient &o = p.orients[oriIdx];
        long long X = curX - o.minx;
        long long Y = curY - o.miny;
        ans[idx] = {X, Y, o.R, o.F};
        curX += o.w;
        rowH = max(rowH, o.h);
        Wactual = max(Wactual, curX);
    }
    long long Hactual = curY + rowH;
    long long W = max(1LL, Wactual);
    long long H = max(1LL, Hactual);
    
    cout << W << " " << H << "\n";
    for (int i = 0; i < n; ++i) {
        cout << ans[i].X << " " << ans[i].Y << " " << ans[i].R << " " << ans[i].F << "\n";
    }
    return 0;
}