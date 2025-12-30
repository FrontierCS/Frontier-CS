#include <iostream>
#include <vector>
#include <cmath>
#include <iomanip>
#include <map>
#include <algorithm>
#include <cassert>

using namespace std;

using ld = long double;

int N;

map<long long, ld> memo[3];

ld query(long long x, long long y) {
    cout << "? " << x << " " << y << endl;
    ld dist_sum;
    cin >> dist_sum;
    return dist_sum;
}

ld get_val(long long k, int x_val) {
    if (memo[x_val].count(k)) {
        return memo[x_val][k];
    }
    ld res = query(x_val, k);
    return memo[x_val][k] = res;
}

struct LineInfo {
    long long val;
    long long scaled_inv_c;

    bool operator<(const LineInfo& other) const {
        if (scaled_inv_c != other.scaled_inv_c) {
            return scaled_inv_c < other.scaled_inv_c;
        }
        return val < other.val;
    }
};

vector<LineInfo> found_lines_info[3];

void find_lines_recursive(long long min_k, long long max_k, int x_val) {
    if (min_k >= max_k) return;

    ld h_min = get_val(min_k, x_val);
    ld h_max = get_val(max_k, x_val);

    if (max_k - min_k < 5) {
        for (long long k = min_k + 1; k < max_k; ++k) {
            get_val(k, x_val);
        }
        for (long long k = min_k + 1; k < max_k; ++k) {
            ld h_km1 = get_val(k - 1, x_val);
            ld h_k = get_val(k, x_val);
            ld h_kp1 = get_val(k + 1, x_val);
            ld d2h = h_km1 + h_kp1 - 2 * h_k;
            if (d2h > 1e-7) {
                // Here we assume b_i are unique. d2h = 2/C_i
                found_lines_info[x_val].push_back({k, (long long)round((d2h / 2.0) * 1e12)});
            }
        }
        return;
    }

    long long mid_k = min_k + (max_k - min_k) / 2;
    if (mid_k == min_k) mid_k++;
    if (mid_k == max_k) mid_k--;
    if (mid_k <= min_k || mid_k >= max_k) { // Should not happen with above checks
        find_lines_recursive(min_k, max_k-1, x_val);
        return;
    }

    ld h_mid = get_val(mid_k, x_val);

    ld h_linear_mid = h_min + (h_max - h_min) * (ld)(mid_k - min_k) / (ld)(max_k - min_k);

    if (h_linear_mid - h_mid > 1e-7) {
        find_lines_recursive(min_k, mid_k, x_val);
        find_lines_recursive(mid_k, max_k, x_val);
    }
}

vector<long long> a_sol, b_sol;
vector<pair<long long, long long>> candidates;
vector<long long> c_inv_scaled_sol;
map<LineInfo, int> m1_counts, m2_counts;

bool solve_signs(int k) {
    if (k == (int)candidates.size()) {
        return true;
    }

    long long b = candidates[k].first;
    long long abs_a = candidates[k].second;
    long long c_inv_scaled = c_inv_scaled_sol[k];

    // Try a = abs_a
    LineInfo li1 = {b + abs_a, c_inv_scaled};
    LineInfo li2 = {b + 2 * abs_a, c_inv_scaled};

    bool possible_pos = false;
    auto it1 = m1_counts.find(li1);
    if (it1 != m1_counts.end() && it1->second > 0) {
        auto it2 = m2_counts.find(li2);
        if (it2 != m2_counts.end() && it2->second > 0) {
            possible_pos = true;
        }
    }
    
    if (possible_pos) {
        m1_counts[li1]--;
        m2_counts[li2]--;
        a_sol.push_back(abs_a);
        b_sol.push_back(b);
        if (solve_signs(k + 1)) return true;
        a_sol.pop_back();
        b_sol.pop_back();
        m1_counts[li1]++;
        m2_counts[li2]++;
    }

    if (abs_a == 0) return false;

    // Try a = -abs_a
    li1 = {b - abs_a, c_inv_scaled};
    li2 = {b - 2 * abs_a, c_inv_scaled};
    
    bool possible_neg = false;
    auto it1_neg = m1_counts.find(li1);
    if (it1_neg != m1_counts.end() && it1_neg->second > 0) {
        auto it2_neg = m2_counts.find(li2);
        if (it2_neg != m2_counts.end() && it2_neg->second > 0) {
            possible_neg = true;
        }
    }
    
    if (possible_neg) {
        m1_counts[li1]--;
        m2_counts[li2]--;
        a_sol.push_back(-abs_a);
        b_sol.push_back(b);
        if (solve_signs(k + 1)) return true;
        a_sol.pop_back();
        b_sol.pop_back();
        m1_counts[li1]++;
        m2_counts[li2]++;
    }

    return false;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    cout << fixed << setprecision(10);

    cin >> N;

    find_lines_recursive(-10001, 10001, 0);

    for(const auto& info : found_lines_info[0]){
        long long b = info.val;
        ld c_inv = info.scaled_inv_c / 1e12;
        ld c_sq = 1.0 / (c_inv * c_inv);
        long long abs_a = round(sqrt(max((ld)0.0, c_sq - 1.0L)));
        candidates.push_back({b, abs_a});
        c_inv_scaled_sol.push_back(info.scaled_inv_c);
    }
    
    find_lines_recursive(-20002, 20002, 1);
    find_lines_recursive(-30003, 30003, 2);
    
    for (auto& info : found_lines_info[1]) {
        m1_counts[info]++;
    }
    for (auto& info : found_lines_info[2]) {
        m2_counts[info]++;
    }

    solve_signs(0);

    cout << "! ";
    for (int i = 0; i < N; ++i) cout << a_sol[i] << (i == N - 1 ? "" : " ");
    cout << " ";
    for (int i = 0; i < N; ++i) cout << b_sol[i] << (i == N - 1 ? "" : " ");
    cout << endl;

    return 0;
}