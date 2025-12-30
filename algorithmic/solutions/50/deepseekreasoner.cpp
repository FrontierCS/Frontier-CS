#include <bits/stdc++.h>
using namespace std;

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    cin >> n >> m;
    vector<long long> cost(m + 1);
    for (int i = 1; i <= m; ++i) {
        cin >> cost[i];
    }

    vector<vector<int>> element_sets(n + 1);
    vector<vector<int>> set_elements(m + 1);
    for (int e = 1; e <= n; ++e) {
        int k;
        cin >> k;
        element_sets[e].reserve(k);
        for (int j = 0; j < k; ++j) {
            int s;
            cin >> s;
            element_sets[e].push_back(s);
            set_elements[s].push_back(e);
        }
    }

    // Greedy weighted set cover
    vector<bool> covered(n + 1, false);
    vector<int> count_uncovered(m + 1);
    for (int s = 1; s <= m; ++s) {
        count_uncovered[s] = set_elements[s].size();
    }
    vector<bool> selected(m + 1, false);
    int uncovered = n;

    auto cmp = [](const tuple<double, int, int>& a, const tuple<double, int, int>& b) {
        return get<0>(a) > get<0>(b); // min-heap
    };
    priority_queue<tuple<double, int, int>, vector<tuple<double, int, int>>, decltype(cmp)> pq(cmp);
    for (int s = 1; s <= m; ++s) {
        if (count_uncovered[s] > 0) {
            pq.push({(double)cost[s] / count_uncovered[s], s, count_uncovered[s]});
        }
    }

    vector<int> chosen;
    while (uncovered > 0) {
        double ratio;
        int s, cnt;
        do {
            if (pq.empty()) {
                // Should not happen if instance is feasible
                goto after_greedy;
            }
            auto top = pq.top();
            pq.pop();
            tie(ratio, s, cnt) = top;
        } while (selected[s] || count_uncovered[s] != cnt);

        selected[s] = true;
        chosen.push_back(s);

        for (int e : set_elements[s]) {
            if (!covered[e]) {
                covered[e] = true;
                --uncovered;
                for (int s2 : element_sets[e]) {
                    if (!selected[s2]) {
                        --count_uncovered[s2];
                        if (count_uncovered[s2] > 0) {
                            pq.push({(double)cost[s2] / count_uncovered[s2], s2, count_uncovered[s2]});
                        }
                    }
                }
            }
        }
    }

after_greedy:
    // Remove redundant sets
    vector<bool> in_sol(m + 1, false);
    for (int s : chosen) in_sol[s] = true;

    vector<int> cover_count(n + 1, 0);
    for (int s : chosen) {
        for (int e : set_elements[s]) {
            ++cover_count[e];
        }
    }

    bool changed = true;
    while (changed) {
        changed = false;
        vector<int> current;
        for (int s : chosen) {
            if (in_sol[s]) current.push_back(s);
        }
        sort(current.begin(), current.end(), [&](int a, int b) {
            return cost[a] > cost[b];
        });

        for (int s : current) {
            if (!in_sol[s]) continue;
            bool redundant = true;
            for (int e : set_elements[s]) {
                if (cover_count[e] <= 1) {
                    redundant = false;
                    break;
                }
            }
            if (redundant) {
                in_sol[s] = false;
                changed = true;
                for (int e : set_elements[s]) {
                    --cover_count[e];
                }
            }
        }
    }

    chosen.clear();
    for (int s = 1; s <= m; ++s) {
        if (in_sol[s]) chosen.push_back(s);
    }

    // Output
    cout << chosen.size() << '\n';
    for (size_t i = 0; i < chosen.size(); ++i) {
        if (i > 0) cout << ' ';
        cout << chosen[i];
    }
    cout << '\n';

    return 0;
}