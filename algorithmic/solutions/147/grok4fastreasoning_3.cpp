#include <bits/stdc++.h>
using namespace std;

struct Company {
    int x, y, r, idx;
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n;
    cin >> n;
    vector<Company> comp(n);
    for (int i = 0; i < n; i++) {
        cin >> comp[i].x >> comp[i].y >> comp[i].r;
        comp[i].idx = i;
    }
    sort(comp.begin(), comp.end(), [](const Company& a, const Company& b) {
        return a.y < b.y;
    });
    vector<double> ideal(n + 1, 0.0);
    for (int i = 1; i <= n; i++) {
        ideal[i] = ideal[i - 1] + (double)comp[i - 1].r / 10000.0;
    }
    vector<int> ends(n + 1);
    ends[0] = 0;
    for (int k = 1; k < n; k++) {
        int lower = comp[k - 1].y + 1;
        int upper = comp[k].y;
        double idl = ideal[k];
        double pos_d = round(idl);
        int pos = (int)pos_d;
        pos = max(lower, min(upper, pos));
        ends[k] = pos;
    }
    ends[n] = 10000;
    vector<int> aa(n), bb(n), cc(n), dd(n);
    for (int si = 0; si < n; si++) {
        int orig = comp[si].idx;
        int bbb = ends[si];
        int ddd = ends[si + 1];
        aa[orig] = 0;
        bb[orig] = bbb;
        cc[orig] = 10000;
        dd[orig] = ddd;
    }
    for (int i = 0; i < n; i++) {
        cout << aa[i] << " " << bb[i] << " " << cc[i] << " " << dd[i] << "\n";
    }
    return 0;
}