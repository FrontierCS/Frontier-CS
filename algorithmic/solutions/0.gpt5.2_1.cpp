#include <bits/stdc++.h>
using namespace std;

using ll = long long;

struct Orientation {
    int R = 0;
    int F = 0;
    ll minx = 0, miny = 0;
    ll w = 0, h = 0;
};

struct Placement {
    ll X = 0, Y = 0;
    int R = 0, F = 0;
};

static inline pair<ll,ll> applyTransform(ll x, ll y, int F, int R){
    if (F) x = -x; // reflect across y-axis
    switch(R & 3){
        case 0: return {x, y};
        case 1: return {y, -x};
        case 2: return {-x, -y};
        default: return {-y, x};
    }
}

static inline ll ceil_sqrt_ll(ll x){
    if (x <= 0) return 0;
    ll r = (ll)floor(sqrt((long double)x));
    while (r*r < x) ++r;
    while (r > 0 && (r-1)*(r-1) >= x) --r;
    return r;
}

struct Piece {
    int k = 0;
    vector<pair<ll,ll>> cells;
    Orientation ori;
};

static pair<ll, vector<Placement>> packWithW(
    const vector<Piece>& pieces,
    const vector<int>& order,
    ll W
){
    int n = (int)pieces.size();
    vector<Placement> res(n);

    ll x = 0, y = 0, shelfH = 0;
    for (int idx : order){
        const auto &p = pieces[idx].ori;
        if (x + p.w > W){
            y += shelfH;
            x = 0;
            shelfH = 0;
        }
        ll placeX = x, placeY = y;

        Placement pl;
        pl.X = placeX - p.minx;
        pl.Y = placeY - p.miny;
        pl.R = p.R;
        pl.F = p.F;
        res[idx] = pl;

        x += p.w;
        shelfH = max(shelfH, p.h);
    }
    ll H = y + shelfH;
    return {H, std::move(res)};
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    cin >> n;
    vector<Piece> pieces(n);

    ll totalCells = 0;
    for (int i = 0; i < n; i++){
        int k;
        cin >> k;
        pieces[i].k = k;
        pieces[i].cells.resize(k);
        for (int j = 0; j < k; j++){
            ll x, y;
            cin >> x >> y;
            pieces[i].cells[j] = {x, y};
        }
        totalCells += k;
    }

    // Choose best orientation for each piece
    ll maxWidth = 1;
    ll sumBBoxArea = 0;
    for (int i = 0; i < n; i++){
        Orientation best;
        bool first = true;
        for (int F = 0; F <= 1; F++){
            for (int R = 0; R < 4; R++){
                ll minx = LLONG_MAX, miny = LLONG_MAX;
                ll maxx = LLONG_MIN, maxy = LLONG_MIN;
                for (auto [x, y] : pieces[i].cells){
                    auto [tx, ty] = applyTransform(x, y, F, R);
                    minx = min(minx, tx);
                    miny = min(miny, ty);
                    maxx = max(maxx, tx);
                    maxy = max(maxy, ty);
                }
                ll w = maxx - minx + 1;
                ll h = maxy - miny + 1;

                // metric: minimize max(w,h), then w, then h
                auto metric = tuple<ll,ll,ll>(max(w,h), w, h);
                if (first || metric < tuple<ll,ll,ll>(max(best.w,best.h), best.w, best.h)){
                    first = false;
                    best.R = R;
                    best.F = F;
                    best.minx = minx;
                    best.miny = miny;
                    best.w = w;
                    best.h = h;
                }
            }
        }
        pieces[i].ori = best;
        maxWidth = max(maxWidth, best.w);
        sumBBoxArea += best.w * best.h;
    }

    // Order pieces for packing
    vector<int> order(n);
    iota(order.begin(), order.end(), 0);
    sort(order.begin(), order.end(), [&](int a, int b){
        const auto &A = pieces[a].ori;
        const auto &B = pieces[b].ori;
        ll ma = max(A.w, A.h), mb = max(B.w, B.h);
        if (ma != mb) return ma > mb;
        if (A.h != B.h) return A.h > B.h;
        if (A.w != B.w) return A.w > B.w;
        return a < b;
    });

    ll target1 = max<ll>(1, ceil_sqrt_ll(totalCells));
    ll target2 = max<ll>(1, ceil_sqrt_ll(sumBBoxArea));
    ll baseTarget = max({target1, target2, maxWidth});

    vector<ll> candidates;
    candidates.reserve(64);
    auto addCand = [&](ll w){
        if (w < maxWidth) w = maxWidth;
        if (w < 1) w = 1;
        candidates.push_back(w);
    };

    addCand(maxWidth);
    addCand(maxWidth + 1);
    addCand(target1);
    addCand(target1 + 1);
    addCand(target2);
    addCand(target2 + 1);
    addCand(baseTarget);
    addCand(baseTarget + 1);

    const vector<long double> mults = {0.70L, 0.85L, 1.00L, 1.15L, 1.30L, 1.50L, 2.00L, 3.00L};
    for (auto m : mults){
        ll w = (ll)floor((long double)baseTarget * m + 0.5L);
        addCand(w);
    }

    sort(candidates.begin(), candidates.end());
    candidates.erase(unique(candidates.begin(), candidates.end()), candidates.end());

    // Try candidates, pick best by (side, H, W)
    ll bestW = -1, bestH = -1, bestSide = -1;
    vector<Placement> bestPlacement;

    for (ll W : candidates){
        auto [H, placement] = packWithW(pieces, order, W);
        ll side = max(W, H);
        if (bestSide == -1 || tuple<ll,ll,ll>(side, H, W) < tuple<ll,ll,ll>(bestSide, bestH, bestW)){
            bestSide = side;
            bestW = W;
            bestH = H;
            bestPlacement = std::move(placement);
        }
    }

    // Output square (as per statement's W=H line)
    ll side = bestSide;
    cout << side << " " << side << "\n";
    for (int i = 0; i < n; i++){
        cout << bestPlacement[i].X << " " << bestPlacement[i].Y << " " << bestPlacement[i].R << " " << bestPlacement[i].F << "\n";
    }
    return 0;
}