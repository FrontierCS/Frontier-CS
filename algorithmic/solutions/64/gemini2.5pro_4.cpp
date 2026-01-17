#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <cmath>
#include <chrono>
#include <random>

using namespace std;

typedef long long ll;

struct Item {
    ll val;
    int id;
};

struct Sum {
    ll sum;
    int mask;

    bool operator<(const Sum& other) const {
        return sum < other.sum;
    }
};

pair<ll, int> solve_mim(const vector<Item>& items, ll target) {
    int n = items.size();
    if (n == 0) {
        return {0, 0};
    }
    int n1 = n / 2;
    vector<Sum> s1;
    s1.reserve(1 << n1);
    for (int i = 0; i < (1 << n1); ++i) {
        ll current_sum = 0;
        for (int j = 0; j < n1; ++j) {
            if ((i >> j) & 1) {
                current_sum += items[j].val;
            }
        }
        s1.push_back({current_sum, i});
    }

    int n2 = n - n1;
    vector<Sum> s2;
    s2.reserve(1 << n2);
    for (int i = 0; i < (1 << n2); ++i) {
        ll current_sum = 0;
        for (int j = 0; j < n2; ++j) {
            if ((i >> j) & 1) {
                current_sum += items[n1 + j].val;
            }
        }
        s2.push_back({current_sum, i});
    }

    sort(s2.begin(), s2.end());

    ll best_sum = -1;
    ll min_diff = -1;
    int best_mask = 0;

    for (const auto& p1 : s1) {
        ll required = target - p1.sum;
        auto it = lower_bound(s2.begin(), s2.end(), Sum{required, 0});

        if (it != s2.end()) {
            ll current_sum = p1.sum + it->sum;
             if (current_sum == target) {
                return {target, p1.mask | (it->mask << n1)};
            }
            ll diff = abs(current_sum - target);
            if (min_diff == -1 || diff < min_diff) {
                min_diff = diff;
                best_sum = current_sum;
                best_mask = p1.mask | (it->mask << n1);
            }
        }

        if (it != s2.begin()) {
            it--;
            ll current_sum = p1.sum + it->sum;
            if (current_sum == target) {
                return {target, p1.mask | (it->mask << n1)};
            }
            ll diff = abs(current_sum - target);
            if (min_diff == -1 || diff < min_diff) {
                min_diff = diff;
                best_sum = current_sum;
                best_mask = p1.mask | (it->mask << n1);
            }
        }
    }
    return {best_sum, best_mask};
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    auto start_time = chrono::high_resolution_clock::now();

    int n;
    ll T;
    cin >> n >> T;
    vector<Item> all_items(n);
    for (int i = 0; i < n; ++i) {
        cin >> all_items[i].val;
        all_items[i].id = i;
    }

    if (n <= 42) {
        pair<ll, int> result = solve_mim(all_items, T);
        int final_mask = result.second;
        string ans = "";
        for (int i = 0; i < n; ++i) {
            if ((final_mask >> i) & 1) {
                ans += '1';
            } else {
                ans += '0';
            }
        }
        cout << ans << endl;
    } else {
        vector<int> current_selection(n, 0);
        ll current_sum = 0;
        
        mt19937 rng(chrono::steady_clock::now().time_since_epoch().count());
        for(int i = 0; i < n; ++i) {
            if (uniform_int_distribution<int>(0, 1)(rng)) {
                current_selection[i] = 1;
                current_sum += all_items[i].val;
            }
        }

        vector<int> best_selection = current_selection;
        ll min_diff = abs(current_sum - T);

        if (min_diff == 0) {
            string ans = "";
            for (int i = 0; i < n; ++i) {
                ans += (best_selection[i] ? '1' : '0');
            }
            cout << ans << endl;
            return 0;
        }

        vector<int> p(n);
        iota(p.begin(), p.end(), 0);

        const int K = 40;

        while (true) {
            auto current_time = chrono::high_resolution_clock::now();
            if (chrono::duration_cast<chrono::milliseconds>(current_time - start_time).count() > 1950) {
                break;
            }

            shuffle(p.begin(), p.end(), rng);

            vector<Item> sub_problem_items;
            sub_problem_items.reserve(K);
            for (int i = 0; i < K; ++i) {
                sub_problem_items.push_back(all_items[p[i]]);
            }

            ll fixed_sum = 0;
            for (int i = K; i < n; ++i) {
                if (current_selection[p[i]]) {
                    fixed_sum += all_items[p[i]].val;
                }
            }

            ll sub_target = T - fixed_sum;
            pair<ll, int> sub_result = solve_mim(sub_problem_items, sub_target);
            
            current_sum = fixed_sum + sub_result.first;
            int sub_mask = sub_result.second;

            for (int i = 0; i < K; ++i) {
                if ((sub_mask >> i) & 1) {
                    current_selection[sub_problem_items[i].id] = 1;
                } else {
                    current_selection[sub_problem_items[i].id] = 0;
                }
            }
            
            if (abs(current_sum - T) < min_diff) {
                min_diff = abs(current_sum - T);
                best_selection = current_selection;
                if (min_diff == 0) break;
            }
        }

        string ans = "";
        for (int i = 0; i < n; ++i) {
            ans += (best_selection[i] ? '1' : '0');
        }
        cout << ans << endl;
    }

    return 0;
}