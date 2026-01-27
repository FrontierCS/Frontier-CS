#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n, m;
    if(!(cin >> n >> m)) return 0;
    vector<long long> cost(m);
    for (int i = 0; i < m; ++i) cin >> cost[i];

    vector<vector<int>> sets(m);              // sets[s] -> list of elements in set s
    vector<vector<int>> sets_of_element(n);   // sets_of_element[e] -> list of sets containing element e

    bool impossible = false;
    for (int e = 0; e < n; ++e) {
        int k; cin >> k;
        if (k == 0) impossible = true;
        for (int j = 0; j < k; ++j) {
            int a; cin >> a; --a;
            if (a >= 0 && a < m) {
                sets[a].push_back(e);
                sets_of_element[e].push_back(a);
            }
        }
    }

    if (impossible) {
        cout << 0 << "\n\n";
        return 0;
    }

    vector<int> uncovered_count(m);
    for (int s = 0; s < m; ++s) uncovered_count[s] = (int)sets[s].size();

    vector<int> cover_count(n, 0);
    vector<char> covered(n, 0);
    int num_uncovered = n;

    struct Node {
        int id;
        int cnt;
        long double ratio;
    };
    struct Cmp {
        bool operator()(const Node& a, const Node& b) const {
            if (a.ratio != b.ratio) return a.ratio > b.ratio; // min-heap behavior
            if (a.cnt != b.cnt) return a.cnt < b.cnt; // prefer larger coverage on tie
            return a.id > b.id;
        }
    };
    priority_queue<Node, vector<Node>, Cmp> pq;
    for (int s = 0; s < m; ++s) {
        if (uncovered_count[s] > 0) {
            pq.push({s, uncovered_count[s], (long double)cost[s] / (long double)uncovered_count[s]});
        }
    }

    vector<int> chosen;
    chosen.reserve(m);

    while (num_uncovered > 0 && !pq.empty()) {
        Node cur = pq.top(); pq.pop();
        int s = cur.id;
        if (uncovered_count[s] == 0) continue;
        if (cur.cnt != uncovered_count[s]) {
            pq.push({s, uncovered_count[s], (long double)cost[s] / (long double)uncovered_count[s]});
            continue;
        }
        // select set s
        chosen.push_back(s);
        for (int e : sets[s]) {
            if (cover_count[e] == 0) {
                covered[e] = 1;
                num_uncovered--;
            }
            cover_count[e]++;
            // decrease uncovered_count for sets containing e
            for (int t : sets_of_element[e]) {
                if (uncovered_count[t] > 0) {
                    uncovered_count[t]--;
                    // lazy update: push a new node; optional to reduce staleness
                    if (uncovered_count[t] > 0) {
                        pq.push({t, uncovered_count[t], (long double)cost[t] / (long double)uncovered_count[t]});
                    }
                }
            }
        }
    }

    if (num_uncovered > 0) {
        // Could not cover all elements
        cout << 0 << "\n\n";
        return 0;
    }

    // Prune redundant sets
    vector<int> multiplicity = cover_count;
    vector<char> in_solution(m, 0);
    for (int s : chosen) in_solution[s] = 1;

    // Order sets for pruning: higher cost first, then lower efficiency
    vector<int> order = chosen;
    sort(order.begin(), order.end(), [&](int a, int b){
        if (cost[a] != cost[b]) return cost[a] > cost[b];
        // tie-breaker: fewer elements first (more likely redundant)
        return sets[a].size() < sets[b].size();
    });

    for (int s : order) {
        bool can_remove = true;
        for (int e : sets[s]) {
            if (multiplicity[e] <= 1) { can_remove = false; break; }
        }
        if (can_remove) {
            in_solution[s] = 0;
            for (int e : sets[s]) multiplicity[e]--;
        }
    }

    vector<int> ans;
    for (int s = 0; s < m; ++s) if (in_solution[s]) ans.push_back(s + 1); // back to 1-based

    cout << ans.size() << "\n";
    for (size_t i = 0; i < ans.size(); ++i) {
        if (i) cout << ' ';
        cout << ans[i];
    }
    cout << "\n";
    return 0;
}