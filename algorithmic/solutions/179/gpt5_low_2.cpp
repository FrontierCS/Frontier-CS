#include <bits/stdc++.h>
#include <boost/multiprecision/cpp_int.hpp>

using namespace std;
using boost::multiprecision::cpp_int;

static inline cpp_int parse_big(const string& s) {
    cpp_int x = 0;
    for (char c : s) {
        if (c >= '0' && c <= '9') {
            x *= 10;
            x += (c - '0');
        }
    }
    return x;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n;
    string Ws;
    if (!(cin >> n >> Ws)) {
        return 0;
    }
    cpp_int W = parse_big(Ws);
    vector<cpp_int> a(n);
    for (int i = 0; i < n; ++i) {
        string s; 
        cin >> s;
        a[i] = parse_big(s);
    }

    // Precompute orders
    vector<int> idx(n);
    iota(idx.begin(), idx.end(), 0);

    vector<pair<cpp_int,int>> with_idx(n);
    for (int i = 0; i < n; ++i) with_idx[i] = {a[i], i};

    vector<vector<int>> orders;

    // Original order
    orders.push_back(idx);

    // Descending by value
    {
        auto v = with_idx;
        sort(v.begin(), v.end(), [](const auto& x, const auto& y){
            return x.first > y.first;
        });
        vector<int> ord;
        ord.reserve(n);
        for (auto &p : v) ord.push_back(p.second);
        orders.push_back(move(ord));
    }

    // Ascending by value
    {
        auto v = with_idx;
        sort(v.begin(), v.end(), [](const auto& x, const auto& y){
            return x.first < y.first;
        });
        vector<int> ord;
        ord.reserve(n);
        for (auto &p : v) ord.push_back(p.second);
        orders.push_back(move(ord));
    }

    // Two random shuffles with fixed seeds for determinism
    {
        vector<int> ord = idx;
        mt19937_64 rng(123456789);
        shuffle(ord.begin(), ord.end(), rng);
        orders.push_back(ord);
        shuffle(ord.begin(), ord.end(), rng);
        orders.push_back(ord);
    }

    auto absdiff = [&](const cpp_int& x, const cpp_int& y) -> cpp_int {
        return (x >= y) ? (x - y) : (y - x);
    };

    // Best solution tracking
    vector<int> best_pick(n, 0);
    cpp_int best_diff = absdiff(W, cpp_int(0)); // starting from sum=0
    cpp_int best_sum = 0;

    auto try_order = [&](const vector<int>& ord, int mode) {
        // mode 0: add if abs(sum+ai - W) <= abs(sum-W)
        // mode 1: add if sum+ai <= W
        vector<int> pick(n, 0);
        cpp_int sum = 0;
        cpp_int cur_diff = absdiff(W, sum);

        for (int id : ord) {
            const cpp_int& v = a[id];
            if (mode == 0) {
                cpp_int nd = absdiff(W, sum + v);
                if (nd <= cur_diff) {
                    pick[id] = 1;
                    sum += v;
                    cur_diff = nd;
                }
            } else {
                if (sum + v <= W) {
                    pick[id] = 1;
                    sum += v;
                    cur_diff = absdiff(W, sum);
                }
            }
        }
        // Update best if improved
        cpp_int diff = absdiff(W, sum);
        if (diff < best_diff) {
            best_diff = diff;
            best_pick = move(pick);
            best_sum = sum;
        }
    };

    for (const auto& ord : orders) {
        try_order(ord, 0);
        try_order(ord, 1);
    }

    // Output best picks
    for (int i = 0; i < n; ++i) {
        if (i) cout << ' ';
        cout << best_pick[i];
    }
    cout << '\n';

    return 0;
}