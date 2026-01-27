#include <bits/stdc++.h>
using namespace std;

struct Piece {
    vector<pair<int,int>> cells;
};

pair<long long,long long> transformPoint(long long x, long long y, int R, int F) {
    if (F) x = -x; // reflect across y-axis
    long long nx, ny;
    switch (R) {
        case 0: nx = x; ny = y; break;
        case 1: nx = y; ny = -x; break; // 90° cw
        case 2: nx = -x; ny = -y; break; // 180°
        case 3: nx = -y; ny = x; break; // 270° cw
        default: nx = x; ny = y; break;
    }
    return {nx, ny};
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n;
    if (!(cin >> n)) return 0;
    vector<Piece> pieces(n);
    for (int i = 0; i < n; ++i) {
        int k; cin >> k;
        pieces[i].cells.resize(k);
        for (int j = 0; j < k; ++j) {
            int x, y; cin >> x >> y;
            pieces[i].cells[j] = {x, y};
        }
    }

    struct Choice {
        int R, F;
        long long minx, miny;
        long long width, height;
    };
    vector<Choice> chosen(n);

    for (int i = 0; i < n; ++i) {
        long long bestW = LLONG_MAX, bestH = LLONG_MAX;
        int bestR = 0, bestF = 0;
        long long bestMinX = 0, bestMinY = 0;
        for (int F = 0; F <= 1; ++F) {
            for (int R = 0; R < 4; ++R) {
                long long minx = LLONG_MAX, miny = LLONG_MAX;
                long long maxx = LLONG_MIN, maxy = LLONG_MIN;
                for (auto &c : pieces[i].cells) {
                    auto p = transformPoint(c.first, c.second, R, F);
                    minx = min(minx, p.first);
                    miny = min(miny, p.second);
                    maxx = max(maxx, p.first);
                    maxy = max(maxy, p.second);
                }
                long long w = maxx - minx + 1;
                long long h = maxy - miny + 1;
                if (w < bestW || (w == bestW && h < bestH)) {
                    bestW = w; bestH = h;
                    bestR = R; bestF = F;
                    bestMinX = minx; bestMinY = miny;
                }
            }
        }
        chosen[i] = {bestR, bestF, bestMinX, bestMinY, bestW, bestH};
    }

    vector<long long> X(n), Y(n);
    long long curX = 0;
    long long maxH = 0;
    for (int i = 0; i < n; ++i) {
        X[i] = curX - chosen[i].minx;
        Y[i] = -chosen[i].miny;
        curX += chosen[i].width;
        if (chosen[i].height > maxH) maxH = chosen[i].height;
    }
    long long W = max(curX, maxH);
    long long H = W; // Make it square (to satisfy any potential W=H requirement)

    cout << W << " " << H << "\n";
    for (int i = 0; i < n; ++i) {
        cout << X[i] << " " << Y[i] << " " << chosen[i].R << " " << chosen[i].F << "\n";
    }
    return 0;
}