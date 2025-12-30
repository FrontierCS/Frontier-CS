#include <bits/stdc++.h>
using namespace std;
using ll = long long;
using i128 = __int128_t;

i128 area(ll la, ll ra, ll lb, ll rb) {
    return (i128)(ra - la + 1) * (rb - lb + 1);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    ll n;
    cin >> n;
    vector<array<ll, 4>> rects; // each: la, ra, lb, rb
    rects.push_back({1, n, 1, n});

    while (true) {
        // find rectangle with largest area
        int idx = 0;
        i128 max_a = 0;
        for (int i = 0; i < (int)rects.size(); ++i) {
            i128 a = area(rects[i][0], rects[i][1], rects[i][2], rects[i][3]);
            if (a > max_a) {
                max_a = a;
                idx = i;
            }
        }

        auto& r = rects[idx];
        ll x = (r[0] + r[1]) / 2;
        ll y = (r[2] + r[3]) / 2;

        cout << x << " " << y << endl;
        cout.flush();

        int resp;
        cin >> resp;
        if (resp == 0) {
            break;
        } else if (resp == 1) {
            ll new_la = x + 1;
            if (new_la <= r[1]) {
                rects[idx] = {new_la, r[1], r[2], r[3]};
            } else {
                rects.erase(rects.begin() + idx);
            }
        } else if (resp == 2) {
            ll new_lb = y + 1;
            if (new_lb <= r[3]) {
                rects[idx] = {r[0], r[1], new_lb, r[3]};
            } else {
                rects.erase(rects.begin() + idx);
            }
        } else if (resp == 3) {
            // split into two rectangles
            rects.erase(rects.begin() + idx);
            // R1: [la, x-1] × [lb, rb]
            if (x - 1 >= r[0]) {
                rects.push_back({r[0], x - 1, r[2], r[3]});
            }
            // R2: [la, ra] × [lb, y-1]
            if (y - 1 >= r[2]) {
                rects.push_back({r[0], r[1], r[2], y - 1});
            }
        }

        if (rects.empty()) {
            // Should never happen, but safeguard
            break;
        }
    }

    return 0;
}