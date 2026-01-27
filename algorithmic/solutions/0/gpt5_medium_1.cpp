#include <bits/stdc++.h>
using namespace std;

struct Piece {
    int k;
    vector<pair<int,int>> cells;
    int bestR = 0, bestF = 0;
    int minx = 0, miny = 0;
    int w = 1, h = 1;
};

static inline void transform_point(int x, int y, int F, int R, int &ox, int &oy) {
    if (F) x = -x;
    switch (R & 3) {
        case 0: ox = x;  oy = y;  break;
        case 1: ox = y;  oy = -x; break; // 90° clockwise
        case 2: ox = -x; oy = -y; break; // 180°
        case 3: ox = -y; oy = x;  break; // 270°
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n;
    if (!(cin >> n)) return 0;
    vector<Piece> pieces(n);
    long long totalCells = 0;
    for (int i = 0; i < n; ++i) {
        int k; cin >> k;
        pieces[i].k = k;
        pieces[i].cells.resize(k);
        for (int j = 0; j < k; ++j) {
            int x, y; cin >> x >> y;
            pieces[i].cells[j] = {x, y};
        }
        totalCells += k;
    }

    long long totalBoxArea = 0;
    int maxW = 1;
    for (int i = 0; i < n; ++i) {
        auto &pc = pieces[i];
        long long bestArea = (1LL<<62);
        int bestW = 0, bestH = 0, bestMinX = 0, bestMinY = 0, bestR = 0, bestF = 0;
        for (int F = 0; F <= 1; ++F) {
            for (int R = 0; R < 4; ++R) {
                int minx = INT_MAX, miny = INT_MAX, maxx = INT_MIN, maxy = INT_MIN;
                for (auto &p : pc.cells) {
                    int ox, oy;
                    transform_point(p.first, p.second, F, R, ox, oy);
                    minx = min(minx, ox);
                    maxx = max(maxx, ox);
                    miny = min(miny, oy);
                    maxy = max(maxy, oy);
                }
                int w = maxx - minx + 1;
                int h = maxy - miny + 1;
                long long area = 1LL * w * h;
                bool take = false;
                if (area < bestArea) take = true;
                else if (area == bestArea) {
                    if (h < bestH) take = true;
                    else if (h == bestH) {
                        if (w < bestW) take = true;
                        else if (w == bestW) {
                            if (R < bestR) take = true;
                            else if (R == bestR && F < bestF) take = true;
                        }
                    }
                }
                if (take) {
                    bestArea = area;
                    bestW = w; bestH = h;
                    bestMinX = minx; bestMinY = miny;
                    bestR = R; bestF = F;
                }
            }
        }
        pc.bestR = bestR;
        pc.bestF = bestF;
        pc.minx = bestMinX;
        pc.miny = bestMinY;
        pc.w = bestW;
        pc.h = bestH;
        totalBoxArea += 1LL * pc.w * pc.h;
        maxW = max(maxW, pc.w);
    }

    // Determine target shelf width
    long double root = sqrt((long double)max(1LL, totalBoxArea));
    int Wcap = (int)ceill(root);
    Wcap = max(Wcap, maxW);
    if (Wcap < 1) Wcap = 1;

    // Sort pieces by height descending for shelf packing
    vector<int> order(n);
    iota(order.begin(), order.end(), 0);
    stable_sort(order.begin(), order.end(), [&](int a, int b){
        if (pieces[a].h != pieces[b].h) return pieces[a].h > pieces[b].h;
        return pieces[a].w > pieces[b].w;
    });

    vector<long long> X(n), Y(n);
    vector<int> R(n), F(n);

    long long x = 0, y = 0, shelfH = 0, maxWused = 0;
    for (int idx : order) {
        auto &pc = pieces[idx];
        if (x + pc.w > Wcap) {
            y += shelfH;
            x = 0;
            shelfH = 0;
        }
        X[idx] = x - pc.minx;
        Y[idx] = y - pc.miny;
        R[idx] = pc.bestR;
        F[idx] = pc.bestF;

        x += pc.w;
        shelfH = max<long long>(shelfH, pc.h);
        maxWused = max(maxWused, x);
    }
    long long Hused = y + shelfH;
    long long Wused = maxWused;

    long long side = max(Wused, Hused);
    if (side < 1) side = 1;

    cout << side << " " << side << "\n";
    for (int i = 0; i < n; ++i) {
        cout << X[i] << " " << Y[i] << " " << R[i] << " " << F[i] << "\n";
    }

    return 0;
}