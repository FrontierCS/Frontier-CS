#include <bits/stdc++.h>
using namespace std;

struct Orientation {
    int w, h;
    int sx, sy; // shift to move min corner to (0,0)
    int r;      // rotation (0 or 1 used)
};

struct Piece {
    int id;
    int k;
    vector<pair<int,int>> cells;
    Orientation ori[2];
    int maxDim;
    int minBoundArea;
    int minWidth;
};

static Orientation computeOrientation(const vector<pair<int,int>>& cells, int r) {
    int minx = INT_MAX, miny = INT_MAX, maxx = INT_MIN, maxy = INT_MIN;
    for (auto &p : cells) {
        int x = p.first, y = p.second;
        int rx, ry;
        switch (r & 3) {
            case 0: rx = x;  ry = y;  break;        // 0°
            case 1: rx = y;  ry = -x; break;        // 90° CW
            case 2: rx = -x; ry = -y; break;        // 180°
            default: rx = -y; ry = x; break;        // 270° CW
        }
        if (rx < minx) minx = rx;
        if (ry < miny) miny = ry;
        if (rx > maxx) maxx = rx;
        if (ry > maxy) maxy = ry;
    }
    Orientation o;
    o.w = maxx - minx + 1;
    o.h = maxy - miny + 1;
    o.sx = -minx;
    o.sy = -miny;
    o.r = r & 3;
    return o;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n;
    if (!(cin >> n)) return 0;
    vector<Piece> pieces(n);
    
    long long sumCells = 0;
    long long sumMinBoundArea = 0;
    int globalMaxDim = 1;
    long long sumMinWidth = 0;
    
    for (int i = 0; i < n; ++i) {
        pieces[i].id = i;
        int k;
        cin >> k;
        pieces[i].k = k;
        sumCells += k;
        pieces[i].cells.resize(k);
        for (int j = 0; j < k; ++j) {
            int x, y;
            cin >> x >> y;
            pieces[i].cells[j] = {x, y};
        }
        pieces[i].ori[0] = computeOrientation(pieces[i].cells, 0);
        pieces[i].ori[1] = computeOrientation(pieces[i].cells, 1);
        pieces[i].maxDim = max(pieces[i].ori[0].w, pieces[i].ori[0].h); // same as ori[1] swapped
        pieces[i].minBoundArea = min(pieces[i].ori[0].w * pieces[i].ori[0].h,
                                     pieces[i].ori[1].w * pieces[i].ori[1].h);
        pieces[i].minWidth = min(pieces[i].ori[0].w, pieces[i].ori[0].h);
        if (pieces[i].maxDim > globalMaxDim) globalMaxDim = pieces[i].maxDim;
        sumMinBoundArea += pieces[i].minBoundArea;
        sumMinWidth += pieces[i].minWidth;
    }
    
    vector<int> order(n);
    iota(order.begin(), order.end(), 0);
    sort(order.begin(), order.end(), [&](int a, int b){
        const Piece &pa = pieces[a], &pb = pieces[b];
        if (pa.maxDim != pb.maxDim) return pa.maxDim > pb.maxDim;
        if (pa.minBoundArea != pb.minBoundArea) return pa.minBoundArea > pb.minBoundArea;
        if (pa.k != pb.k) return pa.k > pb.k;
        return pa.id < pb.id;
    });
    
    auto packShelf = [&](int W, bool record, vector<int> *outX, vector<int> *outY, vector<int> *outR) -> long long {
        long long rowY = 0;
        int curX = 0;
        int rowH = 0;
        for (int idx : order) {
            const Piece &p = pieces[idx];
            const Orientation &A = p.ori[0];
            const Orientation &B = p.ori[1];
            int left = W - curX;
            bool fitA = (A.w <= left);
            bool fitB = (B.w <= left);
            int chosen = -1;
            if (!fitA && !fitB) {
                // start new row
                rowY += rowH;
                curX = 0;
                rowH = 0;
                left = W;
                // choose orientation that minimizes height; tie by width
                if (A.h < B.h || (A.h == B.h && A.w <= B.w)) chosen = 0; else chosen = 1;
            } else if (fitA && fitB) {
                // choose to minimize increase in row height, then smaller width
                int incA = max(0, A.h - rowH);
                int incB = max(0, B.h - rowH);
                if (incA < incB) chosen = 0;
                else if (incB < incA) chosen = 1;
                else {
                    // tie: prefer smaller height, then smaller width
                    if (A.h < B.h || (A.h == B.h && A.w <= B.w)) chosen = 0; else chosen = 1;
                }
            } else if (fitA) {
                chosen = 0;
            } else {
                chosen = 1;
            }
            const Orientation &Ch = (chosen == 0 ? A : B);
            int posX = curX;
            int posY = (int)rowY;
            if (record) {
                (*outX)[p.id] = posX + Ch.sx;
                (*outY)[p.id] = posY + Ch.sy;
                (*outR)[p.id] = Ch.r;
            }
            curX += Ch.w;
            if (Ch.h > rowH) rowH = Ch.h;
        }
        long long H = rowY + rowH;
        return H;
    };
    
    // Generate candidate widths
    set<int> candSet;
    auto addW = [&](long long w){
        int W = (int)max<long long>(1, w);
        if (W < globalMaxDim) W = globalMaxDim;
        candSet.insert(W);
    };
    addW(globalMaxDim);
    long double baseS = sqrt((long double)max(1LL, sumCells));
    addW((long long)ceill(baseS));
    long double baseB = sqrt((long double)max(1LL, sumMinBoundArea));
    addW((long long)ceill(baseB));
    // Multipliers around baseS
    vector<long double> mults = {0.6L, 0.7L, 0.8L, 0.9L, 1.0L, 1.1L, 1.2L, 1.3L, 1.5L, 1.8L, 2.2L};
    for (auto m : mults) addW((long long)ceill(baseS * m));
    for (auto m : mults) addW((long long)ceill(baseB * m));
    // Linear sweep from globalMaxDim to sumMinWidth
    int steps = 32;
    long long upper = max<long long>(globalMaxDim, sumMinWidth);
    for (int i = 0; i <= steps; ++i) {
        long long W = globalMaxDim + (upper - globalMaxDim) * i / steps;
        addW(W);
    }
    addW(upper);
    
    vector<int> X(n), Y(n), R(n), F(n, 0);
    long long bestArea = LLONG_MAX;
    long long bestH = LLONG_MAX;
    int bestW = globalMaxDim;
    
    for (int W : candSet) {
        long long H = packShelf(W, false, nullptr, nullptr, nullptr);
        long long A = (long long)W * H;
        if (A < bestArea || (A == bestArea && (H < bestH || (H == bestH && W < bestW)))) {
            bestArea = A;
            bestH = H;
            bestW = W;
        }
    }
    
    long long finalH = packShelf(bestW, true, &X, &Y, &R);
    
    cout << bestW << " " << finalH << "\n";
    for (int i = 0; i < n; ++i) {
        cout << X[i] << " " << Y[i] << " " << R[i] << " " << F[i] << "\n";
    }
    return 0;
}