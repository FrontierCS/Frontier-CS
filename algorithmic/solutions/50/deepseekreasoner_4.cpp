#include <bits/stdc++.h>
using namespace std;

int main() {
    clock_t start = clock();
    const double TIME_LIMIT = 9.5 * CLOCKS_PER_SEC;
    int n, m;
    scanf("%d %d", &n, &m);
    vector<int> cost(m+1);
    for (int i = 1; i <= m; i++) {
        scanf("%d", &cost[i]);
    }
    vector<vector<int>> set_elements(m+1);
    vector<vector<int>> element_sets(n);
    for (int i = 0; i < n; i++) {
        int k;
        scanf("%d", &k);
        while (k--) {
            int a;
            scanf("%d", &a);
            set_elements[a].push_back(i);
            element_sets[i].push_back(a);
        }
    }
    // Build bitsets for greedy
    vector<bitset<400>> set_bits(m+1);
    for (int j = 1; j <= m; j++) {
        for (int e : set_elements[j]) {
            set_bits[j].set(e);
        }
    }
    
    // Greedy
    vector<bool> chosen(m+1, false);
    vector<int> cover_count(n, 0);
    bitset<400> uncovered;
    uncovered.set();
    int total_cost = 0;
    while (uncovered.any()) {
        double best_ratio = 1e30;
        int best_set = -1;
        for (int j = 1; j <= m; j++) {
            if (chosen[j]) continue;
            bitset<400> new_cov = set_bits[j] & uncovered;
            int cnt = new_cov.count();
            if (cnt == 0) continue;
            double ratio = (double)cost[j] / cnt;
            if (ratio < best_ratio) {
                best_ratio = ratio;
                best_set = j;
            }
        }
        if (best_set == -1) break;
        chosen[best_set] = true;
        total_cost += cost[best_set];
        uncovered &= ~set_bits[best_set];
        for (int e : set_elements[best_set]) {
            cover_count[e]++;
        }
    }
    
    // Compute critical_count for chosen sets
    vector<int> critical_count(m+1, 0);
    for (int j = 1; j <= m; j++) {
        if (!chosen[j]) continue;
        int cnt = 0;
        for (int e : set_elements[j]) {
            if (cover_count[e] == 1) cnt++;
        }
        critical_count[j] = cnt;
    }
    
    // Redundant removal (descending cost)
    bool changed;
    do {
        changed = false;
        vector<int> chosen_list;
        for (int j = 1; j <= m; j++) if (chosen[j]) chosen_list.push_back(j);
        sort(chosen_list.begin(), chosen_list.end(), [&](int a, int b) { return cost[a] > cost[b]; });
        for (int i : chosen_list) {
            if (!chosen[i]) continue;
            if (critical_count[i] == 0) {
                chosen[i] = false;
                total_cost -= cost[i];
                for (int e : set_elements[i]) {
                    int old = cover_count[e];
                    cover_count[e]--;
                    if (old == 2) {
                        for (int s : element_sets[e]) {
                            if (chosen[s]) {
                                critical_count[s]++;
                                break;
                            }
                        }
                    }
                }
                changed = true;
            }
        }
    } while (changed);
    
    // Local improvement
    vector<int> unchosen;
    for (int j = 1; j <= m; j++) if (!chosen[j]) unchosen.push_back(j);
    random_device rd;
    mt19937 g(rd());
    shuffle(unchosen.begin(), unchosen.end(), g);
    
    bool improved = true;
    while (improved && (clock() - start) < TIME_LIMIT) {
        improved = false;
        for (int j : unchosen) {
            if (chosen[j]) continue;
            // Backup state
            vector<bool> old_chosen = chosen;
            vector<int> old_cover_count = cover_count;
            vector<int> old_critical_count = critical_count;
            int old_total_cost = total_cost;
            
            // Add set j
            for (int e : set_elements[j]) {
                int old = cover_count[e];
                cover_count[e]++;
                if (old == 1) {
                    for (int s : element_sets[e]) {
                        if (chosen[s]) {
                            critical_count[s]--;
                            break;
                        }
                    }
                }
            }
            chosen[j] = true;
            int cnt_critical = 0;
            for (int e : set_elements[j]) {
                if (cover_count[e] == 1) cnt_critical++;
            }
            critical_count[j] = cnt_critical;
            total_cost += cost[j];
            
            // Remove redundant sets in descending cost order
            vector<int> chosen_list;
            for (int i = 1; i <= m; i++) if (chosen[i]) chosen_list.push_back(i);
            sort(chosen_list.begin(), chosen_list.end(), [&](int a, int b) { return cost[a] > cost[b]; });
            for (int i : chosen_list) {
                if (!chosen[i]) continue;
                if (critical_count[i] == 0) {
                    chosen[i] = false;
                    total_cost -= cost[i];
                    for (int e : set_elements[i]) {
                        int old = cover_count[e];
                        cover_count[e]--;
                        if (old == 2) {
                            for (int s : element_sets[e]) {
                                if (chosen[s]) {
                                    critical_count[s]++;
                                    break;
                                }
                            }
                        }
                    }
                }
            }
            
            if (total_cost < old_total_cost) {
                improved = true;
            } else {
                chosen = old_chosen;
                cover_count = old_cover_count;
                critical_count = old_critical_count;
                total_cost = old_total_cost;
            }
        }
        if (improved) {
            unchosen.clear();
            for (int j = 1; j <= m; j++) if (!chosen[j]) unchosen.push_back(j);
            shuffle(unchosen.begin(), unchosen.end(), g);
        }
    }
    
    // Output
    vector<int> result;
    for (int j = 1; j <= m; j++) if (chosen[j]) result.push_back(j);
    printf("%d\n", (int)result.size());
    for (size_t i = 0; i < result.size(); i++) {
        if (i > 0) printf(" ");
        printf("%d", result[i]);
    }
    printf("\n");
    
    return 0;
}