#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n;
    if (!(cin >> n)) return 0;
    struct Piece {
        long long minx, miny, maxx, maxy;
        long long w, h;
    };
    vector<Piece> pieces(n);
    for (int i = 0; i < n; ++i) {
        int k; 
        cin >> k;
        long long minx = LLONG_MAX, miny = LLONG_MAX, maxx = LLONG_MIN, maxy = LLONG_MIN;
        for (int j = 0; j < k; ++j) {
            long long x, y; 
            cin >> x >> y;
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
    
    long long W = 0, H = 0;
    for (int i = 0; i < n; ++i) {
        W += pieces[i].w;
        H = max(H, pieces[i].h);
    }
    
    cout << W << " " << H << "\n";
    long long curX = 0;
    for (int i = 0; i < n; ++i) {
        long long X = curX - pieces[i].minx;
        long long Y = -pieces[i].miny;
        cout << X << " " << Y << " 0 0\n";
        curX += pieces[i].w;
    }
    return 0;
}