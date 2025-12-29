#include <bits/stdc++.h>
using namespace std;

typedef long long ll;

ll dc(ll a, ll b, ll nn) {
    ll dif = abs(a - b);
    return min(dif, nn - dif);
}

ll get_x(ll r, ll delta, ll nn) {
    ll base = r - 1;
    ll newbase = (base + delta % nn + nn) % nn;
    return newbase + 1;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(NULL);
    int T;
    cin >> T;
    for (int t = 0; t < T; t++) {
        ll n;
        cin >> n;
        ll third = n / 3;
        vector<ll> refs = {1LL, 1LL + third, 1LL + 2 * third};
        bool solved = false;
        for (ll this_r : refs) {
            if (solved) break;
            // binary search clockwise for smallest pos >=1 where < dc
            ll lo = 1, hi = n - 1;
            while (lo < hi) {
                ll mid = lo + (hi - lo) / 2;
                ll xx = get_x(this_r, mid, n);
                cout << "? " << this_r << " " << xx << endl;
                cout.flush();
                ll dis;
                cin >> dis;
                ll dcc = dc(this_r, xx, n);
                if (dis < dcc) {
                    hi = mid;
                } else {
                    lo = mid + 1;
                }
            }
            ll pos = lo;
            ll xx = get_x(this_r, pos, n);
            cout << "? " << this_r << " " << xx << endl;
            cout.flush();
            ll dis;
            cin >> dis;
            ll dcc = dc(this_r, xx, n);
            if (dis >= dcc) continue; // no reduced in clockwise for this r
            // found
            ll LL = xx;
            ll drl = dis;
            ll kk = drl - 1;
            if (kk < 0) continue;
            vector<ll> cands;
            ll zcw = get_x(this_r, kk, n);
            cands.push_back(zcw);
            ll zccw = get_x(this_r, -kk, n);
            if (zccw != zcw) cands.push_back(zccw);
            ll other = -1;
            for (ll zz : cands) {
                if (zz == LL) continue;
                cout << "? " << LL << " " << zz << endl;
                cout.flush();
                ll diz;
                cin >> diz;
                if (diz == 1) {
                    other = zz;
                    break;
                }
            }
            if (other == -1) continue;
            ll u = min(LL, other);
            ll v = max(LL, other);
            cout << "! " << u << " " << v << endl;
            cout.flush();
            int res;
            cin >> res;
            if (res == 1) {
                solved = true;
            } else {
                return 0;
            }
        }
        // if not solved, should not happen
        assert(solved);
    }
    return 0;
}