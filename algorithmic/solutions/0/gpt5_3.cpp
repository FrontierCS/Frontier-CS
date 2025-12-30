#include <bits/stdc++.h>
using namespace std;

struct Piece {
    int k;
    vector<pair<int,int>> cells;
};

struct Choice {
    int F, R;
    int minx, miny, maxx, maxy;
    int w, h;
};

pair<int,int> apply_transform(int x, int y, int F, int R) {
    if (F) x = -x; // reflect across y-axis
    int nx = x, ny = y;
    switch (R % 4) {
        case 0: nx = x; ny = y; break;
        case 1: nx = y; ny = -x; break; // 90° CW
        case 2: nx = -x; ny = -y; break; // 180°
        case 3: nx = -y; ny = x; break; // 270° CW
    }
    return {nx, ny};
}

Choice evaluate_choice(const vector<pair<int,int>>& cells, int F, int R) {
    int minx = INT_MAX, miny = INT_MAX, maxx = INT_MIN, maxy = INT_MIN;
    for (auto &c : cells) {
        auto t = apply_transform(c.first, c.second, F, R);
        minx = min(minx, t.first);
        maxx = max(maxx, t.first);
        miny = min(miny, t.second);
        maxy = max(maxy, t.second);
    }
    Choice ch;
    ch.F = F; ch.R = R;
    ch.minx = minx; ch.maxx = maxx;
    ch.miny = miny; ch.maxy = maxy;
    ch.w = maxx - minx + 1;
    ch.h = maxy - miny + 1;
    return ch;
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

    vector<int> bestF(n, 0), bestR(n, 0);
    vector<int> minx(n, 0), miny(n, 0), w(n, 1), h(n, 1);

    for (int i = 0; i < n; ++i) {
        Choice best;
        bool has = false;
        for (int F = 0; F <= 1; ++F) {
            for (int R = 0; R < 4; ++R) {
                Choice ch = evaluate_choice(pieces[i].cells, F, R);
                if (!has || ch.w < best.w || (ch.w == best.w && ch.h < best.h) ||
                    (ch.w == best.w && ch.h == best.h && (F < best.F || (F == best.F && R < best.R)))) {
                    best = ch;
                    has = true;
                }
            }
        }
        bestF[i] = best.F;
        bestR[i] = best.R;
        minx[i] = best.minx;
        miny[i] = best.miny;
        w[i] = best.w;
        h[i] = best.h;
    }

    long long curX = 0;
    long long H = 0;
    for (int i = 0; i < n; ++i) H = max<long long>(H, h[i]);
    vector<long long> X(n), Y(n);
    for (int i = 0; i < n; ++i) {
        X[i] = curX - minx[i];
        Y[i] = - (long long)miny[i];
        curX += w[i];
    }
    long long W = curX;

    cout << W << " " << H << "\n";
    for (int i = 0; i < n; ++i) {
        cout << X[i] << " " << Y[i] << " " << bestR[i] << " " << bestF[i] << "\n";
    }
    return 0;
}