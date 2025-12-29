#include <bits/stdc++.h>
using namespace std;

struct Poly {
    vector<pair<int, int>> cells;
    int bb_w, bb_h;
    int chosen_r, chosen_f;
};

vector<pair<int, int>> get_key(vector<pair<int, int>> v) {
    sort(v.begin(), v.end(), [](const pair<int, int>& a, const pair<int, int>& b) {
        if (a.first != b.first) return a.first < b.first;
        return a.second < b.second;
    });
    return v;
}

void prepare(int n, const vector<int>& best_idxs, const vector<vector<vector<pair<int, int>>>>& all_all_shapes, const vector<int>& ks, bool is_flat, vector<Poly>& polys, vector<pair<int, int>>& item_hs, vector<int>& order_out, int& max_pw_out) {
    int max_pw = 0;
    vector<pair<int, int>> item_hs_local(n);
    for (int i = 0; i < n; i++) {
        int idx = best_idxs[i];
        auto cells0 = all_all_shapes[i][idx];
        int k = ks[i];
        int ow = 0, oh = 0;
        for (auto p : cells0) {
            ow = max(ow, p.first + 1);
            oh = max(oh, p.second + 1);
        }
        bool need_swap = is_flat ? (oh > ow) : (oh < ow);
        vector<pair<int, int>> cells = cells0;
        int cf = idx / 4;
        int cr = idx % 4;
        int pw, ph;
        if (need_swap) {
            vector<pair<int, int>> sw(k);
            int mx2 = INT_MAX, my2 = INT_MAX;
            for (int j = 0; j < k; j++) {
                int x = cells0[j].first;
                int y = cells0[j].second;
                int nx = y;
                int ny = -x;
                sw[j] = {nx, ny};
                mx2 = min(mx2, nx);
                my2 = min(my2, ny);
            }
            for (int j = 0; j < k; j++) {
                sw[j].first -= mx2;
                sw[j].second -= my2;
            }
            auto key_sw = get_key(sw);
            bool found = false;
            for (int ff = 0; ff < 2 && !found; ff++) {
                for (int rr = 0; rr < 4; rr++) {
                    int idd = ff * 4 + rr;
                    if (get_key(all_all_shapes[i][idd]) == key_sw) {
                        cf = ff;
                        cr = rr;
                        found = true;
                        break;
                    }
                }
            }
            assert(found);
            cells = sw;
            ph = ow;
            pw = oh;
        } else {
            ph = oh;
            pw = ow;
        }
        polys[i].cells = cells;
        polys[i].bb_w = pw;
        polys[i].bb_h = ph;
        polys[i].chosen_f = cf;
        polys[i].chosen_r = cr;
        item_hs_local[i] = {ph, i};
        max_pw = max(max_pw, pw);
    }
    vector<int> order(n);
    iota(order.begin(), order.end(), 0);
    sort(order.begin(), order.end(), [&](int a, int b) {
        if (item_hs_local[a].first != item_hs_local[b].first) return item_hs_local[a].first > item_hs_local[b].first;
        return item_hs_local[a].second < item_hs_local[b].second;
    });
    item_hs = move(item_hs_local);
    order_out = move(order);
    max_pw_out = max_pw;
}

