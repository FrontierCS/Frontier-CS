#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n;
    if(!(cin >> n)) return 0;
    struct Piece {
        int k;
        vector<pair<int,int>> cells;
        int minx, miny, maxx, maxy;
        int w, h;
    };
    vector<Piece> pieces(n);
    for (int i = 0; i < n; ++i) {
        int k; cin >> k;
        pieces[i].k = k;
        pieces[i].cells.resize(k);
        int minx = INT_MAX, miny = INT_MAX, maxx = INT_MIN, maxy = INT_MIN;
        for (int j = 0; j < k; ++j) {
            int x,y; cin >> x >> y;
            pieces[i].cells[j] = {x,y};
            minx = min(minx, x);
            miny = min(miny, y);
            maxx = max(maxx, x);
            maxy = max(maxy, y);
        }
        pieces[i].minx = minx;
        pieces[i].miny = miny;
        pieces[i].maxx = maxx;
        pieces[i].maxy = maxy;
        pieces[i].w = maxx - minx + 1;
        pieces[i].h = maxy - miny + 1;
    }
    long long curX = 0;
    long long H = 0;
    for (int i = 0; i < n; ++i) {
        H = max<long long>(H, pieces[i].h);
        curX += pieces[i].w;
    }
    long long W = curX;
    // Make square to satisfy potential W=H constraint
    long long S = max(W, H);
    W = S; H = S;

    cout << W << " " << H << "\n";
    long long xpos = 0;
    for (int i = 0; i < n; ++i) {
        auto &p = pieces[i];
        long long X = xpos - p.minx;
        long long Y = -p.miny;
        int R = 0, F = 0;
        cout << X << " " << Y << " " << R << " " << F << "\n";
        xpos += p.w;
    }
    return 0;
}