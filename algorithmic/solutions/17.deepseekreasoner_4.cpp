#include <iostream>
#include <cmath>
#include <algorithm>
using namespace std;

int query(int l, int r) {
    cout << "? " << l << " " << r << endl;
    int res;
    cin >> res;
    return res;
}

int find(int l, int r, int u) {
    if (l == r) return l;
    int len = r - l + 1;
    if (len == 2) {
        return (l == u) ? r : l;
    }
    if (len == 3) {
        int cand1, cand2;
        if (u == l) {
            cand1 = l+1;
            cand2 = l+2;
        } else if (u == l+1) {
            cand1 = l;
            cand2 = l+2;
        } else {
            cand1 = l;
            cand2 = l+1;
        }
        int adj = (abs(cand1 - u) == 1) ? cand1 : cand2;
        int v = query(min(u, adj), max(u, adj));
        if (v == u) return adj;
        else return (adj == cand1) ? cand2 : cand1;
    }
    int m = (l + r) / 2;
    if (u <= m) {
        int a = query(l, m);
        if (u == a) return find(l, m, a);
        else {
            int b = query(m+1, r);
            return find(m+1, r, b);
        }
    } else {
        int b = query(m+1, r);
        if (u == b) return find(m+1, r, b);
        else {
            int a = query(l, m);
            return find(l, m, a);
        }
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);
    int T;
    cin >> T;
    while (T--) {
        int n;
        cin >> n;
        int u = query(1, n);
        int ans = find(1, n, u);
        cout << "! " << ans << endl;
    }
    return 0;
}