#include <bits/stdc++.h>
using namespace std;

int n;
int queries = 0;
const int QUERY_LIMIT = 500;
map<pair<int, int>, int> cache;

int ask(int x, int y) {
    if (x == y) return 0;
    if (x > y) swap(x, y);
    auto it = cache.find({x, y});
    if (it != cache.end()) return it->second;
    cout << "? " << x << " " << y << endl;
    int d;
    cin >> d;
    queries++;
    cache[{x, y}] = d;
    return d;
}

void guess(int u, int v) {
    if (u > v) swap(u, v);
    cout << "! " << u << " " << v << endl;
    int r;
    cin >> r;
    if (r == -1) exit(0);
}

inline int mod_add(int a, int b, int n) {
    int res = (a - 1 + b) % n;
    if (res < 0) res += n;
    return res + 1;
}

int get_d(int i, int half) {
    int j = mod_add(i, half, n);
    return ask(i, j);
}

pair<int, int> ternary_search(int l, int r, int half) {
    while (r - l > 3) {
        int m1 = l + (r - l) / 3;
        int m2 = r - (r - l) / 3;
        int d1 = get_d(m1, half);
        int d2 = get_d(m2, half);
        if (d1 < d2) {
            r = m2 - 1;
        } else {
            l = m1 + 1;
        }
    }
    int best_i = l, best_d = get_d(l, half);
    for (int i = l + 1; i <= r; ++i) {
        int d = get_d(i, half);
        if (d < best_d) {
            best_d = d;
            best_i = i;
        }
    }
    return {best_i, best_d};
}

bool try_candidate(int x, int L) {
    if (L < 2 || L > n - 2) return false;
    int y1 = mod_add(x, L, n);
    int y2 = mod_add(x, -L, n);
    int d1 = ask(x, y1);
    if (d1 == 1 && L != 1 && L != n - 1) {
        guess(x, y1);
        return true;
    }
    int d2 = ask(x, y2);
    if (d2 == 1 && L != 1 && L != n - 1) {
        guess(x, y2);
        return true;
    }
    return false;
}

void solve() {
    cin >> n;
    queries = 0;
    cache.clear();
    int half = n / 2;  // floor(n/2)

    int l1 = 1, r1 = 1 + half;
    if (r1 > n) r1 = n;
    int l2 = 1 + half, r2 = n;
    if (l2 > n) l2 = n;

    auto [x1, d1] = ternary_search(l1, r1, half);
    auto [x2, d2] = ternary_search(l2, r2, half);

    int x, d_val;
    if (d1 <= d2) {
        x = x1;
        d_val = d1;
    } else {
        x = x2;
        d_val = d2;
    }

    int L = half + 1 - d_val;
    if (L < 2) L = 2;
    if (L > n - 2) L = n - 2;

    if (try_candidate(x, L)) return;

    for (int dx : {-1, 1}) {
        int nx = mod_add(x, dx, n);
        int nd = get_d(nx, half);
        int nL = half + 1 - nd;
        if (nL < 2 || nL > n - 2) continue;
        if (try_candidate(nx, nL)) return;
    }

    int ox = (d1 <= d2 ? x2 : x1);
    int od = (d1 <= d2 ? d2 : d1);
    L = half + 1 - od;
    if (L < 2) L = 2;
    if (L > n - 2) L = n - 2;
    if (try_candidate(ox, L)) return;

    for (int dx : {-1, 1}) {
        int nx = mod_add(ox, dx, n);
        int nd = get_d(nx, half);
        int nL = half + 1 - nd;
        if (nL < 2 || nL > n - 2) continue;
        if (try_candidate(nx, nL)) return;
    }

    // Should never reach here with a valid test case
    // As a fallback, guess arbitrarily (should not happen)
    guess(1, 2);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);
    int T;
    cin >> T;
    while (T--) {
        solve();
    }
    return 0;
}