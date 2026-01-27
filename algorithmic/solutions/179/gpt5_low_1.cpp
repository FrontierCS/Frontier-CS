#include <bits/stdc++.h>
#include <boost/multiprecision/cpp_int.hpp>

using namespace std;
using boost::multiprecision::cpp_int;

cpp_int parseBig(const string &s) {
    cpp_int x = 0;
    for (char c : s) {
        if (c >= '0' && c <= '9') {
            x *= 10;
            x += (c - '0');
        }
    }
    return x;
}

cpp_int abs_diff(const cpp_int &a, const cpp_int &b) {
    return (a >= b) ? (a - b) : (b - a);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n;
    string sW;
    if (!(cin >> n >> sW)) {
        return 0;
    }
    cpp_int W = parseBig(sW);
    vector<cpp_int> a(n);
    for (int i = 0; i < n; ++i) {
        string s; cin >> s;
        a[i] = parseBig(s);
    }

    // Greedy under-or-equal-to-W solution
    vector<int> idx(n);
    iota(idx.begin(), idx.end(), 0);
    sort(idx.begin(), idx.end(), [&](int i, int j){
        if (a[i] == a[j]) return i < j;
        return a[i] > a[j];
    });

    vector<int> pick_greedy(n, 0);
    cpp_int Sg = 0;
    for (int id : idx) {
        if (Sg + a[id] <= W) {
            Sg += a[id];
            pick_greedy[id] = 1;
        }
    }

    // Best single element (could exceed W if closer)
    int best_single_idx = 0;
    cpp_int best_single_diff = abs_diff(a[0], W);
    for (int i = 1; i < n; ++i) {
        cpp_int d = abs_diff(a[i], W);
        if (d < best_single_diff) {
            best_single_diff = d;
            best_single_idx = i;
        }
    }

    cpp_int diff_greedy = abs_diff(Sg, W);
    cpp_int diff_single = best_single_diff;

    vector<int> ans(n, 0);
    if (diff_single < diff_greedy) {
        ans[best_single_idx] = 1;
    } else {
        ans = pick_greedy;
    }

    for (int i = 0; i < n; ++i) {
        if (i) cout << ' ';
        cout << ans[i];
    }
    cout << '\n';
    return 0;
}