#include <iostream>
#include <cstdlib>
using namespace std;

typedef long long ll;

ll n;

int query(ll x, ll y) {
    cout << x << " " << y << endl;
    cout.flush();
    int r;
    cin >> r;
    if (r == 0) {
        exit(0); // found, terminate immediately
    }
    return r;
}

void solve(ll la, ll ra, ll lb, ll rb) {
    if (la > ra || lb > rb) return; // empty interval, should not happen
    if (la == ra && lb == rb) {
        query(la, lb); // this must be the answer
        return;
    }
    ll x = (la + ra) / 2;
    ll y = (lb + rb) / 2;
    int r = query(x, y);
    if (r == 1) {
        solve(x + 1, ra, lb, rb);
    } else if (r == 2) {
        solve(la, ra, y + 1, rb);
    } else if (r == 3) {
        // try left part
        if (x - 1 >= la) {
            solve(la, x - 1, lb, rb);
        }
        // if not found, try bottom part
        if (y - 1 >= lb) {
            solve(x, ra, lb, y - 1);
        }
    }
}

int main() {
    cin >> n;
    solve(1, n, 1, n);
    return 0;
}