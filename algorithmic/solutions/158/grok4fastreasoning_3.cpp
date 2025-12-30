#include <bits/stdc++.h>
using namespace std;
typedef long long ll;

struct Point {
    ll x, y;
};

bool cmp_x(const Point& a, const Point& b) {
    return a.x < b.x || (a.x == b.x && a.y < b.y);
}

bool cmp_y(const Point& a, const Point& b) {
    return a.y < b.y || (a.y == b.y && a.x < b.x);
}

int main() {
    int N, K;
    cin >> N >> K;
    vector<int> a(11, 0);
    for (int d = 1; d <= 10; d++) cin >> a[d];
    vector<Point> points(N);
    for (int i = 0; i < N; i++) {
        cin >> points[i].x >> points[i].y;
    }
    double facts[11];
    facts[0] = 1.0;
    for (int i = 1; i <= 10; i++) facts[i] = facts[i - 1] * i;
    double max_score = -1.0;
    int best_v = 0, best_h = 0;
    for (int nv = 0; nv <= 100; nv++) {
        for (int nh = 0; nh <= 100 - nv; nh++) {
            int ev = min(nv, N - 1);
            int eh = min(nh, N - 1);
            long long nc = (ev + 1LL) * (eh + 1LL);
            if (nc == 0) continue;
            double lam = N * 1.0 / nc;
            double esc = 0.0;
            for (int d = 1; d <= 10; d++) {
                double pd = exp(-lam) * pow(lam, d) / facts[d];
                double bd = nc * pd;
                esc += min((double)a[d], bd);
            }
            if (esc > max_score) {
                max_score = esc;
                best_v = nv;
                best_h = nh;
            }
        }
    }
    int num_v = min(best_v, N - 1);
    int num_h = min(best_h, N - 1);
    // vertical cuts
    int total_slabs_v = num_v + 1;
    int qv = N / total_slabs_v;
    int rv = N % total_slabs_v;
    vector<int> slab_sizes_v(total_slabs_v, qv);
    for (int i = 0; i < rv; i++) slab_sizes_v[i]++;
    sort(points.begin(), points.end(), cmp_x);
    vector<ll> cut_x;
    int cum = 0;
    for (int s = 0; s < num_v; s++) {
        cum += slab_sizes_v[s];
        ll cx = points[cum - 1].x + 1;
        cut_x.push_back(cx);
    }
    // horizontal cuts
    int total_slabs_h = num_h + 1;
    int qh = N / total_slabs_h;
    int rh = N % total_slabs_h;
    vector<int> slab_sizes_h(total_slabs_h, qh);
    for (int i = 0; i < rh; i++) slab_sizes_h[i]++;
    sort(points.begin(), points.end(), cmp_y);
    vector<ll> cut_y;
    cum = 0;
    for (int s = 0; s < num_h; s++) {
        cum += slab_sizes_h[s];
        ll cy = points[cum - 1].y + 1;
        cut_y.push_back(cy);
    }
    int k = cut_x.size() + cut_y.size();
    cout << k << endl;
    ll BIG = 1000000000LL;
    for (ll cx : cut_x) {
        cout << cx << " " << -BIG << " " << cx << " " << BIG << endl;
    }
    for (ll cy : cut_y) {
        cout << -BIG << " " << cy << " " << BIG << " " << cy << endl;
    }
    return 0;
}