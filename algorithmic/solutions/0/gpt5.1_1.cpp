#include <bits/stdc++.h>
using namespace std;

struct Poly {
    int k;
    vector<pair<long long,long long>> cells; // original coordinates
    int bestR = 0, bestF = 0;
    long long minX = 0, minY = 0;
    int width = 1, height = 1;
    long long boxArea = 1;
    long long transX = 0, transY = 0;
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    vector<Poly> polys(n);
    long long totalBoxArea = 0;
    int maxWidthPiece = 1, maxHeightPiece = 1;

    for (int i = 0; i < n; ++i) {
        int k;
        cin >> k;
        polys[i].k = k;
        polys[i].cells.resize(k);
        for (int j = 0; j < k; ++j) {
            long long x, y;
            cin >> x >> y;
            polys[i].cells[j] = {x, y};
        }

        bool first = true;
        long long bestArea = 0;
        int bestW = 0, bestH = 0;
        long long bestMinX = 0, bestMinY = 0;
        int bestR = 0, bestF = 0;

        for (int F = 0; F <= 1; ++F) {
            for (int R = 0; R < 4; ++R) {
                long long minX = LLONG_MAX, minY = LLONG_MAX;
                long long maxX = LLONG_MIN, maxY = LLONG_MIN;

                for (int j = 0; j < k; ++j) {
                    long long x = polys[i].cells[j].first;
                    long long y = polys[i].cells[j].second;

                    if (F == 1) x = -x; // reflect across y-axis

                    long long rx, ry;
                    switch (R) {
                        case 0: rx = x;  ry = y;  break;
                        case 1: rx = y;  ry = -x; break; // 90° CW
                        case 2: rx = -x; ry = -y; break; // 180°
                        case 3: rx = -y; ry = x;  break; // 270° CW
                        default: rx = x; ry = y; break;
                    }

                    if (rx < minX) minX = rx;
                    if (rx > maxX) maxX = rx;
                    if (ry < minY) minY = ry;
                    if (ry > maxY) maxY = ry;
                }

                int w = (int)(maxX - minX + 1);
                int h = (int)(maxY - minY + 1);
                long long area = 1LL * w * h;

                if (first ||
                    area < bestArea ||
                    (area == bestArea && max(w, h) < max(bestW, bestH)) ||
                    (area == bestArea && max(w, h) == max(bestW, bestH) && w < bestW) ||
                    (area == bestArea && max(w, h) == max(bestW, bestH) && w == bestW && h < bestH)) {
                    first = false;
                    bestArea = area;
                    bestW = w;
                    bestH = h;
                    bestMinX = minX;
                    bestMinY = minY;
                    bestR = R;
                    bestF = F;
                }
            }
        }

        polys[i].bestR = bestR;
        polys[i].bestF = bestF;
        polys[i].minX = bestMinX;
        polys[i].minY = bestMinY;
        polys[i].width = bestW;
        polys[i].height = bestH;
        polys[i].boxArea = bestArea;

        totalBoxArea += bestArea;
        if (bestW > maxWidthPiece) maxWidthPiece = bestW;
        if (bestH > maxHeightPiece) maxHeightPiece = bestH;
    }

    if (totalBoxArea <= 0) {
        // Degenerate, but constraints guarantee at least one cell
        cout << 1 << " " << 1 << "\n";
        for (int i = 0; i < n; ++i) {
            cout << 0 << " " << 0 << " " << 0 << " " << 0 << "\n";
        }
        return 0;
    }

    // Determine target row width based on total bounding-box area
    long long ta = totalBoxArea;
    int width_limit = (int)std::sqrt((long double)ta);
    if (1LL * width_limit * width_limit < ta) ++width_limit;
    if (width_limit < 1) width_limit = 1;
    if (width_limit < maxWidthPiece) width_limit = maxWidthPiece;

    long long curX = 0, curY = 0;
    int rowHeight = 0;
    long long globalWidth = 0;

    for (int i = 0; i < n; ++i) {
        int w = polys[i].width;
        int h = polys[i].height;

        if (curX + w > width_limit && curX > 0) {
            curY += rowHeight;
            rowHeight = 0;
            curX = 0;
        }

        polys[i].transX = curX - polys[i].minX;
        polys[i].transY = curY - polys[i].minY;

        curX += w;
        if (h > rowHeight) rowHeight = h;
        if (curX > globalWidth) globalWidth = curX;
    }

    long long globalHeight = curY + rowHeight;
    if (globalHeight <= 0) globalHeight = 1;
    if (globalWidth <= 0) globalWidth = 1;

    long long side = max(globalWidth, globalHeight);
    if (side <= 0) side = 1;

    cout << side << " " << side << "\n";
    for (int i = 0; i < n; ++i) {
        cout << polys[i].transX << " " << polys[i].transY << " "
             << polys[i].bestR << " " << polys[i].bestF << "\n";
    }

    return 0;
}