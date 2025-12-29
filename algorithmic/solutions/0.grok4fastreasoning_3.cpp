#include <bits/stdc++.h>
using namespace std;

struct Orient {
    int f, r, w, h, minx, miny;
    bool valid;
};

Orient compute_best(const vector<pair<int, int>>& cells, int S) {
    Orient res;
    res.valid = false;
    int best_h = INT_MAX;
    int best_w_for_h = -1;
    for (int f = 0; f < 2; f++) {
        for (int rr = 0; rr < 4; rr++) {
            int min_tx = INT_MAX, max_tx = INT_MIN;
            int min_ty = INT_MAX, max_ty = INT_MIN;
            for (auto [x, y] : cells) {
                int tx = f ? -x : x;
                int ty = y;
                int rtx = tx, rty = ty;
                if (rr == 1) {
                    rtx = ty;
                    rty = -tx;
                } else if (rr == 2) {
                    rtx = -tx;
                    rty = -ty;
                } else if (rr == 3) {
                    rtx = -ty;
                    rty = tx;
                }
                min_tx = min(min_tx, rtx);
                max_tx = max(max_tx, rtx);
                min_ty = min(min_ty, rty);
                max_ty = max(max_ty, rty);
            }
            int cw = max_tx - min_tx + 1;
            int ch = max_ty - min_ty + 1;
            if (cw > S || ch > S) continue;
            bool better = (ch < best_h) || (ch == best_h && cw > best_w_for_h);
            if (better) {
                best_h = ch;
                best_w_for_h = cw;
                res.f = f;
                res.r = rr;
                res.minx = min_tx;
                res.miny = min_ty;
                res.w = cw;
                res.h = ch;
                res.valid = true;
            }
        }
    }
    return res;
}

int get_packed_height(int S, const vector<vector<pair<int, int>>>& polys) {
    int nn = polys.size();
    vector<pair<int, int>> rects(nn);
    for (int i = 0; i < nn; i++) {
        Orient bo = compute_best(polys[i], S);
        if (!bo.valid) return INT_MAX;
        rects[i] = {bo.w, bo.h};
    }
    sort(rects.begin(), rects.end(), [](const pair<int, int>& a, const pair<int, int>& b) {
        if (a.second != b.second) return a.second > b.second;
        return a.first > b.first;
    });
    int shelf_hh = 0;
    int cur_xx = 0;
    int tot_hh = 0;
    for (auto& p : rects) {
        int ww = p.first, hh = p.second;
        if (cur_xx + ww <= S) {
            cur_xx += ww;
            shelf_hh = max(shelf_hh, hh);
        } else {
            tot_hh += shelf_hh;
            shelf_hh = hh;
            cur_xx = ww;
        }
    }
    tot_hh += shelf_hh;
    return tot_hh;
}

struct Piece2 {
    int idx, w, h, f, r, minx, miny;
};

void compute_placement(int S, const vector<vector<pair<int, int>>>& polys, vector<int>& Xs, vector<int>& Ys, vector<int>& Rs, vector<int>& Fs) {
    int nn = polys.size();
    vector<Orient> bests(nn);
    for (int i = 0; i < nn; i++) {
        Orient bo = compute_best(polys[i], S);
        bests[i] = bo;
    }
    vector<Piece2> items(nn);
    for (int i = 0; i < nn; i++) {
        items[i].idx = i;
        items[i].w = bests[i].w;
        items[i].h = bests[i].h;
        items[i].f = bests[i].f;
        items[i].r = bests[i].r;
        items[i].minx = bests[i].minx;
        items[i].miny = bests[i].miny;
    }
    sort(items.begin(), items.end(), [](const Piece2& a, const Piece2& b) {
        if (a.h != b.h) return a.h > b.h;
        return a.w > b.w;
    });
    int shelf_yy = 0;
    int shelf_hh = 0;
    int cur_xx = 0;
    for (auto& item : items) {
        int i = item.idx;
        int px, py;
        if (cur_xx + item.w <= S) {
            px = cur_xx;
            py = shelf_yy;
            cur_xx += item.w;
            shelf_hh = max(shelf_hh, item.h);
        } else {
            shelf_yy += shelf_hh;
            shelf_hh = item.h;
            cur_xx = item.w;
            px = 0;
            py = shelf_yy;
        }
        Xs[i] = px - item.minx;
        Ys[i] = py - item.miny;
        Rs[i] = item.r;
        Fs[i] = item.f;
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n;
    cin >> n;
    vector<vector<pair<int, int>>> polys(n);
    int total_k = 0;
    for (int i = 0; i < n; i++) {
        int k;
        cin >> k;
        total_k += k;
        polys[i].resize(k);
        for (int j = 0; j < k; j++) {
            cin >> polys[i][j].first >> polys[i][j].second;
        }
    }
    int low = (total_k == 0 ? 0 : (int)ceil(sqrt(total_k * 1.0)));
    int high = total_k;
    while (low < high) {
        int mid = low + (high - low) / 2;
        int ph = get_packed_height(mid, polys);
        if (ph <= mid) {
            high = mid;
        } else {
            low = mid + 1;
        }
    }
    int S = low;
    vector<int> Xs(n), Ys(n), Rs(n), Fs(n);
    compute_placement(S, polys, Xs, Ys, Rs, Fs);
    cout << S << " " << S << "\n";
    for (int i = 0; i < n; i++) {
        cout << Xs[i] << " " << Ys[i] << " " << Rs[i] << " " << Fs[i] << "\n";
    }
    return 0;
}