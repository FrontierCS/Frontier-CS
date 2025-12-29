#include <bits/stdc++.h>
using namespace std;

struct Point {
    int x, y;
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);
    int N;
    cin >> N;
    vector<Point> macks(N), sards(N);
    for (int i = 0; i < N; i++) {
        int x, y;
        cin >> x >> y;
        macks[i] = {x, y};
    }
    for (int i = 0; i < N; i++) {
        int x, y;
        cin >> x >> y;
        sards[i] = {x, y};
    }
    const int MAXY = 100005;
    vector<int> ft(MAXY + 1, 0);
    auto update = [&](int pos, int val) {
        for (; pos <= MAXY; pos += pos & -pos) ft[pos] += val;
    };
    auto get_prefix = [&](int pos) -> int {
        int sum = 0;
        for (; pos > 0; pos -= pos & -pos) sum += ft[pos];
        return sum;
    };
    auto get_range = [&](int l, int r) -> int {
        if (l > r) return 0;
        return get_prefix(r) - get_prefix(l - 1);
    };
    int best_score = INT_MIN;
    int best_xl = 0, best_xr = 0, best_yb = 0, best_yt = 0;
    vector<int> added;
    // First sweep: sort by x, fenwick on y
    {
        auto cmp = [](const Point& a, const Point& b) { return a.x < b.x; };
        sort(macks.begin(), macks.end(), cmp);
        sort(sards.begin(), sards.end(), cmp);
        added.clear();
        for (int L = 0; L < N; L++) {
            added.clear();
            auto it = lower_bound(sards.begin(), sards.end(), macks[L].x, [](const Point& p, int val) { return p.x < val; });
            int ptr = it - sards.begin();
            int cur_yb = macks[L].y;
            int cur_yt = macks[L].y;
            while (ptr < N && sards[ptr].x <= macks[L].x) {
                int yy = sards[ptr].y + 1;
                update(yy, 1);
                added.push_back(yy);
                ptr++;
            }
            int aa = 1;
            int bb = get_range(cur_yb + 1, cur_yt + 1);
            int sc = aa - bb;
            if (sc > best_score) {
                best_score = sc;
                best_xl = macks[L].x;
                best_xr = macks[L].x;
                best_yb = cur_yb;
                best_yt = cur_yt;
            }
            for (int R = L + 1; R < N; R++) {
                cur_yb = min(cur_yb, macks[R].y);
                cur_yt = max(cur_yt, macks[R].y);
                aa = R - L + 1;
                while (ptr < N && sards[ptr].x <= macks[R].x) {
                    int yy = sards[ptr].y + 1;
                    update(yy, 1);
                    added.push_back(yy);
                    ptr++;
                }
                bb = get_range(cur_yb + 1, cur_yt + 1);
                sc = aa - bb;
                if (sc > best_score) {
                    best_score = sc;
                    best_xl = macks[L].x;
                    best_xr = macks[R].x;
                    best_yb = cur_yb;
                    best_yt = cur_yt;
                }
            }
            for (int pos : added) {
                update(pos, -1);
            }
        }
    }
    // Second sweep: sort by y, fenwick on x
    {
        auto cmp = [](const Point& a, const Point& b) { return a.y < b.y; };
        sort(macks.begin(), macks.end(), cmp);
        sort(sards.begin(), sards.end(), cmp);
        added.clear();
        for (int L = 0; L < N; L++) {
            added.clear();
            auto it = lower_bound(sards.begin(), sards.end(), macks[L].y, [](const Point& p, int val) { return p.y < val; });
            int ptr = it - sards.begin();
            int cur_minx = macks[L].x;
            int cur_maxx = macks[L].x;
            while (ptr < N && sards[ptr].y <= macks[L].y) {
                int yy = sards[ptr].x + 1;
                update(yy, 1);
                added.push_back(yy);
                ptr++;
            }
            int aa = 1;
            int bb = get_range(cur_minx + 1, cur_maxx + 1);
            int sc = aa - bb;
            if (sc > best_score) {
                best_score = sc;
                best_xl = cur_minx;
                best_xr = cur_maxx;
                best_yb = macks[L].y;
                best_yt = macks[L].y;
            }
            for (int R = L + 1; R < N; R++) {
                cur_minx = min(cur_minx, macks[R].x);
                cur_maxx = max(cur_maxx, macks[R].x);
                aa = R - L + 1;
                while (ptr < N && sards[ptr].y <= macks[R].y) {
                    int yy = sards[ptr].x + 1;
                    update(yy, 1);
                    added.push_back(yy);
                    ptr++;
                }
                bb = get_range(cur_minx + 1, cur_maxx + 1);
                sc = aa - bb;
                if (sc > best_score) {
                    best_score = sc;
                    best_xl = cur_minx;
                    best_xr = cur_maxx;
                    best_yb = macks[L].y;
                    best_yt = macks[R].y;
                }
            }
            for (int pos : added) {
                update(pos, -1);
            }
        }
    }
    // Now construct polygon
    int xl = best_xl;
    int xr = best_xr;
    int yb_ = best_yb;
    int yt_ = best_yt;
    auto get_small = [&](int px, int py) -> vector<pair<int, int>> {
        if (px < 100000 && py < 100000) {
            return {{px, py}, {px + 1, py}, {px + 1, py + 1}, {px, py + 1}};
        } else if (px > 0 && py < 100000) {
            return {{px, py}, {px - 1, py}, {px - 1, py + 1}, {px, py + 1}};
        } else if (px < 100000 && py > 0) {
            return {{px, py}, {px + 1, py}, {px + 1, py - 1}, {px, py - 1}};
        } else {
            return {{px, py}, {px - 1, py}, {px - 1, py - 1}, {px, py - 1}};
        }
    };
    vector<pair<int, int>> verts;
    bool is_single = (xl == xr && yb_ == yt_);
    if (is_single) {
        verts = get_small(xl, yb_);
    } else {
        if (xl == xr) {
            bool go_right = (xl < 100000);
            int xl2 = go_right ? xl : xl - 1;
            int xr2 = go_right ? xl + 1 : xl;
            xl = xl2;
            xr = xr2;
        }
        if (yb_ == yt_) {
            bool go_up = (yb_ < 100000);
            int yb2 = go_up ? yb_ : yb_ - 1;
            int yt2 = go_up ? yb_ + 1 : yb_;
            yb_ = yb2;
            yt_ = yt2;
        }
        verts = {{xl, yb_}, {xr, yb_}, {xr, yt_}, {xl, yt_}};
    }
    cout << 4 << '\n';
    for (auto [a, b] : verts) {
        cout << a << ' ' << b << '\n';
    }
}