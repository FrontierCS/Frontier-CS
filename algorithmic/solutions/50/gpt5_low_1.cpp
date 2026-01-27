#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n, m;
    if (!(cin >> n >> m)) return 0;
    vector<long long> cost(m + 1);
    for (int i = 1; i <= m; ++i) cin >> cost[i];
    
    const int B = 512;
    using BS = bitset<B>;
    vector<BS> setMask(m + 1);
    vector<vector<int>> elements_in_set(m + 1);
    vector<vector<int>> sets_of_elem(n + 1);
    
    for (int i = 1; i <= n; ++i) {
        int k; cin >> k;
        for (int j = 0; j < k; ++j) {
            int a; cin >> a;
            if (a >= 1 && a <= m) {
                setMask[a].set(i);
                elements_in_set[a].push_back(i);
                sets_of_elem[i].push_back(a);
            }
        }
    }
    
    // Check for any element with no set covering it (still try to proceed, but impossible)
    for (int i = 1; i <= n; ++i) {
        if (sets_of_elem[i].empty()) {
            // No feasible cover; output empty (or try best effort)
            cout << 0 << "\n\n";
            return 0;
        }
    }
    
    BS covered;
    vector<int> chosen;
    vector<char> chosen_flag(m + 1, 0);
    
    int covered_cnt = 0;
    while (covered_cnt < n) {
        int best = -1;
        long double best_ratio = numeric_limits<long double>::infinity();
        int best_gain = 0;
        for (int s = 1; s <= m; ++s) {
            BS tmp = setMask[s] & (~covered);
            int gain = (int)tmp.count();
            if (gain <= 0) continue;
            long double ratio = (long double)cost[s] / (long double)gain;
            if (ratio < best_ratio || (ratio == best_ratio && cost[s] < cost[best])) {
                best_ratio = ratio;
                best = s;
                best_gain = gain;
            }
        }
        if (best == -1) {
            // Fallback: pick cheapest set that covers any uncovered element
            long long minc = LLONG_MAX;
            int pick = -1;
            for (int s = 1; s <= m; ++s) {
                BS tmp = setMask[s] & (~covered);
                if (tmp.any() && cost[s] < minc) {
                    minc = cost[s];
                    pick = s;
                }
            }
            if (pick == -1) break; // cannot proceed
            best = pick;
        }
        if (!chosen_flag[best]) {
            chosen.push_back(best);
            chosen_flag[best] = 1;
        }
        BS newly = setMask[best] & (~covered);
        covered |= setMask[best];
        covered_cnt = (int)covered.count();
    }
    
    // If still not fully covered (shouldn't usually happen), try to add sets per uncovered element
    if (covered_cnt < n) {
        for (int i = 1; i <= n; ++i) {
            if (!covered.test(i)) {
                int best = -1;
                long long minc = LLONG_MAX;
                for (int s : sets_of_elem[i]) {
                    if (cost[s] < minc) { minc = cost[s]; best = s; }
                }
                if (best != -1 && !chosen_flag[best]) {
                    chosen.push_back(best);
                    chosen_flag[best] = 1;
                    covered |= setMask[best];
                }
            }
        }
    }
    
    // Redundancy removal
    vector<int> cover_count(n + 1, 0);
    for (int s : chosen) {
        for (int e : elements_in_set[s]) cover_count[e]++;
    }
    vector<int> new_chosen;
    for (int idx = (int)chosen.size() - 1; idx >= 0; --idx) {
        int s = chosen[idx];
        bool redundant = true;
        for (int e : elements_in_set[s]) {
            if (cover_count[e] <= 1) { redundant = false; break; }
        }
        if (redundant) {
            for (int e : elements_in_set[s]) cover_count[e]--;
            chosen_flag[s] = 0;
        } else {
            new_chosen.push_back(s);
        }
    }
    reverse(new_chosen.begin(), new_chosen.end());
    chosen.swap(new_chosen);
    
    // Local improvement: try single replacement with a cheaper set that covers unique elements
    // Build bitset of selected sets for quick checks
    // Precompute mask of unique elements for each chosen set
    // Iterate a few times for potential cascading improvements
    int iterations = 2;
    while (iterations--) {
        bool improved = false;
        // recompute cover_count
        fill(cover_count.begin(), cover_count.end(), 0);
        for (int s : chosen) for (int e : elements_in_set[s]) cover_count[e]++;
        
        for (int i = 0; i < (int)chosen.size(); ++i) {
            int s = chosen[i];
            BS uniq;
            for (int e : elements_in_set[s]) if (cover_count[e] == 1) uniq.set(e);
            if (uniq.none()) {
                // If no unique elements, try removing it now as redundant
                bool redundant = true;
                for (int e : elements_in_set[s]) if (cover_count[e] <= 1) { redundant = false; break; }
                if (redundant) {
                    for (int e : elements_in_set[s]) cover_count[e]--;
                    chosen_flag[s] = 0;
                    chosen.erase(chosen.begin() + i);
                    --i;
                    improved = true;
                }
                continue;
            }
            // Find a set t not chosen that covers uniq and has lower cost
            int best_t = -1;
            long long best_c = cost[s] - 1; // must be strictly cheaper
            for (int t = 1; t <= m; ++t) {
                if (t == s || chosen_flag[t]) continue;
                // Quick filter: t must cover all uniq elements
                BS tmp = setMask[t] & uniq;
                if (tmp == uniq) {
                    if (cost[t] < cost[s] && cost[t] < (best_t == -1 ? LLONG_MAX : best_c)) {
                        best_t = t;
                        best_c = cost[t];
                    }
                }
            }
            if (best_t != -1) {
                // Apply swap: remove s, add t
                for (int e : elements_in_set[s]) cover_count[e]--;
                for (int e : elements_in_set[best_t]) cover_count[e]++;
                chosen_flag[s] = 0;
                chosen_flag[best_t] = 1;
                chosen[i] = best_t;
                improved = true;
            }
        }
        if (!improved) break;
    }
    
    // Final sanity: ensure coverage
    BS final_cover;
    for (int s : chosen) final_cover |= setMask[s];
    vector<int> final_list;
    if ((int)final_cover.count() < n) {
        // Add sets to cover any missing elements
        for (int i = 1; i <= n; ++i) {
            if (!final_cover.test(i)) {
                int best = -1;
                long long minc = LLONG_MAX;
                for (int s : sets_of_elem[i]) {
                    if (cost[s] < minc) { minc = cost[s]; best = s; }
                }
                if (best != -1) {
                    if (!chosen_flag[best]) {
                        chosen.push_back(best);
                        chosen_flag[best] = 1;
                    }
                    final_cover |= setMask[best];
                }
            }
        }
    }
    
    sort(chosen.begin(), chosen.end());
    chosen.erase(unique(chosen.begin(), chosen.end()), chosen.end());
    
    cout << chosen.size() << "\n";
    for (size_t i = 0; i < chosen.size(); ++i) {
        if (i) cout << ' ';
        cout << chosen[i];
    }
    cout << "\n";
    return 0;
}