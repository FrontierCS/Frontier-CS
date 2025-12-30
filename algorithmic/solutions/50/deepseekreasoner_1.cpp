#include <bits/stdc++.h>
using namespace std;

const int MAX_N = 400;
const int MAX_M = 4000;

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    cin >> n >> m;

    vector<long long> cost(m);
    for (int i = 0; i < m; i++) {
        cin >> cost[i];
    }

    vector<bitset<MAX_N>> set_mask(m);
    vector<vector<int>> set_elements(m);

    for (int i = 0; i < n; i++) {
        int k;
        cin >> k;
        for (int j = 0; j < k; j++) {
            int a;
            cin >> a;
            a--; // to 0-index
            set_mask[a].set(i);
            set_elements[a].push_back(i);
        }
    }

    // ---------- randomized greedy ----------
    const int R = 20; // number of random greedy trials
    vector<bool> best_solution(m, false);
    long long best_cost = 0;
    bool first = true;

    mt19937 rng(chrono::steady_clock::now().time_since_epoch().count());
    uniform_real_distribution<double> dist(0.9, 1.1);

    for (int trial = 0; trial < R; trial++) {
        vector<long long> perturbed_cost = cost;
        for (int i = 0; i < m; i++) {
            perturbed_cost[i] = (long long)(cost[i] * dist(rng));
        }

        vector<bool> selected(m, false);
        bitset<MAX_N> covered;
        int covered_count = 0;
        vector<int> order_selected;

        while (covered_count < n) {
            long long best_ratio = 1LL << 60;
            int best_set = -1;
            int best_new = 0;
            for (int j = 0; j < m; j++) {
                if (selected[j]) continue;
                bitset<MAX_N> new_cover = set_mask[j] & ~covered;
                int cnt = new_cover.count();
                if (cnt == 0) continue;
                long long ratio = perturbed_cost[j] * 1000 / cnt; // scale to avoid floating point
                if (ratio < best_ratio || (ratio == best_ratio && cnt > best_new)) {
                    best_ratio = ratio;
                    best_set = j;
                    best_new = cnt;
                }
            }
            if (best_set == -1) break;
            selected[best_set] = true;
            order_selected.push_back(best_set);
            covered |= set_mask[best_set];
            covered_count = covered.count();
        }

        // compute coverage count for removal
        vector<int> coverage_count(n, 0);
        for (int j = 0; j < m; j++) {
            if (selected[j]) {
                for (int e : set_elements[j]) {
                    coverage_count[e]++;
                }
            }
        }

        // remove redundant sets in reverse order
        for (int idx = order_selected.size() - 1; idx >= 0; idx--) {
            int j = order_selected[idx];
            if (!selected[j]) continue;
            bool redundant = true;
            for (int e : set_elements[j]) {
                if (coverage_count[e] <= 1) {
                    redundant = false;
                    break;
                }
            }
            if (redundant) {
                selected[j] = false;
                for (int e : set_elements[j]) {
                    coverage_count[e]--;
                }
            }
        }

        // compute cost
        long long total = 0;
        for (int j = 0; j < m; j++) {
            if (selected[j]) total += cost[j];
        }

        if (first || total < best_cost) {
            best_cost = total;
            best_solution = selected;
            first = false;
        }
    }

    // ---------- simulated annealing ----------
    vector<bool> current = best_solution;
    long long current_cost = best_cost;

    // compute coverage count and uncovered count
    vector<int> coverage_count(n, 0);
    int uncovered_count = 0;
    for (int j = 0; j < m; j++) {
        if (current[j]) {
            for (int e : set_elements[j]) {
                coverage_count[e]++;
            }
        }
    }
    for (int e = 0; e < n; e++) {
        if (coverage_count[e] == 0) uncovered_count++;
    }

    long long sum_all_costs = accumulate(cost.begin(), cost.end(), 0LL);
    long long penalty = sum_all_costs + 1;
    long long current_penalized = current_cost + penalty * uncovered_count;

    // SA parameters
    double T = 1000.0;
    double cooling = 0.999995;
    int iterations = 2000000;

    uniform_int_distribution<int> rand_set(0, m - 1);
    uniform_real_distribution<double> rand_prob(0.0, 1.0);

    for (int iter = 0; iter < iterations; iter++) {
        int j = rand_set(rng);
        bool old = current[j];

        // compute new state
        long long new_cost = current_cost;
        int new_uncovered = uncovered_count;
        if (old) { // removing
            new_cost -= cost[j];
            for (int e : set_elements[j]) {
                coverage_count[e]--;
                if (coverage_count[e] == 0) new_uncovered++;
            }
        } else { // adding
            new_cost += cost[j];
            for (int e : set_elements[j]) {
                if (coverage_count[e] == 0) new_uncovered--;
                coverage_count[e]++;
            }
        }
        long long new_penalized = new_cost + penalty * new_uncovered;
        long long delta = new_penalized - current_penalized;

        if (delta < 0 || rand_prob(rng) < exp(-delta / T)) {
            // accept
            current_cost = new_cost;
            uncovered_count = new_uncovered;
            current_penalized = new_penalized;
            current[j] = !old;
            if (uncovered_count == 0 && current_cost < best_cost) {
                best_cost = current_cost;
                best_solution = current;
            }
        } else {
            // reject: revert coverage changes
            if (old) {
                for (int e : set_elements[j]) {
                    coverage_count[e]++;
                }
            } else {
                for (int e : set_elements[j]) {
                    coverage_count[e]--;
                }
            }
        }

        T *= cooling;
    }

    // final removal pass on best solution
    current = best_solution;
    // compute coverage count
    fill(coverage_count.begin(), coverage_count.end(), 0);
    for (int j = 0; j < m; j++) {
        if (current[j]) {
            for (int e : set_elements[j]) {
                coverage_count[e]++;
            }
        }
    }
    // try to remove each selected set if redundant
    for (int j = 0; j < m; j++) {
        if (!current[j]) continue;
        bool redundant = true;
        for (int e : set_elements[j]) {
            if (coverage_count[e] <= 1) {
                redundant = false;
                break;
            }
        }
        if (redundant) {
            current[j] = false;
            for (int e : set_elements[j]) {
                coverage_count[e]--;
            }
        }
    }

    // output
    vector<int> chosen;
    for (int j = 0; j < m; j++) {
        if (current[j]) chosen.push_back(j + 1);
    }
    cout << chosen.size() << "\n";
    for (size_t i = 0; i < chosen.size(); i++) {
        if (i > 0) cout << " ";
        cout << chosen[i];
    }
    cout << endl;

    return 0;
}