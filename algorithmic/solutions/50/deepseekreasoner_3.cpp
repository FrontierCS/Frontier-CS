#include <bits/stdc++.h>
using namespace std;

const int MAX_N = 400;
const int MAX_M = 4000;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);
    
    int n, m;
    cin >> n >> m;
    vector<long long> cost(m);
    for (int i = 0; i < m; i++) {
        cin >> cost[i];
    }
    vector<bitset<MAX_N>> sets(m);
    for (int i = 0; i < n; i++) {
        int k;
        cin >> k;
        for (int j = 0; j < k; j++) {
            int a;
            cin >> a;
            a--;
            sets[a].set(i);
        }
    }

    // Greedy algorithm
    bitset<MAX_N> uncovered;
    for (int i = 0; i < n; i++) uncovered.set(i);
    vector<bool> selected(m, false);
    vector<int> greedy_sol;
    long long greedy_cost = 0;
    while (uncovered.any()) {
        double best_ratio = 1e18;
        int best_set = -1;
        int best_cnt = 0;
        for (int j = 0; j < m; j++) {
            if (selected[j]) continue;
            bitset<MAX_N> cover = sets[j] & uncovered;
            int cnt = cover.count();
            if (cnt == 0) continue;
            double ratio = (double)cost[j] / cnt;
            if (ratio < best_ratio - 1e-9 || (abs(ratio - best_ratio) < 1e-9 && cnt > best_cnt)) {
                best_ratio = ratio;
                best_set = j;
                best_cnt = cnt;
            }
        }
        if (best_set == -1) break; // should not happen
        selected[best_set] = true;
        greedy_sol.push_back(best_set);
        greedy_cost += cost[best_set];
        uncovered &= ~sets[best_set];
    }

    // Remove redundant sets from greedy solution
    sort(greedy_sol.begin(), greedy_sol.end(),
         [&](int a, int b) { return cost[a] > cost[b]; });
    bitset<MAX_N> union_all;
    union_all.reset();
    for (int idx : greedy_sol) union_all |= sets[idx];
    vector<bool> redundant(greedy_sol.size(), false);
    for (int i = 0; i < (int)greedy_sol.size(); i++) {
        int idx = greedy_sol[i];
        bitset<MAX_N> temp = union_all & ~sets[idx];
        if (temp.all()) {
            redundant[i] = true;
            union_all = temp;
        }
    }
    vector<int> greedy_nored;
    for (int i = 0; i < (int)greedy_sol.size(); i++) {
        if (!redundant[i]) greedy_nored.push_back(greedy_sol[i]);
    }
    greedy_sol.swap(greedy_nored);
    greedy_cost = 0;
    union_all.reset();
    for (int idx : greedy_sol) {
        greedy_cost += cost[idx];
        union_all |= sets[idx];
    }

    // Simulated Annealing
    vector<int> current_sol = greedy_sol;
    long long current_cost = greedy_cost;
    bitset<MAX_N> current_union = union_all;
    vector<bool> current_selected(m, false);
    for (int idx : current_sol) current_selected[idx] = true;

    vector<int> best_sol = current_sol;
    long long best_cost = current_cost;

    double avg_cost = accumulate(cost.begin(), cost.end(), 0.0) / m;
    double T = avg_cost * 10.0;
    const double cooling_rate = 0.999999;
    const int iterations = 5000000;

    mt19937 rng(chrono::steady_clock::now().time_since_epoch().count());
    uniform_real_distribution<> dis(0.0, 1.0);

    for (int iter = 0; iter < iterations; iter++) {
        double r = dis(rng);
        if (r < 0.33) {
            // Add a random non-selected set
            int s2 = rng() % m;
            if (current_selected[s2]) continue;
            long long new_cost = current_cost + cost[s2];
            double delta = new_cost - current_cost;
            if (delta < 0 || dis(rng) < exp(-delta / T)) {
                current_sol.push_back(s2);
                current_selected[s2] = true;
                current_union |= sets[s2];
                current_cost = new_cost;
                if (current_cost < best_cost) {
                    best_cost = current_cost;
                    best_sol = current_sol;
                }
            }
        } else if (r < 0.66) {
            // Remove a random selected set if feasible
            if (current_sol.empty()) continue;
            int rand_idx = rng() % current_sol.size();
            int s1 = current_sol[rand_idx];
            bitset<MAX_N> new_union = current_union & ~sets[s1];
            if (new_union.all()) {
                long long new_cost = current_cost - cost[s1];
                double delta = new_cost - current_cost;
                if (delta < 0 || dis(rng) < exp(-delta / T)) {
                    current_sol[rand_idx] = current_sol.back();
                    current_sol.pop_back();
                    current_selected[s1] = false;
                    current_union = new_union;
                    current_cost = new_cost;
                    if (current_cost < best_cost) {
                        best_cost = current_cost;
                        best_sol = current_sol;
                    }
                }
            }
        } else {
            // Swap a random selected set with a random non-selected set
            if (current_sol.empty()) continue;
            int rand_sel_idx = rng() % current_sol.size();
            int s1 = current_sol[rand_sel_idx];
            int s2 = rng() % m;
            if (current_selected[s2]) continue;
            bitset<MAX_N> new_union = (current_union & ~sets[s1]) | sets[s2];
            if (new_union.all()) {
                long long new_cost = current_cost - cost[s1] + cost[s2];
                double delta = new_cost - current_cost;
                if (delta < 0 || dis(rng) < exp(-delta / T)) {
                    current_sol[rand_sel_idx] = s2;
                    current_selected[s1] = false;
                    current_selected[s2] = true;
                    current_union = new_union;
                    current_cost = new_cost;
                    if (current_cost < best_cost) {
                        best_cost = current_cost;
                        best_sol = current_sol;
                    }
                }
            }
        }
        T *= cooling_rate;
    }

    // Final redundancy removal on best solution
    sort(best_sol.begin(), best_sol.end(),
         [&](int a, int b) { return cost[a] > cost[b]; });
    bitset<MAX_N> union_best;
    union_best.reset();
    for (int idx : best_sol) union_best |= sets[idx];
    vector<bool> redundant_best(best_sol.size(), false);
    for (int i = 0; i < (int)best_sol.size(); i++) {
        int idx = best_sol[i];
        bitset<MAX_N> temp = union_best & ~sets[idx];
        if (temp.all()) {
            redundant_best[i] = true;
            union_best = temp;
        }
    }
    vector<int> final_sol;
    for (int i = 0; i < (int)best_sol.size(); i++) {
        if (!redundant_best[i]) final_sol.push_back(best_sol[i]);
    }
    best_sol.swap(final_sol);
    best_cost = 0;
    for (int idx : best_sol) best_cost += cost[idx];

    // Output
    cout << best_sol.size() << "\n";
    for (int idx : best_sol) {
        cout << idx + 1 << " ";
    }
    cout << "\n";

    return 0;
}