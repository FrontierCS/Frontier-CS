#include <bits/stdc++.h>
using namespace std;

pair<int, int> transform(int x, int y, int f, int r) {
    if (f) x = -x;
    int tx = x, ty = y;
    if (r == 0) {
        return {tx, ty};
    } else if (r == 1) {
        return {ty, -tx};
    } else if (r == 2) {
        return {-tx, -ty};
    } else {
        return {-ty, tx};
    }
}

struct Poly {
    int k;
    vector<pair<int, int>> cells;
};

struct Placement {
    int X, Y, R, F;
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    cin >> n;
    vector<Poly> polys(n);
    for (int i = 0; i < n; i++) {
        cin >> polys[i].k;
        polys[i].cells.resize(polys[i].k);
        for (int j = 0; j < polys[i].k; j++) {
            int x, y;
            cin >> x >> y;
            polys[i].cells[j] = {x, y};
        }
    }

    // Horizontal packing: minimize vertical span (h)
    vector<int> best_hh(n), best_ww(n), best_Fh(n), best_Rh(n);
    for (int i = 0; i < n; i++) {
        int min_h = INT_MAX / 2;
        int min_w = INT_MAX / 2;
        int bf = 0, br = 0;
        for (int f = 0; f < 2; f++) {
            for (int r = 0; r < 4; r++) {
                int mnx = INT_MAX / 2, mny = INT_MAX / 2;
                int mxx = -INT_MAX / 2, mxy = -INT_MAX / 2;
                for (auto [ox, oy] : polys[i].cells) {
                    auto [tx, ty] = transform(ox, oy, f, r);
                    mnx = min(mnx, tx);
                    mny = min(mny, ty);
                    mxx = max(mxx, tx);
                    mxy = max(mxy, ty);
                }
                int cw = mxx - mnx + 1;
                int ch = mxy - mny + 1;
                if (ch < min_h || (ch == min_h && cw < min_w)) {
                    min_h = ch;
                    min_w = cw;
                    bf = f;
                    br = r;
                }
            }
        }
        best_hh[i] = min_h;
        best_ww[i] = min_w;
        best_Fh[i] = bf;
        best_Rh[i] = br;
    }

    vector<int> order(n);
    iota(order.begin(), order.end(), 0);
    sort(order.begin(), order.end(), [&](int a, int b) {
        if (best_hh[a] != best_hh[b]) return best_hh[a] > best_hh[b];
        return a < b;
    });

    struct Shelf {
        int y, height, used;
    };
    vector<Shelf> shelves;
    int current_H = 0;
    int overall_W = 0;
    vector<Placement> pack1(n);
    for (int jj = 0; jj < n; jj++) {
        int i = order[jj];
        int h = best_hh[i];
        int w = best_ww[i];
        int R = best_Rh[i];
        int F = best_Fh[i];
        int mnx = INT_MAX / 2, mny = INT_MAX / 2;
        for (auto [ox, oy] : polys[i].cells) {
            auto [tx, ty] = transform(ox, oy, F, R);
            mnx = min(mnx, tx);
            mny = min(mny, ty);
        }
        int chosen_j = -1;
        for (int j = 0; j < (int)shelves.size(); j++) {
            if (shelves[j].height >= h) {
                chosen_j = j;
                break;
            }
        }
        int place_x, place_y;
        if (chosen_j == -1) {
            place_y = current_H;
            place_x = 0;
            shelves.push_back({current_H, h, w});
            current_H += h;
            overall_W = max(overall_W, w);
        } else {
            place_x = shelves[chosen_j].used;
            place_y = shelves[chosen_j].y;
            shelves[chosen_j].used += w;
            overall_W = max(overall_W, shelves[chosen_j].used);
        }
        int X = place_x - mnx;
        int Y = place_y - mny;
        pack1[i] = {X, Y, R, F};
    }

    // Vertical packing: minimize horizontal span (w)
    vector<int> best_wv(n), best_hv(n), best_Fv(n), best_Rv(n);
    for (int i = 0; i < n; i++) {
        int min_perp = INT_MAX / 2;
        int min_along = INT_MAX / 2;
        int bf = 0, br = 0;
        for (int f = 0; f < 2; f++) {
            for (int r = 0; r < 4; r++) {
                int mnx = INT_MAX / 2, mny = INT_MAX / 2;
                int mxx = -INT_MAX / 2, mxy = -INT_MAX / 2;
                for (auto [ox, oy] : polys[i].cells) {
                    auto [tx, ty] = transform(ox, oy, f, r);
                    mnx = min(mnx, tx);
                    mny = min(mny, ty);
                    mxx = max(mxx, tx);
                    mxy = max(mxy, ty);
                }
                int cw = mxx - mnx + 1;
                int ch = mxy - mny + 1;
                if (cw < min_perp || (cw == min_perp && ch < min_along)) {
                    min_perp = cw;
                    min_along = ch;
                    bf = f;
                    br = r;
                }
            }
        }
        best_wv[i] = min_perp;
        best_hv[i] = min_along;
        best_Fv[i] = bf;
        best_Rv[i] = br;
    }

    vector<int> order_v(n);
    iota(order_v.begin(), order_v.end(), 0);
    sort(order_v.begin(), order_v.end(), [&](int a, int b) {
        if (best_wv[a] != best_wv[b]) return best_wv[a] > best_wv[b];
        return a < b;
    });

    struct VShelf {
        int x, width, used_y;
    };
    vector<VShelf> vshelves;
    int current_Wv = 0;
    int overall_Hv = 0;
    vector<Placement> pack2(n);
    for (int jj = 0; jj < n; jj++) {
        int i = order_v[jj];
        int perp = best_wv[i];
        int along = best_hv[i];
        int R = best_Rv[i];
        int F = best_Fv[i];
        int mnx = INT_MAX / 2, mny = INT_MAX / 2;
        for (auto [ox, oy] : polys[i].cells) {
            auto [tx, ty] = transform(ox, oy, F, R);
            mnx = min(mnx, tx);
            mny = min(mny, ty);
        }
        int chosen_j = -1;
        for (int j = 0; j < (int)vshelves.size(); j++) {
            if (vshelves[j].width >= perp) {
                chosen_j = j;
                break;
            }
        }
        int place_x, place_y;
        if (chosen_j == -1) {
            place_x = current_Wv;
            place_y = 0;
            vshelves.push_back({current_Wv, perp, along});
            current_Wv += perp;
            overall_Hv = max(overall_Hv, along);
        } else {
            place_x = vshelves[chosen_j].x;
            place_y = vshelves[chosen_j].used_y;
            vshelves[chosen_j].used_y += along;
            overall_Hv = max(overall_Hv, vshelves[chosen_j].used_y);
        }
        int X = place_x - mnx;
        int Y = place_y - mny;
        pack2[i] = {X, Y, R, F};
    }

    long long area1 = 1LL * overall_W * current_H;
    long long area2 = 1LL * current_Wv * overall_Hv;
    bool use1 = (area1 < area2) ||
                (area1 == area2 && (current_H < overall_Hv ||
                 (current_H == overall_Hv && overall_W < current_Wv)));
    if (use1) {
        cout << overall_W << " " << current_H << "\n";
        for (int i = 0; i < n; i++) {
            auto p = pack1[i];
            cout << p.X << " " << p.Y << " " << p.R << " " << p.F << "\n";
        }
    } else {
        cout << current_Wv << " " << overall_Hv << "\n";
        for (int i = 0; i < n; i++) {
            auto p = pack2[i];
            cout << p.X << " " << p.Y << " " << p.R << " " << p.F << "\n";
        }
    }
    return 0;
}