pair<int, int> compute_best_W_H(int n, int W, const vector<Poly>& polys, const vector<int>& order, long long total_S) {
    int ba = INT_MAX;
    int bw = -1;
    int bh = -1;
    double ss = sqrt(total_S);
    int minw = 1;
    for (auto& p : polys) minw = max(minw, p.bb_w);
    int start_trial = max(minw, (int)(ss * 0.5));
    int end_trial = (int)(ss * 2.0) + 100;
    end_trial = max(end_trial, minw);
    for (int trial = start_trial; trial <= end_trial; trial++) {
        int curr_x = 0;
        int level_hh = 0;
        int total_hh = 0;
        bool valid = true;
        for (int j = 0; j < n && valid; j++) {
            int ii = order[j];
            int ih = polys[ii].bb_h;
            int iw = polys[ii].bb_w;
            if (iw > trial) {
                valid = false;
                continue;
            }
            bool can_place = (curr_x + iw <= trial) && (level_hh == 0 || ih <= level_hh);
            if (can_place) {
                curr_x += iw;
                if (level_hh == 0) level_hh = ih;
            } else {
                total_hh += level_hh;
                level_hh = ih;
                curr_x = iw;
            }
        }
        total_hh += level_hh;
        if (!valid) continue;
        int this_H = total_hh;
        int area = trial * this_H;
        if (area < ba || (area == ba && this_H < bh) || (area == ba && this_H == bh && trial < bw)) {
            ba = area;
            bw = trial;
            bh = this_H;
        }
    }
    if (bw == -1) {
        // fallback large
        bw = (int)ceil(sqrt(total_S)) * 2;
        bh = (int)ceil(total_S * 1.0 / bw) * 2;
    }
    return {bw, bh};
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n;
    cin >> n;
    vector<int> ks(n);
    vector<vector<pair<int, int>>> raws(n);
    long long total_S = 0;
    for (int i = 0; i < n; i++) {
        int k;
        cin >> k;
        ks[i] = k;
        total_S += k;
        vector<pair<int, int>> raw(k);
        int minx = INT_MAX, miny = INT_MAX;
        for (int j = 0; j < k; j++) {
            int x, y;
            cin >> x >> y;
            raw[j] = {x, y};
            minx = min(minx, x);
            miny = min(miny, y);
        }
        for (auto& p : raw) {
            p.first -= minx;
            p.second -= miny;
        }
        raws[i] = raw;
    }
    vector<vector<vector<pair<int, int>>>> all_all_shapes(n);
    vector<int> best_idxs(n, -1);
    for (int i = 0; i < n; i++) {
        auto& raw = raws[i];
        int k = ks[i];
        auto& all_shapes = all_all_shapes[i];
        all_shapes.resize(8);
        int best_a = INT_MAX;
        int best_m = INT_MAX;
        int best_s = INT_MAX;
        int bidx = -1;
        for (int f = 0; f < 2; f++) {
            for (int r = 0; r < 4; r++) {
                int idx = f * 4 + r;
                vector<pair<int, int>> shape(k);
                int mx = INT_MAX, my = INT_MAX, Mx = INT_MIN, My = INT_MIN;
                for (int j = 0; j < k; j++) {
                    int x = raw[j].first, y = raw[j].second;
                    int xx = x, yy = y;
                    if (f) xx = -xx;
                    for (int t = 0; t < r; t++) {
                        int nx = yy;
                        int ny = -xx;
                        xx = nx;
                        yy = ny;
                    }
                    shape[j] = {xx, yy};
                    mx = min(mx, xx);
                    my = min(my, yy);
                    Mx = max(Mx, xx);
                    My = max(My, yy);
                }
                for (int j = 0; j < k; j++) {
                    shape[j].first -= mx;
                    shape[j].second -= my;
                }
                all_shapes[idx] = shape;
                int tw = Mx - mx + 1;
                int th = My - my + 1;
                int area = tw * th;
                int md = max(tw, th);
                int sd = tw + th;
                if (area < best_a || (area == best_a && md < best_m) || (area == best_a && md == best_m && sd < best_s)) {
                    best_a = area;
                    best_m = md;
                    best_s = sd;
                    bidx = idx;
                }
            }
        }
        best_idxs[i] = bidx;
    }
    long long best_overall_area = LLONG_MAX;
    int best_overall_W = -1;
    int best_overall_H = -1;
    int best_mode = -1;
    // mode 0: flat
    {
        vector<Poly> polys0(n);
        vector<pair<int, int>> item_hs0(n);
        vector<int> order0(n);
        int max_pw0;
        prepare(n, best_idxs, all_all_shapes, ks, true, polys0, item_hs0, order0, max_pw0);
        auto [w0, h0] = compute_best_W_H(n, 0, polys0, order0, total_S);
        long long area0 = (long long)w0 * h0;
        if (area0 < best_overall_area || (area0 == best_overall_area && h0 < best_overall_H) || (area0 == best_overall_area && h0 == best_overall_H && w0 < best_overall_W)) {
            best_overall_area = area0;
            best_overall_W = w0;
            best_overall_H = h0;
            best_mode = 0;
        }
    }
    // mode 1: tall
    {
        vector<Poly> polys1(n);
        vector<pair<int, int>> item_hs1(n);
        vector<int> order1(n);
        int max_pw1;
        prepare(n, best_idxs, all_all_shapes, ks, false, polys1, item_hs1, order1, max_pw1);
        auto [w1, h1] = compute_best_W_H(n, 0, polys1, order1, total_S);
        long long area1 = (long long)w1 * h1;
        if (area1 < best_overall_area || (area1 == best_overall_area && h1 < best_overall_H) || (area1 == best_overall_area && h1 == best_overall_H && w1 < best_overall_W)) {
            best_overall_area = area1;
            best_overall_W = w1;
            best_overall_H = h1;
            best_mode = 1;
        }
    }
    // now final preparation and placement
    vector<Poly> polys(n);
    vector<pair<int, int>> dummy_ihs(n);
    vector<int> order(n);
    int dummy_max;
    prepare(n, best_idxs, all_all_shapes, ks, best_mode == 0, polys, dummy_ihs, order, dummy_max);
    int W = best_overall_W;
    int H = best_overall_H;
    // simulate placement
    int curr_x = 0;
    int curr_y = 0;
    int level_hh = 0;
    vector<pair<int, int>> positions(n);
    for (size_t j = 0; j < order.size(); ++j) {
        int ii = order[j];
        int ih = polys[ii].bb_h;
        int iw = polys[ii].bb_w;
        int px, py;
        bool can_place = (curr_x + iw <= W) && (level_hh == 0 || ih <= level_hh);
        if (can_place) {
            px = curr_x;
            py = curr_y;
            curr_x += iw;
            if (level_hh == 0) level_hh = ih;
        } else {
            if (level_hh > 0) curr_y += level_hh;
            level_hh = ih;
            px = 0;
            py = curr_y;
            curr_x = iw;
        }
        positions[ii] = {px, py};
    }
    // output
    cout << W << " " << H << "\n";
    for (int i = 0; i < n; i++) {
        auto [X, Y] = positions[i];
        int R = polys[i].chosen_r;
        int F = polys[i].chosen_f;
        cout << X << " " << Y << " " << R << " " << F << "\n";
    }
    return 0;
}