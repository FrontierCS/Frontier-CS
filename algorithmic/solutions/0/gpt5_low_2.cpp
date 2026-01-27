#include <bits/stdc++.h>
using namespace std;

struct Piece {
    int idx;
    int k;
    int minx, miny, maxx, maxy;
    int w, h;
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n;
    if(!(cin >> n)) return 0;
    vector<vector<pair<int,int>>> cells(n);
    vector<Piece> pieces(n);
    long long total_box_area = 0;
    int maxw = 0, maxh = 0;
    for (int i = 0; i < n; ++i) {
        int k; cin >> k;
        cells[i].resize(k);
        int minx = INT_MAX, miny = INT_MAX, maxx = INT_MIN, maxy = INT_MIN;
        for (int j = 0; j < k; ++j) {
            int x, y; cin >> x >> y;
            cells[i][j] = {x, y};
            minx = min(minx, x);
            miny = min(miny, y);
            maxx = max(maxx, x);
            maxy = max(maxy, y);
        }
        int w = maxx - minx + 1;
        int h = maxy - miny + 1;
        pieces[i] = {i, k, minx, miny, maxx, maxy, w, h};
        total_box_area += 1LL * w * h;
        maxw = max(maxw, w);
        maxh = max(maxh, h);
    }
    
    // Sort pieces by height then width descending to improve shelf packing
    vector<int> order(n);
    iota(order.begin(), order.end(), 0);
    sort(order.begin(), order.end(), [&](int a, int b){
        if (pieces[a].h != pieces[b].h) return pieces[a].h > pieces[b].h;
        if (pieces[a].w != pieces[b].w) return pieces[a].w > pieces[b].w;
        return pieces[a].idx < pieces[b].idx;
    });
    
    auto try_pack = [&](int S, vector<pair<int,int>>& pos)->bool{
        long long x = 0, y = 0;
        int shelfH = 0;
        pos.assign(n, {0,0});
        for (int oi = 0; oi < n; ++oi) {
            int id = order[oi];
            int w = pieces[id].w;
            int h = pieces[id].h;
            if (w > S || h > S) return false;
            if (x + w > S) {
                y += shelfH;
                x = 0;
                shelfH = 0;
            }
            if (y + h > S) return false;
            pos[id] = {(int)x, (int)y};
            x += w;
            shelfH = max(shelfH, h);
        }
        // final height y + shelfH <= S ensured by checks
        return true;
    };
    
    // Initial S
    int S = max({maxw, maxh, (int)ceil(sqrt((long double)max(1LL, total_box_area)))});
    S = max(S, 1);
    vector<pair<int,int>> pos;
    // Increase S until pack succeeds
    int iters = 0;
    while (!try_pack(S, pos)) {
        // Grow S
        S = max(S * 2, S + 1);
        if (++iters > 60) { // safety
            break;
        }
    }
    
    // Output W and H as a square to satisfy potential W=H requirement
    int W = S, H = S;
    cout << W << " " << H << "\n";
    for (int i = 0; i < n; ++i) {
        int X = pos[i].first - pieces[i].minx;
        int Y = pos[i].second - pieces[i].miny;
        int R = 0;
        int F = 0;
        cout << X << " " << Y << " " << R << " " << F << "\n";
    }
    return 0;
}