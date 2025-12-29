#include <iostream>
#include <vector>
#include <map>
#include <cmath>
#include <algorithm>
#include <cassert>
#include <iomanip>
#include <functional>

using namespace std;

using ll = long long;
using ld = long double;

const int X0 = 0;
const int X1 = 1;
const int Xm1 = -1;
const double EPS = 1e-8;
const double DELTA_EPS = 1e-6;

map<pair<int, ld>, double> cache;

double query(int x, ld y) {
    auto key = make_pair(x, y);
    if (cache.count(key)) return cache[key];
    cout << "? " << x << " " << fixed << setprecision(10) << y << endl;
    double res;
    cin >> res;
    cache[key] = res;
    return res;
}

vector<pair<ll, double>> get_breakpoints(int X) {
    ll low_y = -10000LL * abs(X) - 10000;
    ll high_y =  10000LL * abs(X) + 10000;
    ll L = low_y - 1;
    ll R = high_y;

    map<ll, double> h_cache;
    auto compute_h = [&](ll m) -> double {
        if (h_cache.count(m)) return h_cache[m];
        double f1 = query(X, m + 0.5);
        double f2 = query(X, m + 1.0);
        double val = 2.0 * (f2 - f1);
        h_cache[m] = val;
        return val;
    };

    vector<pair<ll, double>> breakpoints;
    double D_left = compute_h(L);
    double D_right = compute_h(R);
    ll current_m = L;
    double current_D = D_left;

    while (current_D + EPS < D_right) {
        ll lo = current_m + 1;
        ll hi = R;
        ll found = -1;
        while (lo <= hi) {
            ll mid = (lo + hi) / 2;
            double h_mid = compute_h(mid);
            if (h_mid > current_D + EPS) {
                found = mid;
                hi = mid - 1;
            } else {
                lo = mid + 1;
            }
        }
        if (found == -1) break; // should not happen

        ll m_next = found;
        double h_next = compute_h(m_next);
        double h_prev = compute_h(m_next - 1); // equals current_D
        double delta = h_next - h_prev;
        breakpoints.emplace_back(m_next, delta);

        current_m = m_next;
        current_D = h_next;
    }
    return breakpoints;
}

int main() {
    int n;
    cin >> n;

    vector<pair<ll, double>> bp0 = get_breakpoints(X0);
    vector<pair<ll, double>> bp1 = get_breakpoints(X1);
    vector<pair<ll, double>> bpm1 = get_breakpoints(Xm1);

    // For each breakpoint compute approximate |a|
    auto process = [](vector<pair<ll, double>>& bp) -> vector<tuple<ll, double, int>> {
        vector<tuple<ll, double, int>> res;
        for (auto [y, delta] : bp) {
            double inv = 2.0 / delta;
            double a2 = inv * inv - 1;
            if (a2 < 0) a2 = 0;
            int abs_a = (int)round(sqrt(a2));
            res.emplace_back(y, delta, abs_a);
        }
        return res;
    };

    auto data0 = process(bp0);
    auto data1 = process(bp1);
    auto datam1 = process(bpm1);

    // Group by abs_a for each x
    map<int, vector<ll>> group0, group1, groupm1;
    for (auto [y, delta, abs_a] : data0) group0[abs_a].push_back(y);
    for (auto [y, delta, abs_a] : data1) group1[abs_a].push_back(y);
    for (auto [y, delta, abs_a] : datam1) groupm1[abs_a].push_back(y);

    vector<pair<int, int>> lines;

    for (auto& [abs_a, vec0] : group0) {
        auto it1 = group1.find(abs_a);
        auto itm1 = groupm1.find(abs_a);
        if (it1 == group1.end() || itm1 == groupm1.end()) continue;

        vector<ll>& v0 = vec0;
        vector<ll>& v1 = it1->second;
        vector<ll>& vm1 = itm1->second;

        int m = v0.size();
        if (v1.size() != m || vm1.size() != m) continue;

        vector<bool> used1(m, false), usedm1(m, false);
        vector<pair<int, int>> cur_lines;
        bool ok = false;

        function<void(int)> dfs = [&](int idx) {
            if (idx == m) {
                ok = true;
                return;
            }
            for (int j = 0; j < m; ++j) {
                if (used1[j]) continue;
                for (int k = 0; k < m; ++k) {
                    if (usedm1[k]) continue;
                    if (2 * v0[idx] == v1[j] + vm1[k]) {
                        int a = v1[j] - v0[idx];
                        if (abs(a) != abs_a) continue;
                        ll b = v0[idx]; // since x=0, b = y0
                        if (b < -10000 || b > 10000) continue;
                        used1[j] = usedm1[k] = true;
                        cur_lines.emplace_back(a, b);
                        dfs(idx + 1);
                        if (ok) return;
                        cur_lines.pop_back();
                        used1[j] = usedm1[k] = false;
                    }
                }
            }
        };

        dfs(0);
        if (ok) {
            for (auto& p : cur_lines) lines.push_back(p);
        }
    }

    // Output answer
    cout << "! ";
    for (auto [a, b] : lines) cout << a << " ";
    for (auto [a, b] : lines) cout << b << " ";
    cout << endl;

    return 0;
}